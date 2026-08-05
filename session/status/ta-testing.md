last_update: 2026-07-30T19:40:00+03:00
state: in-progress
current_step: All planned actions complete — branch refreshed, tag created and pushed, image built and pushed to quay. Dean explicitly authorized both pushes; planner executed them directly. Awaiting Dean's review.

## Branch
ta-testing at .../ta-testing ; tip 6bfb73e1 (= upstream/main tip, tracking upstream/main)
Recreated via `git checkout -B ta-testing upstream/main` — moves the branch pointer only, no new
commits (nothing to DCO-sign). Old assembly (db530eed, the C+D `--no-ff` merge on top of the older
main@11d70a8a) is superseded: C, D, and now E/F have all merged directly into the real upstream
main, so the old merge's content is redundant. That old state remains permanently recoverable via
the `ta-0.9-test-20260728` tag (unchanged, still points at db530eed) — nothing was lost.

## Why the branch pointer moved instead of another --no-ff merge
db530eed predates the real upstream merges of C/D, so it is NOT an ancestor of the current
upstream/main — diverged history, not a fast-forward base. Since C #1480 and D #1481 (the two PRs
this branch used to assemble by hand) are now on upstream/main itself, and E #1502 + F #1503 have
also merged, the simplest correct integration state is upstream/main directly. ta-testing is
disposable-by-design (never an upstream PR), so repointing it loses nothing.

## Content confirmed present (via `git log upstream/main --oneline`)
- f9f04d81 — PR C #1480 (throughput: model-level arrival-rate decode demand)
- f5261c8e — PR D #1481 (saturation: per-analyzer liveness gate on scale-down veto)
- 1d5553ee — PR E #1502 (controller: warn on live ConfigMap edit that can't change TA registration)
- 6bfb73e1 — PR F #1503 (fix throughput+saturation: correctness guards for ThroughputAnalyzer and
  the liveness engine) — current tip
- da58c0e0 — #1486 (ScalingPolicy schema Phase 1 in the saturation ConfigMap) — landed independently
  on the same upstream history, included incidentally as part of "upstream/main tip"

## Local tag — PUSHED
ta-0.9-test-20260730 (annotated, GPG-signed, on 6bfb73e1) — "TA 0.9 integration test build:
upstream/main (6bfb73e1) — includes C #1480, D #1481, E #1502, F #1503". Signature verified via
`git tag -v` (Good "git" signature, key SHA256:q4lKwxmYDY2hZRA3Jzu1DvSfCWWw58BLaL+vuD+VA3w).
**Pushed to origin** (Dean-authorized "quay creds in env. go ahead. push git and docker.";
executed by the planner directly — network-only action, not a worktree file write):
`git push origin ta-0.9-test-20260730` → `* [new tag] ta-0.9-test-20260730 -> ta-0.9-test-20260730`.
Plain, non-force push — the commit it points at (`6bfb73e1`) was already public via `origin/main`.
Previous tag ta-0.9-test-20260728 (on db530eed) preserved unchanged — do not touch, it is the
permanent record of the old hand-assembled C+D state.

## Verified (gates, all from this worktree at 6bfb73e1)
- make test — PASS (all packages ok; envtest suites green, e.g. controller/indexers 7.8s, saturation 4.3s)
- gofmt -l internal cmd — clean (empty). Note: `pkg/` no longer exists on this tip — moved into
  `internal/queueing` by upstream #1448, so the old three-dir gofmt invocation (`./internal/...
  ./pkg/... ./cmd/...`) now 2-for-3; used `internal cmd` (no `./...` suffix — gofmt doesn't expand
  that glob) plus `test/` implicitly covered by go vet/build.
- make lint — 0 issues
- go build ./... — clean

## Image build + push (2026-07-30) — PUSHED
Built locally from 6bfb73e1 (tag ta-0.9-test-20260730) via `make docker-build
IMG=quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9` — native x86_64 docker build (no
buildx), all stages cached/green.
- IMG ref: `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9`
- Local image ID: `sha256:3d438b65c824d2438d4f422eeaebb57f08b22bfb1f2bb16d9ce89e3380dc15af`
- os/arch: `linux/amd64` (Dockerfile builds `CGO_ENABLED=0 GOOS=linux GOARCH=amd64`)
- This local image tag overwrote the previous 2026-07-28 build's tag on the local docker daemon
  (same IMG ref) — the old image ID (`sha256:ce5fac61...`) is no longer tagged locally.
- **Pushed to quay.io** (Dean-authorized, quay creds in his env; executed by the planner directly):
  `make docker-push IMG=quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9` →
  `ta-0.9: digest: sha256:80dec0e9728f4e7d1d06a952f43330e8b1ac5f09592284f87c0e9981c05e19ca size: 3233`.
  **Pushed digest:** `sha256:80dec0e9728f4e7d1d06a952f43330e8b1ac5f09592284f87c0e9981c05e19ca`
  (note: this is the registry manifest digest returned by the push, distinct from the local image
  ID above — both refer to the same build).

## origin/main and origin/ta-testing — independently confirmed (read-only)
Fetched `origin main ta-testing` (before the pushes below):
- `origin/main` = `6bfb73e1` — **identical** to the new ta-testing tip and to `upstream/main`.
  Someone had already fast-forwarded and pushed origin/main to this exact commit before this
  refresh ran, which is why the tag push (below) needed no force/lease handling.
- `origin/ta-testing` = `db530eed` (as of this fetch) — the old pre-refresh state, redundant with
  origin/main. Now genuinely stale/pointless; a separate, non-urgent cleanup, not acted on here.
  The `ta-testing` branch itself was never pushed — only the tag was (see below), since branch
  content was already public via origin/main.

## Pushes — ALL DONE (Dean-authorized, executed by the planner directly)
Dean gave explicit authorization ("quay creds in env. go ahead. push git and docker.") and the
planner ran both pushes directly as network-only actions (not worktree file writes):
1. `git push origin ta-0.9-test-20260730` — **succeeded**: `* [new tag] ta-0.9-test-20260730 ->
   ta-0.9-test-20260730`. Plain, non-force tag push (target commit already public via
   origin/main).
2. `make docker-push IMG=quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9` —
   **succeeded**: `ta-0.9: digest: sha256:80dec0e9728f4e7d1d06a952f43330e8b1ac5f09592284f87c0e9981c05e19ca
   size: 3233`.
No further push/GitHub action is outstanding. This coder session did not run either push itself —
recorded here as reported by the planner; not independently re-verified by this session (not
required per the planner's instruction).

## Notes
This is a TEST-ONLY integration branch — never an upstream PR, never will be. As of this refresh
its "integration" role is nearly vestigial: a plain `main` checkout at 6bfb73e1 already contains
C+D+E+F, so ta-testing's only remaining value is being a stable, tagged, Dean-owned name/image
pipeline pointing at a known-good TA 0.9 SHA — it is no longer hand-assembling anything via merge.

All planned actions for this refresh are now complete: branch repointed, tag created + pushed,
image built + pushed to quay. Work remains `state: in-progress` per convention (only Dean marks
`done`); nothing further is expected from a coder session on this task unless Dean raises
follow-ups.
