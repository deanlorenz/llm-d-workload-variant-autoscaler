# Review — checkpoint-capture-spec.md, sync-watchers-spec.md, doc-tooling-spec.md

**review** (Type 6) · **Status: DRAFT.**

## At a glance

**Mission:** design review (Opus) of the three retroactive Type 3 specs written 2026-08-16, before any
coder builds against them.

**Approach:** the retroactive documentation is accurate and well-sourced; every claimed defect is real.
The problems concentrate in two places: the S0/S0b guard-library design (`checkpoint-capture-spec.md`)
is under-specified in ways that would stall or mislead a coder, and three "no defect found" verdicts
are wrong — a defect of the exact class the specs were hunting is present in each case.

**Needs you:** Finding 2 (below) is a real architectural decision, not a documentation fix — is the
single-instance guard held for the process's whole lifetime, or only at startup (released once the
loop is confirmed to be the sole instance)? Everything downstream (whether Guard 2/`pgrep` is still
needed, whether a trap is required, whether the pid-based staleness check in Addendum 10 is even
reachable) depends on this answer, and neither Addendum 10 nor any of the three specs actually decided
it.

**Checklist:**
- [ ] Dean decides Finding 2 (guard lifetime).
- [ ] Revise `checkpoint-capture-spec.md` S0/S0b/S5/S6 per Findings 1-3, 5, 7, 8.
- [ ] Revise `sync-watchers-spec.md` S2/S4/Defect-B per Findings 4, 9, 10.
- [ ] Revise `doc-tooling-spec.md` per Finding 6.
- [ ] Amend Addendum 10 once Finding 2 is decided.

---

## Findings

Ranked most severe first. "Must fix" findings block a coder from starting correctly; "worth noting"
findings don't block but should be corrected.

### Finding 1 (must fix) — S0's `guard_acquire` interface cannot express what the three call sites need

`checkpoint-capture-spec.md` S0 and `atomic-step-protocol-design-addendum-10.md` both give the
signature `guard_acquire <name> <origin-pid>`. The `mkdir` path only needs `<name>`, but the `pgrep`
liveness check needs a **regex over argv**:

```
pgrep -f "session-snapshot[.]sh .*--origin-pid $origin_pid"
```

The escaped `[.]sh` (not `.sh`, which matches any character) and the `.*--origin-pid` prefix are
load-bearing — Addendum 7 treats this escaping as deliberate. A convention (script-basename-without-
`.sh` derives the pattern) is derivable from the three existing call sites, but neither S0 nor Addendum
10 states it, so a coder has to reinvent it and can get the escaping subtly wrong, producing a guard
that silently over-matches.

Separately, the pgrep check's own exclusion (`| grep -qv "^$$\$"`) depends on `$$` resolving to the
*sourcing script's* pid once this logic moves into a sourced function (correct, since `source` doesn't
fork) — but this is exactly the kind of detail a coder "fixes" into `$BASHPID` or a subshell-captured
value, silently breaking it. Addendum 7's own history: the pgrep-only version left **zero** survivors
on two simultaneous launches (4/4) when this class of bug was present.

**Fix required:** S0 must state the pattern-derivation rule literally, or take the pattern as an
explicit third argument — and must state the `$$` constraint explicitly rather than relying on a coder
inheriting an unstated invariant from the original inline code.

### Finding 2 (must fix, needs Dean) — the guard's lifetime is undecided, and everything downstream depends on the answer

S0 says the guard directory holds the acquiring process's pid, *"since that pid is what the staleness
check in a later acquisition attempt reads."* But all three current scripts release the guard
immediately after the startup check (`rmdir "$dedup_dir" # commit point: proceeding to become the
watcher`) — before entering the loop. Addendum 10 acknowledges this in passing (*"held only during
startup, removed inline"*) but then designs a pid-based staleness check as if the guard were held for
the process's entire lifetime. These two framings are incompatible:

- **If the guard stays released-at-startup** (today's behavior, unchanged): a guard directory existing
  at all means a process died inside a sub-second startup window. Its recorded pid will almost always
  already be dead, so the pid check reclaims immediately — correct, but this makes the mtime fallback
  and the 1-week threshold essentially dead code, and the pid check barely improves on what exists.
- **If the guard is instead held for the loop's lifetime** (which is what makes the pid check
  genuinely valuable — "reclaim immediately if the holder is dead" implies the holder is *supposed to
  still be holding it*): `guard_release` moves from the startup path to an exit path, Guard 2
  (`pgrep`) becomes **redundant** (a held directory with a live pid already answers "is one running"),
  and Addendum 7's explicit "**No trap**" ruling needs revisiting — a long-lived held guard with no
  trap *is* the lingering lock file Dean specifically objected to when this whole redesign started.

Neither `checkpoint-capture-spec.md` nor Addendum 10 states which shape is intended. A coder cannot
build S0 without deciding this themselves, and the decision changes whether Guard 2 survives, whether
a trap is now needed, and whether the mtime fallback is ever reachable.

**This is a decision for Dean, not something to resolve inside a spec revision.**

### Finding 3 (must fix) — `tick-live-index.sh` S5's "no defect found" contradicts Addendum 7's own tracked bug

`checkpoint-capture-spec.md` S5 says "No defect found," but Addendum 7's own "Still open" list names,
twice: *"`tick-live-index.sh:111` still carries the `stat -f %m` bug."* Confirmed directly at line 111:

```bash
mtime_epoch=$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null)
```

Verified the failure mode directly: `stat -f %m <file>` on GNU coreutils exits non-zero and prints a
filesystem block to stdout, not a timestamp. It is *latent*, not live, on this machine specifically —
`stat -c %Y` is tried first and succeeds on GNU, so the broken fallback is never reached here. That is
a real mitigating detail, but "no defect found" is still the wrong verdict for a line a frozen addendum
already tracks as an open bug.

**Fix required:** change the verdict to "carries the known `stat -f %m` fallback bug per Addendum 7;
latent, not live, on GNU (the `-c %Y` branch is tried first) — fix or delete the unreachable fallback."

### Finding 4 (must fix) — `sync-main-watch.sh`'s status file lies about liveness after a crash, and `sync-watchers-spec.md` asserts the opposite

`sync-watchers-spec.md` S2 claims the script writes status *"via a `trap ... EXIT` on any exit path
(so a killed or crashing watcher still leaves an accurate 'stopped' status, not a stale 'watching' one
that lies about liveness)."*

**Verified directly, and this is false.** `write_status()` hardcodes the state field unconditionally:

```bash
write_status() {
  local step="$1" notes="$2"
  ...
    echo "state: watching"          # line 69 — always this, regardless of $step
    echo "current_step: $step"
```

`cleanup() { write_status "stopped" ...; }` passes `"stopped"` as `$step`, which lands in
`current_step`, never in `state`. After any exit — clean or crashed — the status file still reads
`state: watching`.

This is not cosmetic: `sync-main-session-start.sh:58` uses this exact field as its auto-start success
gate:

```bash
if [ -f "$status_file" ] && grep -q '^state: watching' "$status_file" 2>/dev/null; then
```

Because the field is always `watching` after any run — including a crash — **the hook reports
"AUTO-STARTED it — no action needed" for a watcher that may already be dead.** This is a third live
defect in the same hook (alongside Defects A and B, already documented), of exactly the class the spec
was hunting, and the spec's own text asserts the opposite of what the code does.

**Fix required:** correct S2's claim; add this as a named defect (suggest "Defect C") alongside A and
B; flag that a coder fixing Defect A will likely use this exact grep as their verification and get a
false-positive result.

### Finding 5 (must fix) — Defect 1's stated fix is incomplete; `--digest` is also missing, silently disabling Tier-2 registration

`checkpoint-capture-spec.md`'s Defect 1 names only the missing `--origin-pid`. But
`tier1-session-start.sh`'s launch line also omits `--digest`, and in `session-snapshot.sh`:

- Tier-2 self-registration is gated on `[ -n "$tfile" ] && [ -n "$digest" ]` (registration never
  happens without `--digest`).
- `consolidate()` returns early without `--digest` (line 161), so `--consolidate-every` can never fire
  either.

The spec's own `## Intent` call-stack diagram claims the hook path produces both registration and
optional consolidation — under the only caller that exists, it produces neither. This isn't a
one-flag fix either: the hook only builds a `.raw.md` sidecar path, and adding `--digest` means
deciding whether the hook should also create/seed a digest file with a "Captured through:" marker
(`tick-consolidate.sh` hard-dies without one) — a decision that belongs in the spec, not left to a
coder's judgment mid-fix.

**Fix required:** expand Defect 1's description to include the missing `--digest`, and state explicitly
whether the hook should seed a digest file (and with what marker) or leave Tier-2 registration
deliberately absent for hook-started sessions.

### Finding 6 (worth noting) — `doc-tooling-spec.md` says "no changes proposed" while the frozen design assigns `toc-refresh.sh` a specific pending change

`atomic-step-protocol-design.md` § Consequences for existing artifacts contains: *"`scripts/toc-refresh.sh`
— keep anchor/TOC generation; drop the line-range half, including the double-run stabilization pass."*
That's a scoped, decided, unbuilt change in a FINAL frozen design — narrower than "retire the whole
script eventually," which is the framing `doc-tooling-spec.md` offers instead. Not blocking (nothing
breaks meanwhile, and deferring until no old-shape doc needs ranges is a legitimate sequencing
argument) — but the spec should cite that design row rather than imply no change is decided at all.

### Finding 7 (worth noting) — wrong citation: Addendum 8 doesn't discuss `tick-shared-scan.sh`

`checkpoint-capture-spec.md` S4 cites Addendum 8 for the "never run live" claim. Addendum 8 is about
background-agent infrastructure and contains zero mentions of `tick-shared-scan`/Tier-2. The claim
itself is true (and correctly reflected in the roadmap); the citation is wrong, likely meant for
Addendum 2 or 9.

### Finding 8 (worth noting) — S0/S0b lack the step-shape fields the design requires for executable steps

Per `atomic-step-protocol-design.md` § The step, `conventions:` is a mandatory, affirmatively-stated
field — *"Omission → halt."* The retroactive steps in all three specs correctly have only briefs (no
execution to specify), matching the sibling specs' own convention. But S0 and S0b are the one place in
these three documents describing genuinely new code, and they have no `scope`, `verify`, `done_when`,
or `conventions:` line. Combined with Findings 1-2, S0 is currently a brief without a step.

### Finding 9 (worth noting) — Defect B's description is imprecise and under-reports a second stale claim in the same comment block

`sync-watchers-spec.md` cites "lines 30-48" for the stale flock text; the flock sentence is at line 45.
Lines 30-39 are a separate paragraph with its own stale claim — it describes the retired `anchor_alive()`
mechanism ("self-exits once neither a VS Code-WSL connection nor a Claude process remains anywhere in
this WSL instance"), which no longer matches the current watcher's actual behavior (checks one specific
origin pid, not "any Claude process anywhere"). A coder fixing Defect B needs to correct two claims in
that comment block, not one.

### Finding 10 (worth noting) — minor accuracy nits

- `sync-watchers-spec.md` S4's verdict strings ("RUNNING/STALE-NOT-RUNNING/NOT RUNNING") don't exactly
  match the code's actual output (`RUNNING`, `STALE / NOT RUNNING`, `NOT RUNNING (no status file —
  never started on this machine)`) — the script's own header comment has the same drift, so this is a
  faithfully-reproduced pre-existing inaccuracy, not a new one.
- `checkpoint-capture-spec.md` S1 doesn't mention that `session-snapshot.sh` treats any nonzero
  extract exit code (including the `.tick-disabled` gate's exit 3) as a logged no-op — worth one
  clause, since a stray `.tick-disabled` file without the env-var opt-out would silently starve Tier-1
  forever.
- Both specs cite in-file line numbers in documents whose own regime is retiring line addressing —
  pragmatic for shell scripts with no heading structure, but these specific numbers are the most
  likely to rot the moment a coder adds the missing flags these findings call for.

## What was checked and found accurate

Worth recording, since most of the review holds up:

- Defect 1, Defect A, and Defect B are all real and correctly characterized (Defect A's detail that
  `sync-main-watch.sh` has **no** `--once` escape at all, unlike `session-snapshot.sh`, was independently
  verified).
- The guard-block duplication claim is exact — a direct diff of all three copies shows they differ only
  in the script name and two comment words.
- `sync-current-watch.sh`'s exclusion and its still-old flock/`anchor_alive()` state are both confirmed.
- `toc-refresh.sh`'s anchor algorithm claim was verified by running the actual pipeline
  (`"Type 1 — Foo"` → `type-1--foo`).
- S3 (`tick-consolidate.sh`), and `sync-main-once.sh`/`sync-main-status.sh` in the sync-watchers family,
  check out against the code as described, including the `--ff-only`-never-a-merge-commit behavior,
  `last_sync` preservation across a no-op one-shot run, the wrong-branch refusal, and the no-`$(...)`
  allowlisting rationale for the status script.

## Overall verdict

**Needs a narrowly-scoped revision pass before a coder starts on S0/S0b — not a rewrite.** The
retroactive documentation itself is accurate, well-cited, and found three real bugs no prior review
had caught. The blocking problem is that the one genuinely executable part of these specs (S0/S0b) is
the least specified part, and it inherits an architectural question (Finding 2) that only Dean can
answer. Once that's decided: revise `checkpoint-capture-spec.md`'s S0/S0b/S5/S6 and
`sync-watchers-spec.md`'s S2/Defect-B per the findings above, amend Addendum 10 to record the
lifetime decision, and the retroactive steps in all three specs can ship with only minor citation and
wording corrections.
