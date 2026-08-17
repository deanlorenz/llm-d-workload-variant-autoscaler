# role: pr

token:  pr
owns:   review of a GitHub PR
reads:  the PR

## What

Reviews the PR as a GitHub artifact — not code-in-diff (that is `verify`'s and the upstream project's
own `pr-review` skill's job). Explicitly disambiguated in `doc-and-session-model.md`: "`pr` is not the
upstream project's `pr-review` skill, which reviews code inside a PR diff. This role reviews the PR as
a GitHub artifact."

## Gap, skipped per Dean's instruction

Zero skill coverage, zero harvested kernel content. `doc-and-session-model.md` § Skill surface lists
this among "Missing entirely." No rule anywhere defines what "reviewing the PR as a GitHub artifact"
concretely checks (description accuracy? title? scope-vs-diff match? labels/reviewers?). Per Dean's
explicit instruction ("gaps for new roles, not a problem, skip those"), this is left unfilled rather
than invented — build when real source material exists.

origin: doc-and-session-model.md § Roles, § Skill surface
