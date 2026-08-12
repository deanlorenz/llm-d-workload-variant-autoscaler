from: benchmark
to: sync
session: benchmark-campaign-migration-and-t9-20260812

## What changed

Four more local commits on `benchmark` this resume, all DCO-signed, nothing pushed (branch now 27
commits ahead of `origin/benchmark`). Two independent tasks:

**1. Migrated the 7 pre-`runs/` campaign directories from 2026-08-10 into the new tree.**
`dean-20260810-{064736-555,072736-888,080708-371,084756-739,092644-320,100827-539,105211-685}/`
moved into `runs/<same-id>/`, `config/`+`viz/`+`REPORT.md` populated/generated for each (56 files).
Commits: `02793145` (the migration), `5486afde` (a real `.gitignore` bug caught in the process — an
unanchored `dean-*/` rule was silently shadowing the config/viz/REPORT.md allowlist for every run
under `runs/`; fixed by anchoring to `/dean-*/`), `135b4590` (deleted the now-redundant
`session-notes/campaign-viz/` figure mirror, verified byte-identical against the new canonical
location first).

**Security check performed before staging anything:** the results doc flags a live OpenShift
bearer token in every cell's `environment/context.ctx`. Verified it is not among the 56 staged
files — checked the `git add --dry-run` file list against the allowlist, then grepped every staged
file for the token pattern, `BASE64_CONTEXT`, PEM blocks, `Authorization:` headers, and
`client-key-data` (zero hits). The token itself is untouched, still on disk, still needs rotation —
that's unchanged from before this session and remains Dean's.

**2. T9 — wired the gateway access-log follower into `benchmark-run`.** Commit `3ab8128a`.
Processed handoff `benchmark__t9-log-follower-wiring.md` (now `.DONE`), which pointed at the
2026-08-12 correction in `ta-pokprod-testing-plan.md` §7.6.1/§9.1: T9 was reframed from "Dean
applies it personally" to "wire it into the run playbook," since every resource in
`gateway-log-follower.yaml` is namespace-scoped and needs no permission beyond what `benchmark-run`
already has. New `BENCHMARK_GATEWAY_LOG_FOLLOWER` flag (default `true`); `benchmark-run` now applies
the follower automatically before load starts, namespace-substituted via `sed` so it isn't
hardcoded to `dhl-wva-209`. Idempotent — the follower Deployment is left running across runs, not
torn down per run (confirmed with Dean: matches the manifest's own "capture retained on PVC"
design).

Full detail: `session/status/benchmark.md` §20.28 (this session's write-up).

## Verification done / not done

Migration: verified via `git add --dry-run` (exactly 56 files, matching the allowlist precisely)
and three independent grep passes for credential leakage (all clean) before staging. T9: verified
via `make -n benchmark-run` (namespace substitution renders correctly in both the `kubectl -n` flag
and the `sed` pass) and validated the substituted YAML as 4 well-formed Kubernetes documents via
`uv run --with pyyaml`. **Neither has been exercised against a live cluster** — no
`make benchmark-run` invocation, no live `kubectl apply`. That remains the one standing gap across
this entire results-tree effort.

## Update CURRENT.md

Under the benchmark entry in § Recent activity: the 7 pre-existing 2026-08-10 campaign directories
are now migrated into the `runs/` tree (56 tracked files, verified clean of the flagged bearer
token); the redundant `session-notes/campaign-viz/` figure mirror is removed; T9 (gateway
access-log follower) is now wired into `benchmark-run` automatically, closing that item in
`ta-pokprod-testing-plan.md` §9.1. **Live-run verification is still the one standing gap** across
the whole results-tree + T9 effort — nothing has touched a real cluster this session either. Four
commits: `02793145`, `5486afde`, `135b4590`, `3ab8128a`. Nothing pushed.

## Open questions / follow-ups

- One stale prose reference in `planning/ta-pokprod-campaign-20260810-results.md` (line 27,
  mentioning `session-notes/campaign-viz/` as something checked for the token leak) now describes a
  deleted directory — a `plans`-branch text fix, not this branch's to make.
- The live-cluster bearer token in `environment/context.ctx` per migrated cell still needs
  rotation — unchanged ask from before this session, still Dean's.
- Next live campaign run is still the natural point to verify the whole results-tree mechanism
  (workspace relocation, config handoff, REPORT.md, pruning, and now T9's automatic apply) end to
  end against real harness output and a real cluster.
