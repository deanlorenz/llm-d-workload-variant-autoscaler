# Fixture: role collections, against tests/fixtures/conventions

### collection: coder-fixture
description: A coder's conventions, fixture version.
members: commit-message-shape, one-commit-per-step
trigger: session start, as a coder
status: active
origin: fixture

### collection: nested-fixture
description: Wraps coder-fixture plus one direct convention, to exercise nesting.
members: coder-fixture, no-dco-on-plans
trigger: fixture only
status: active
origin: fixture
