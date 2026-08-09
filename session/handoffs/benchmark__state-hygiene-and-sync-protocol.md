to: benchmark
reason: re-read conventions — two new rules on state keeping, plus a duplicate state file to reconcile
refs:
  - session/CONVENTIONS.md (§ Status files — "Every agent keeps its own state, and commits it")
  - session/CONVENTIONS.md (§ Handoff format — "A `sync__` handoff must carry two things")
  - plans/session/status/benchmark.md
  - benchmark/session-notes/status/benchmark.md
note: the two paths above are byte-identical (170,783B); the benchmark-branch copy is committed and clean, the plans copy has 2,602 lines uncommitted with zero unique content — no loss, but two copies with no declared authority. Dean's direction 2026-08-09: the cleanup and a `sync__` handoff back are the coder's.
