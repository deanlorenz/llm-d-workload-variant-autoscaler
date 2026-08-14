to: benchmark
reason: re-run postprocess against 4 pre-fix staircase runs
refs:
  - planning/ta-pokprod-history.md#D-39
  - planning/ta-pokprod-campaign-report-v2-spec.md
note: Dean-approved 2026-08-14, no cluster contact needed -- raw per-request/stage lifecycle data
  already exists on disk for all 4. Run IDs: dean-20260810-064736-555, dean-20260810-072736-888,
  dean-20260810-080708-371, dean-20260810-084756-739. Each currently shows TTFT/ITL/queue-depth as
  "?" in REPORT.md, predating the D-39 postprocess.py fix (2026-08-12) -- same missing-field bug,
  never re-extracted after the fix landed.
