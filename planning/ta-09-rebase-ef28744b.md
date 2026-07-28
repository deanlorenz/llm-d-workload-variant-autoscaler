# TA 0.9 forward-rebase plan — `55e24be9` → `ef28744b`

**Type 3 (ephemeral).** Delete after all four rebases are verified and force-pushed.
**Author:** plan-agent. **Date:** 2026-07-28.

## Why

The four TA 0.9 branches were based on last-good `55e24be9` because the then-upstream
tip (`aa86a2a9`) did not compile (interfaces→domain rename fallout). That fix has since
merged to upstream `main`:

- `fafbc4dd` — the interfaces→domain fix (merged as **#1483**; the earlier #1477 was
  closed as superseded).
- `ef28744b` — **current upstream/main tip**: "fix(saturation-v2): charge waiting
  requests by P/D role (#1470)", sits on top of `fafbc4dd`.

Because each PR's `lint-and-test` job tests *head-merged-into-current-base* and the base
now compiles, the red CI on #1478–#1481 is stale. Forward-rebasing onto `ef28744b`
brings each branch current, removes the stale-merge-ref ambiguity, and gives a clean
final merge.

**Rebase-safety pre-check (plan-agent, read-only, done):** `git merge-tree
--write-tree --merge-base 55e24be9 ef28744b <tip>` returned **CLEAN for all four**.
`engine.go` / `engine_v2.go` are touched on both sides (#1470/#1483 vs. our branches) but
in disjoint hunks; the docs our branches touch (`multi-analyzer-pipeline.md`,
`throughput-analyzer.md`) are not in main's `55e24be9..ef28744b` diff. merge-tree
simulates the final merge, not per-commit replay — a mid-stack conflict is still
*possible* though unlikely; if one appears, stop and surface it rather than improvising.

## Branches (all base `55e24be9`, rebase `--onto ef28744b 55e24be9`)

| Br | Branch | PR | pre-rebase tip | # commits |
|----|--------|----|----------------|-----------|
| A  | `ta-devguide-fixes`      | #1478 | `93742a52` | 4 |
| A′ | `ta-registration-safety` | #1479 | `89337622` | 5 |
| C  | `ta-model-level-demand`  | #1480 | `68681542` | 4 |
| D  | `ta-veto-liveness`       | #1481 | `faab066a` | 6 |

Command per worktree:
```
git rebase --onto ef28744b 55e24be9
```

## Per-commit "behavior to preserve" (mined from commit messages)

The coder must confirm each of these survives the rebase (see verification checklist).
Files expected to interact with the new base: `internal/engines/saturation/engine.go`,
`internal/engines/saturation/engine_v2.go` (both changed by #1470/#1483 on the new base).

- **A (docs-only):** I-21 stale PromQL groupby examples fixed; I-22 removed-file
  reference dropped; I-23 nKV/booting-replica supply note; NTH-1 `port` label fix. No
  Go code — rebase is doc-only; overlap risk near zero.
- **A′:** `effectiveEnabled` opt-in (config-absence veto) + startup non-registration log
  + dev-guide + F1/F2 follow-ups. Touches `engine_v2.go` region → confirm the opt-in gate
  logic and startup log are intact after replay.
- **C:** model-level arrival demand (`Λ_req×avgOL`) + nKV-weighted `avgOL` across
  non-prefill variants + `ArrivalRate` dev-guide row. Touches saturation engine + collector
  → confirm the model-level demand computation and the nKV-weighting survive; run the
  regression test that pins the weighted `avgOL`.
- **D:** per-analyzer liveness gate (uninformative analyzer cannot veto scale-down);
  static-QM `Live:true`; per-tuple `(namespace, modelID, analyzerName)` keying;
  `lastGoodAnalysis` staleness window; dev-guide prose. Touches pipeline + engine →
  confirm the liveness gate and per-tuple keying survive; run the discriminating keying
  test and the QM scale-down test.

## Verification checklist (per branch, after rebase, before declaring done)

1. **Per-file diff inventory** — for `engine.go` and `engine_v2.go` (the files that moved
   on the new base), run `git diff <pre-rebase-tip> HEAD -- <file>` and confirm every
   behavior claimed in that branch's commit messages is still present. (A is doc-only;
   skip for A.)
2. **Per-commit message-vs-diff check** — `git log --stat` the rebased range; confirm no
   commit lost hunks to a silent three-way drop.
3. **Full gates** (now against the newest saturation engine in the base):
   - `make test` — PASS
   - `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty
   - `make lint` — clean
   - `go build ./...` — clean
   - `-race` on D (liveness/keying concurrency): `go test -race` on the affected packages.
4. **DCO** — `git log ef28744b..HEAD --format="%b" | grep -c Signed-off-by` equals the
   commit count; every commit carries `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`.

## Out of scope for the coder

- **No push.** Coder reports back via handoff; Dean force-pushes each branch with
  `--force-with-lease` after confirming (each has an open PR → warn/confirm per branch).
- **No PR-body / CURRENT.md edits.** The stale "#1477 / CI red" caveat in the four PR
  bodies and in CURRENT.md is planner/Dean territory — dropped after the force-push lands.

## Addendum 2026-07-28 — D (#1481) CI re-trigger via tip amend

After the force-push, A/A′/C `lint-and-test` re-ran green, but **D's `pull_request`
workflow never dispatched** (GitHub dropped the webhook — only the
`pull_request_target` signed-commits job fired). A close+reopen of #1481 did **not**
re-fire it (no `pull_request` run created; nothing held awaiting approval). The only
reliable re-trigger is a fresh `synchronize` event = a new head SHA.

**Coder task (D / `ta-veto-liveness` only):** amend the tip to change its SHA without
changing content or commit count:

```
# in the ta-veto-liveness worktree, tip 832baa08
git commit --amend --no-edit -s
```

- `--no-edit`: message unchanged. `-s`: keep the DCO sign-off (do not duplicate — if
  amend would add a second `Signed-off-by`, drop the flag; verify exactly one remains).
- New tip SHA ≠ `832baa08`; **still 6 commits** off `ef28744b`; tree byte-identical.
- Re-verify the DCO line count (6/6) and that `git diff 832baa08 HEAD` is empty (content
  identical — only the commit metadata/SHA changed).
- **No push** — report the new tip; Dean force-pushes (`--force-with-lease`) to fire the
  `synchronize` event that re-dispatches `lint-and-test`.
- No other branch is touched — A/A′/C are already green.

## Post-rebase (plan-agent / Dean, not the coder)

- Force-push all four `--force-with-lease` (Dean-confirmed, per-branch PR warning).
- Update the four PR bodies to drop the now-stale CI caveat (main compiles; fix landed as
  #1483). Update CURRENT.md PR Status rows + head abstract to reflect the forward-rebase
  and green CI.
- Delete this plan doc once verified.
