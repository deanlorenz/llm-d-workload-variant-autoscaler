# Fixture: a member cycle

### collection: cycle-a
description: Points at cycle-b, which points back.
members: cycle-b
trigger: fixture only
status: active
origin: fixture

### collection: cycle-b
description: Points back at cycle-a.
members: cycle-a
trigger: fixture only
status: active
origin: fixture
