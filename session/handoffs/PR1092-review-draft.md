---
to: reviewer
doc: scratch/PR1092-short-draft.md
status: READY
note: PR #1092 (VA CRD removal proposal) — short review comment draft ready; counter-proposal pending integration before Dean posts
---

## Session context

Analysis of PR #1092 (va removal proposal) complete on 2026-05-12. The short review comment
draft at `scratch/PR1092-short-draft.md` is technically and tonally ready to post. Dean is a
non-maintainer contributor; the PR author is a maintainer; the draft is deliberately polite and
fact-stating rather than argumentative.

The draft currently covers:

1. Pluggability (Level 1 / Level 2) is independent of the CRD — does not require removal.
2. Operational burden is unchanged (same data, worse tooling).
3. CRD semantics lost with no stated replacement — status, admission-time validation, lifecycle
   deletion event. The GitOps re-apply concern (annotations silently restored) is in the
   lifecycle paragraph.
4. WVA config bleeds into KEDA objects; persists after uninstall.
5. `VariantAutoscalingConfigSpec` KServe embed contract is broken.

## What is deferred

The counter-proposal (**WVA owns the KEDA ScaledObject as a child resource; user creates only
the VA CRD; WVA auto-generates the Prometheus trigger**) was fully analyzed and exists in
`scratch/PR1092-response-draft.md` (the long draft), but **is deliberately not in the short
draft**. Dean wants to decide how to present it before posting — either:

- Append a separate "alternative worth discussing" section to the short draft, or
- Keep the short draft as-is (concerns only) and propose the counter-proposal in a follow-up
  conversation / separate comment.

KEDA ScaledObject maximal-footprint analysis (what new VA CRD fields would be needed if WVA
owned the ScaledObject) is already done — captured in both `scratch/PR1092-response-draft.md`
and in memory `project_pr1092_analysis.md`.

## Resume points for next session

1. Re-read `scratch/PR1092-short-draft.md` — confirm still aligned with Dean's tone/content.
2. Decide counter-proposal integration approach (append vs defer).
3. If appending: draft a short "alternative" section pointing at the ownership-inversion idea
   without over-specifying.
4. Dean reviews, approves, posts via `gh pr review 1092 --comment -b "$(...)"` — confirm
   explicit authorization per CONVENTIONS "No GitHub actions without explicit confirmation".

## Related artifacts

- `scratch/PR1092-response-draft.md` — long detailed analysis with full counter-proposal
- `scratch/PR1092-short-draft.md` — short draft (the handoff target)
- Memory: `project_pr1092_analysis.md` — full recap including counter-proposal details
