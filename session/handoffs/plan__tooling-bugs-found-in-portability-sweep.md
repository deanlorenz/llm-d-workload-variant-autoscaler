from: planner (llm-scaler workspace bootstrap design)
to: plan (atomic-step-protocol-brainstorm — you're in charge of tooling)
session: three tooling bugs found during the portability sweep — one NEW, one tracked-but-unfixed, one config hazard

## Why this is coming to you

Dean: "if you found a bug send a handoff to that planner — he is in charge of tooling."

These surfaced while sweeping `plans/scripts/` for hardcoded paths (for
`planning/llm-scaler-workspace-bootstrap-design.md`). I was looking for portability blockers and
found actual defects. **I have not fixed any of them** — not my scope, and two are in files your
coder is likely to touch.

Separate handoffs already sent today, not repeated here:
`plan__sync-main-generalize-for-second-repo.md` (R5 generalization) and
`plan__harvest-needs-repo-scope-axis-for-second-repo.md`.

---

## BUG 1 — `sync-main-status.sh` reports **RUNNING for a dead watcher** when `last_check` is empty or missing (NEW — not in any handoff or backlog I can find)

**Site:** `scripts/sync-main-status.sh:20-21`, and the identical logic duplicated at
`scripts/sync-main-session-start.sh:19-20`.

```bash
last_check=$(grep -m1 '^last_check:' "$S" | cut -d' ' -f2-)
lc_epoch=$(date -d "$last_check" +%s 2>/dev/null || echo 0)
age=$(( $(date +%s) - lc_epoch ))
```

**The defect:** if the status file exists but has no `last_check:` line (or an empty value), `$last_check`
is the empty string — and **`date -d "" +%s` succeeds with exit 0**, returning **midnight today**. So:

- the `|| echo 0` fallback is **unreachable** on this path;
- `lc_epoch` becomes midnight-today instead of the intended sentinel `0`;
- `age` becomes "seconds since midnight," not the watcher's real age.

**Verified, not inferred** (this machine, 2026-08-16):

```
$ date -d "" +%s ; echo "rc=$?"
1786827600      rc=0            # midnight today; now was 1786847401
$ date -d "garbage-value" +%s 2>/dev/null || echo 0
0                               # fallback DOES work for genuine garbage
```

**Why it matters, and the failure direction:** the gate is `[ "$age" -lt 150 ]`. Between 00:00 and
00:02:30 local, `age < 150` is **true**, so a **dead watcher is reported RUNNING**. Outside that window
it reports STALE with a meaningless age (e.g. "last check 19801s ago").

The false-RUNNING is the dangerous one: it is precisely the failure mode that let the dead watcher go
unnoticed until Dean asked directly (see
`plan__sync-main-hook-silent-noop-and-tier1-tier2-boundary.md.WIP`, whose root cause is different but
whose *symptom* — "silence that looks like health" — is the same). A status command whose failure mode is
"claims healthy" is worse than one that errors.

**Same shape as a defect you already fixed.** CURRENT.md records `stat -f %m` being wrong on GNU
coreutils because `-f` takes a *format*, so `stat` printed a filesystem block and **exited 0**, making
`|| echo 0` unreachable and feeding prose into `$(( ))`. This is that bug again with `date -d ""`:
**a command that succeeds on bad input, so the `||` fallback never fires.** Worth treating as a class,
not two incidents — anything of the form `x=$(cmd "$maybe_empty" || echo 0)` has it.

**Suggested fix** (yours to decide): guard the empty case before calling `date` —
`[ -n "$last_check" ] || lc_epoch=0` — and, since the same block is duplicated in two scripts, this is
an argument for the shared-library approach CURRENT.md says commit `e4613d36` already introduced for
the checkpoint guards.

---

## BUG 2 — `tick-live-index.sh:111` still carries the `stat -f %m` bug (tracked, still unfixed — confirming it is live)

```bash
mtime_epoch=$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null)
```

Already a tracked backlog item (CURRENT.md § Issues to Open, marked "latent, fallback path only,"
left out of scope when the three checkpoint scripts were fixed via `date -r` in `750f9c5d`).
**Confirmed still present as of 2026-08-16** — I grepped and it is the only remaining `stat -f` in
`scripts/`. Flagging only because your coder is in these files right now, so it is a near-free
drive-by fix rather than a scheduled task. `mtime_epoch` empty → `age_secs=$(( now - ))` → arithmetic
error or garbage `age_stale`.

---

## BUG 3 — config hazard: two branches carry `remote=upstream`, and the push safety is layered

Not a script bug — a **repo-config** hazard, reported because it interacts with the never-push-to-upstream
rule and with any tooling that copies git config.

```
branch.main.remote       = upstream    merge = refs/heads/main
branch.ta-testing.remote = upstream    merge = refs/heads/main
```

Pushes are currently saved by **two independent layers**: `remote.pushdefault = origin`, and
`remote.upstream.pushurl = READ-ONLY-UPSTREAM-DO-NOT-PUSH` (a deliberately invalid URL, so a push dies
at transport resolution and prints the reason — genuinely good, and the single best pattern in the
current setup).

**The hazard is in duplication, not in today's state:** any tooling that reproduces `branch.*.remote`
into a new container while dropping `pushdefault` re-arms both branches. For the new repo my doc says
don't copy branch-tracking config at all. For *here*, the cheap mitigation is an assertion — **every
remote's push URL is either `origin` or a `READ-ONLY-*` sentinel** — which is the kind of check that is
obvious to run once and never again unless it lives in a script. Reasonable candidate for the pre-push
gate; your call whether it belongs to tooling at all.

---

## What I did NOT do

- No script edited, no config changed, no `.WIP` handoff touched.
- BUG 1's fix is *suggested*, not designed — it lands in files your coder owns and may be mid-edit.
- Did not check whether BUG 1's pattern (`cmd || echo 0` where `cmd` succeeds on empty input) exists
  elsewhere in `scripts/`. **Recommend that grep** — the class has now produced two confirmed
  instances, so a third is likelier than not.

Full sweep findings: `planning/llm-scaler-workspace-bootstrap-design.md` § 2 (DRAFT, uncommitted);
§ 8 lists exactly what was read and which claims are unverified.
