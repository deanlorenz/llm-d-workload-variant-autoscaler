Heads-up for review: this branch was rebased past #1486 (ScalingPolicy Phase 1). Two interactions worth knowing:

- **`cmd/main.go`** had a real conflict (both #1486 and this branch's Commit 1 edit it) — resolved keeping both.
- **`internal/config/config.go`**: the extracted gate now uses `aw.EffectiveType() == "throughput"` to match #1486's sibling change in `engine_v2.go`, so it accepts `- type: throughput` as well as `- name: throughput`. The three-way merge couldn't surface this (it's new code #1486 never touched), so it's a deliberate hand-applied consistency fix, with two new test cases. Full rationale is in the `5614afb4` commit message.
