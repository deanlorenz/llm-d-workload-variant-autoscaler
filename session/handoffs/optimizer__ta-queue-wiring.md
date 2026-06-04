reason: re-read plan
refs:
  - planning/TA-PR5-plan.md
  - planning/multi-analyzer-optimizer-plan.md
  - engine-queue-fix worktree, tip 01ed7d8d
note: TA-PR5 needs SchedulerQueue wired through to AnalyzerInput for non-saturation analyzers. engine-queue-fix already does this (1 commit, generic over the analyzer slice). Open question: absorb into multi-analyzer-optimizer or land as a standalone follow-up. Not TA-specific.
