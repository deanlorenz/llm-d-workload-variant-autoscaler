# Rename fixtures

Fixture file. The conventions below are illustrative, not authoritative.

### convention: old-name
description: A convention that exists to be renamed.
scope: conv-rename test fixtures only
trigger: running the conv-rename golden suite
status: active
origin: conv-rename S3 test fixture

Cited from both cite-dirs, so a rename has to rewrite more than one file, and a
deletion has more than one refusal to name.

### convention: other-name
description: The name a rename is refused for colliding with.
scope: conv-rename test fixtures only
trigger: running the conv-rename golden suite
status: active
origin: conv-rename S3 test fixture

Renaming onto this name must be refused: two conventions sharing a name make
every fetch of it ambiguous, which is the failure the whole no-index design
rests on not happening.

### convention: lonely-name
description: A convention nothing cites.
scope: conv-rename test fixtures only
trigger: running the conv-rename golden suite
status: probation
origin: conv-rename S3 test fixture

Nothing cites this one, so it carries the rename-with-no-citations case and both
deletion cases, the refused one and the approved one.
