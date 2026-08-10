# Dangling path topic

Fixture: the body cites a path that does not resolve. Nothing else here is wrong.

### convention: cites-a-missing-path
description: Points at a file that is not on disk.
scope: fixture only
trigger: conv-lint scanning this directory
status: active
origin: fixture for the referenced-path check

The rule is spelled out in `docs/does-not-exist.md`, which is exactly the
problem — the pointer outlived the file.
