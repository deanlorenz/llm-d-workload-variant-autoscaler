# Bad heading level topic

Fixture: a level-2 heading appears after a convention marker, which truncates
the convention at extraction. Nothing else here is wrong.

### convention: truncated-by-a-level-two-heading
description: Its body is cut short by the level-2 heading below.
scope: fixture only
trigger: conv-lint scanning this directory
status: active
origin: fixture for the heading-level check

Body prose that a reader would expect to belong to the convention.

## An interloping level-two heading

Everything from here down is outside the convention as far as extraction is
concerned.
