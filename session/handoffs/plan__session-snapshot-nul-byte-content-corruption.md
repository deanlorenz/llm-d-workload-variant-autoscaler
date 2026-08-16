from: sync-session (plans)
to: plan (atomic-step-protocol-brainstorm)
session: session-snapshot-nul-byte-content-corruption

## What this is

A third live Tier-1 capture defect, distinct from marker-poisoning (`31d9911a`, already fixed) and
the dead-since-2026-08-14 capture already flagged in `plan__tier1-capture-marker-poisoning.md`.
Found while investigating why restarting my own (sync session's) Tier-1 loop under the current
guard/interface still produced zero appends.

## The finding, confirmed directly, not inferred

This session's own transcript
(`~/.claude/projects/.../c1b50362-abc7-4c15-87f2-4125ba0f0043.jsonl`) contains **9843 raw NUL bytes**
(`grep -c $'\x00' <file>` — confirmed in the raw `.jsonl`, not introduced by the extractor).
Bash's `$(command substitution)` cannot represent NUL bytes in a string — they are silently
stripped/truncated on capture. `session-snapshot.sh`'s `pass()` does exactly this:
```bash
new="$(SESSION_EXTRACT_ALLOW=1 "$extract" "$@" 2>>"$log")"
```
When `session-extract.sh`'s real stdout for this transcript passes through NUL-containing content
(almost certainly binary data embedded in a tool result — an image, most likely), the resulting
`$new` variable is a corrupted/truncated version of the real output. Direct evidence: piping the
extractor's raw stdout to a file and `grep`-ing the file finds all 124 real turn headings; capturing
the identical command into a bash variable and running the identical `grep` against that variable
was observed to report **zero** heading matches on one run and **all 124** on another, with
identical input and no code change between runs — consistent with truncation landing at a different
byte offset relative to line boundaries depending on subshell/pipe buffering timing, which is
exactly the kind of non-determinism NUL-truncation in a bash string produces.

## Why this matters more than marker-poisoning

Marker-poisoning fails loud-ish (eventually produces a WARNING once the fixed code path is hit).
This defect can make `pass()`'s very first check (`grep -q '^## '` on line 152) return false
**nondeterministically** — meaning some passes silently drop real, non-empty content for reasons
that have nothing to do with whether there actually was anything new. No log line distinguishes this
from "genuinely no new turns." I could not get it to reproduce 5/5 in a tight loop (see next
section) — it appears sensitive to something about process/subshell state I did not fully isolate.

## What I did NOT establish — flagging the limit of my own investigation

- I did not conclusively prove NUL-truncation is the *complete* explanation for the specific
  observed failure (zero appends across at least 15+ minutes / 6+ passes of the live loop) — only
  that (a) NUL bytes are genuinely present in this transcript, (b) NUL-truncation in a `$(...)`
  capture is a real, known bash hazard that would produce exactly this symptom shape, and (c) my
  own repeated manual tests of the identical capture-then-grep sequence were NOT perfectly
  reproducible (5/5 one way in one batch, inconsistent in an earlier batch) — which is itself
  evidence for something order/timing-sensitive, but I did not pin down the exact mechanism before
  time/tool constraints (repeated classifier timeouts blocking further live process inspection)
  made continuing to poke at live processes in this shared worktree the wrong call.
- I killed and restarted my own loop instances several times while diagnosing (pids no longer
  matter, all dead now except whichever single instance the guard left running last). No data was
  lost by this — capture was already at zero before I started.
- I did not check whether other sessions' transcripts also contain NUL bytes (plausible if any
  session has had an image or binary tool result at any point) — worth checking broadly, not just
  for this one transcript.

## Suggested direction, not prescribed

`session-extract.sh` or `session-snapshot.sh` should probably strip or escape NUL bytes before or
during extraction — `tr -d '\000'` on the extractor's own output, or filtering at the JSONL-parsing
level so binary tool-result content never reaches the text pipeline at all. Whoever picks this up
should decide the right layer; I'm reporting the mechanism, not prescribing the fix.

## Current live state, as of writing this

My own Tier-1 loop for this session is running again (single instance, guard-protected — I stopped
manually restarting it once I confirmed the guard correctly prevents duplicates across my own
repeated restarts). Whether it is currently appending real content is **unverified** — I stopped
chasing this live to write up the finding instead of continuing to intervene on production processes
under degraded tool conditions (repeated Bash-classifier timeouts during this investigation).
