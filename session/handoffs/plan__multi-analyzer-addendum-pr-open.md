from: multi-analyzer-addendum
session: pr-open

## What changed

PR #1266 opened 2026-06-12, base main, reviewer ev-shindin.
Branch tip: 0eeb659c. 6 commits. All gates green (gofmt, make test, make lint,
go build, DCO 6/6).

## Update CURRENT.md

Add to PR Status table:
| multi-analyzer-addendum | #1266 | **PR #1266 OPEN** (base `main`, reviewer ev-shindin) 2026-06-12; 6 commits, all CI green. Addendum to #1246. | `0eeb659c` |

Add to Recent activity (head):
- **2026-06-12 — PR #1266 opened** (`multi-analyzer-addendum`, tip `0eeb659c`).
  Addendum to #1246: disabled-analyzer veto bug fix (`effectiveEnabled` helper),
  config-bridge + non-uniform Score tests, full rewrite of
  `docs/developer-guide/multi-analyzer-pipeline.md` (architecture diagram,
  data model, optimizer internals). Reviewer: ev-shindin.

Update "Issues to Open" — remove the dev-guide polish item (now landed in #1266):
  "Multi-analyzer dev-guide polish — fold design content ... once #1225/#1228/#1246
  reach final shape." → done; close this item.

Update Next steps: add "Await ev-shindin review of #1266."
