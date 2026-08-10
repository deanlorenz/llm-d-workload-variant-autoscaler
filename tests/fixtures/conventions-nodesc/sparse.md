# Sparse topic

Fixture file. Holds one well-formed convention and one that is missing its
`description` field, so the description-less path can be exercised without
making the well-formed fixture directory defective.

### convention: has-a-description
description: A normal convention, present so the file is not all defect.
scope: fixture only
trigger: conv-list scanning this directory
status: active
origin: fixture

Body prose.

### convention: missing-its-description
scope: fixture only
trigger: conv-list scanning this directory
status: probation
origin: fixture for the missing-description path

No `description` field above on purpose. It must still be listed, with a
visible placeholder — being skipped is what would hide it.
