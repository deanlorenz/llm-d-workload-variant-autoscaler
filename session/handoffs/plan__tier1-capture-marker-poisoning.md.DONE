from: plans (single-instance-guard coder)
to: planner
session: tier1-capture-silent-failure

Two live defects in Tier-1 capture, found while working on the guard library. Both are outside my
assigned scope, both are **silent**, and both mean the mechanism whose whole purpose is not losing
the user's words has been capturing nothing. Flagging rather than fixing: the fix needs a decision
about the silent-failure path, and `checkpoint-capture-spec.md` S2 currently records this script's
non-guard logic as defect-free, which is wrong.

## Defect 1 — the marker can be poisoned by the user's own text

`scripts/session-snapshot.sh`'s `pass()` advances its marker like this:

```
printf '%s\n' "$new" | grep '^## ' | tail -1 | sed 's/^## //; s/  *(mid-turn)$//' > "$mark"
```

The intent is "take the newest captured turn's `## <timestamp>` heading". But it matches **any**
line beginning `## ` in the extracted text — including a markdown heading inside a user turn's own
body. When that happens the marker becomes that heading instead of a timestamp, and every later pass
runs `session-extract.sh --since <garbage>`, which matches nothing.

Live evidence, not hypothetical:

- `session/digests/.atomic-step-protocol-brainstorm.raw.md.mark` contains the literal string
  `Findings`.
- `session/digests/.atomic-step-protocol-brainstorm.raw.md.log` repeats `since: Findings` /
  `turns: 0`.
- `session/digests/atomic-step-protocol-brainstorm.raw.md` has not been appended since
  **2026-08-13 18:38**, while that session's transcript
  (`f0196004-c4a5-494c-8b98-1d4176b68ba0.jsonl`) was still being written 20 minutes before I looked.

So capture for that session has been dead for three days. It fails with rc 0, and `turns: 0` is
indistinguishable from "genuinely nothing new" — exactly the shape of failure
`CONVENTIONS.md` § Checkpoint capture already warns about for the extractor's own gate.

## Defect 2 — `sync-session` capture has never appended anything

- `session/digests/.sync-session.raw.md.mark` does not exist.
- Its log shows `turns: 122` every pass — extract is finding turns.
- `session/digests/sync-session.raw.md` has been 379 bytes (just the file header) since
  **2026-08-14 17:41**.

So `pass()`'s `printf '%s' "$new" | grep -q '^## ' || return 0` guard has never matched, meaning
extract's stdout carries no `## ` headings even while its stderr reports 122 turns. Either the two
sides disagree about format or `--since`-less extraction returns something `pass()` does not expect.
Worth confirming which before writing a fix, since it may indicate a contract mismatch between
`session-extract.sh` and `session-snapshot.sh` rather than a bug in either alone.

## Decisions this needs (not mine to make)

1. How to make the marker robust. Options, not exhaustive: match `^## ` **and** validate the
   captured value parses as a timestamp before writing it; anchor on a heading shape the extractor
   controls and a user turn cannot forge; or have `session-extract.sh` emit the marker value itself
   on a separate channel instead of having the caller re-parse its human-readable output.
2. Whether a poisoned/unparseable marker should be **loud** — this is the load-bearing half. Both
   defects survived days because a broken capture and an idle session look identical. A `--since`
   value that parses as nothing arguably deserves a non-zero exit or a distinct log line, not `rc 0`.
3. Whether the existing poisoned marker files should be repaired by hand (drop the marker and
   re-extract from a chosen timestamp) or left, accepting the three-day gap.
4. Correcting `checkpoint-capture-spec.md` S2's "no defect found" verdict for the non-guard logic —
   same class of correction as review Finding 3 made for S5.

## Context you will want

I killed both of these loops by accident during testing (over-broad cleanup helper; recorded in
`session/status/single-instance-guard.md`). That is how I came to read their logs. They were
capturing nothing at the time, so nothing was lost, but they are now **not running**, and restarting
them is the separately-approved deployment step — the command shape is in my status file. If the
marker bug is fixed first, a restart also becomes worth doing rather than restoring a no-op.
