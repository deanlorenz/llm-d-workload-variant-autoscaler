from: collector-va-attribution
session: collector-va-attribution implemented (issue #1263)

## What changed
Implemented the full plan `planning/collector-va-attribution-plan.md` (issue #1263)
on branch `collector-va-attribution` (off `main@526ce851`).

- Commit: `7157c7d2` — "feat(collector): resolve VA attribution behind an Attributor seam"
  (12 files, +520/-161), DCO-signed.
- All 6 plan steps landed. Detail in `session/status/collector-va-attribution.md`.

Highlights:
- New `internal/collector/attribution` package (Attributor seam + default label
  attributor; uncached `HasLabels` pod LIST per namespace).
- Dropped `llm_d_ai_variant` from all 11 per-replica queries; the 3 throughput
  queries also gained `instance` and now group by `(instance, pod)`.
- `buildInstanceKey` is identity-only; the 3 throughput loops re-keyed by
  instance key — fixes the latent A1 key-mismatch (KV + throughput for the same
  replica now merge into one ReplicaMetrics entry). Regression-guarded by a test.
- `CollectReplicaMetrics` takes an `Attributor`; engine builds it per-cycle in
  `prepareModelData` via new `Engine.APIReader` (set from `mgr.GetAPIReader()` in
  `cmd/main.go`).
- Docs: updated `docs/design/controller-behavior.md`; added
  `docs/developer-guide/variant-attribution.md`.

Gates: gofmt clean, `make test` PASS, `make lint` 0 issues, `go build ./...`
clean, `make manifests` no diff from this change.

## Update CURRENT.md
- New PR-Status row / activity entry for `collector-va-attribution`:
  status **code-complete, in review** (NOT merged). 1 commit `7157c7d2` on
  `main@526ce851`; gates green; awaiting internal code review then Dean push to
  origin. Issue #1263.
- Issues-to-Open: the `llm_d_ai_variant` PromQL-groupby removal item (#1263) is
  now implemented on this branch — move from "FILED, awaiting fold-in-vs-separate
  call" to "in PR (collector-va-attribution)". The earlier ev-shindin
  fold-into-#1260-vs-separate question is moot: #1260 is closed; this is the
  standalone PR.
- A review trigger `review__collector-va-attribution-ready.md` is queued —
  internal code review should run before authorizing the push.

## Open questions / follow-ups
- Pre-existing manifest drift (not mine): `make manifests` on `main@526ce851`
  regenerates `config/base/rbac/manager-clusterrole.yaml` to drop a
  `resourcequotas` rule and `autoscaling` patch/update verbs (no kubebuilder
  markers back them). I reverted it so it stays out of this PR. Candidate infra
  issue to file.
- TA3/#1250 coordination (from the plan's coordination note): this PR normalizes
  the 3 throughput queries and fixes their A1 key-mismatch on main. When #1250
  rebases onto a main containing this PR, TA3's own A1 fix is already present —
  flag to the #1250 owner so they don't double-apply (TA3 also drops the label
  and uses the attributor).
- Out of scope and still open: owner-walk locator #1267 (future Attributor impl),
  nil-vs-zero float semantics #1264.
