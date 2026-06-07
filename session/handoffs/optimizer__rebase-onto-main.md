reason: re-read plan
refs:
  - planning/multi-analyzer-optimizer-plan.md
note: #1228 merged to main (d9e4ae1f); origin/main fast-forwarded. Optimizer must rebase onto main — see plan § "Rebase onto main (post-#1228 merge) — CURRENT NEXT ACTION". It's a complete single-pass spec: pre-rebase plan doc, exact `git rebase --onto main b8b823b0` command, expected-conflict files + resolution, per-file diff inventory, grep-to-zero, behaviour backstops, gates. Do it once, verify, hand off. Do not push (Dean force-with-lease pushes after review). PR targets main after.
