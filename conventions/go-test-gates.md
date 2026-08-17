# Go test gates

### convention: go-test-gates
description: WVA-specific test/build/lint gates a coder runs: make test, gofmt, make lint, go build, -race where relevant.
scope: coder agent
trigger: after each substantial change, before calling work done
status: active
origin: session/CODER-CONVENTIONS.md §3 Tests — write and run (CC7)

**3. Tests — write and run.**

- Add unit tests for every new behavior. Migrate or move existing tests
  when the plan doc says to.
- Run the project's test suite after each substantial change. All tests
  must pass before you call work done.
  - `make test` (WVA-specific) is the canonical entry point. It wraps
    `go test ./internal/... ./pkg/... ./cmd/...` plus any project-
    specific flags. Use `make test` rather than invoking `go test`
    directly.
- Run `gofmt -l ./internal/... ./pkg/... ./cmd/...` (WVA-specific) — must
  be empty.
- Run `make lint` (WVA-specific) — must be clean. This runs golangci-lint
  with the repo's `.golangci.yml` (nakedret, unparam, gocritic, staticcheck,
  …). **It is a required gate, not optional** — CI's `lint-and-test` job
  blocks on it, and `gofmt` / `go build` / `make test` do NOT catch these
  findings (they compile and pass tests). `make lint-fix` auto-fixes the
  mechanical ones. Run it before declaring work done, not just before push.
- Run `go build ./...` — must be clean.
- Use `-race` when relevant (especially for concurrency-sensitive code).

If a test fails for reasons outside your scope (pre-existing breakage on
main), note it in your status file and continue — do not fix unrelated
tests.
