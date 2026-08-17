# Status files

### convention: status-files-broadcast-liveness
description: One status file per active branch, overwritten in place at meaningful checkpoints; read-only for everyone else, never absorbed into CURRENT.md.
scope: every coder or owning agent, per branch
trigger: session start, after each commit, entering/leaving blocked state, session end
status: active
origin: session/CONVENTIONS.md § Inter-agent communication, Status files — broadcast liveness (C21)

*Status files — broadcast liveness.* One file per active branch at
session/status/<branch>.md, overwritten in place by the coder (or any owning agent) at
meaningful checkpoints: session start, after each commit, when entering or leaving a
blocked state, at session end. Read-only for everyone else. Never absorbed into
CURRENT.md, never deleted by the planner — dropped when the worktree is removed. Status
is operational/ephemeral; CURRENT.md is canonical project state.

### convention: status-files-every-agent-keeps-state
description: Every agent keeps its own state under plans/ and commits it; an uncommitted state file is one checkout away from gone.
scope: coders, planners, reviewers — everyone
trigger: writing your own state (status file, Type 3 doc)
status: active
origin: session/CONVENTIONS.md § Inter-agent communication, Every agent keeps its own state and commits it (C22)

**Every agent keeps its own state, and commits it.** This applies to coders, planners, reviewers —
everyone. State normally lives under plans/ (your session/status/<branch>.md, your Type 3 in
`planning/`); write it there, and **`git commit` it** rather than leaving it in a working tree. An
uncommitted state file is one `checkout` away from gone and is invisible to every other session. If a
tool or permission boundary blocks you from writing the canonical location, write it where you can,
say so in your handoff, and flag the cleanup — do not silently keep state in a second place. A
duplicate that nobody has declared is worse than an awkward path, because the next session cannot tell
which copy leads.

### convention: status-files-identity-block
description: Mandatory identity block at the top of every status file so a handoff's to: field can express role+task, not just a topic or branch name that two sessions might share.
scope: every session writing a status file
trigger: session start, a role or task change, resume from sleep or restart
status: active
origin: session/CONVENTIONS.md § Inter-agent communication, Identity block (C23)

**Identity block — mandatory, at the top of every status file.** A recurring failure (incident
2026-08-13, see planning/governance-follow-ups.md) is a handoff's `to:` field naming a topic or
branch when two sessions — say a coder and a planner — are both working that same topic at once;
the recipient token has no way to say *which role* it means, so the wrong session claims it. The
fix starts here: every session states its own identity explicitly, in its own status file, so
anything needing to address it precisely has something unambiguous to read. Restate this block
whenever it changes — session start, a role or task change, resume from sleep or a restart — not
only at first write:

```
name: <session's own display name/title, if it has one>
id: <session id, if available>
role: <coder | planner | reviewer | designer | sync | ...>
branch: <branch>
worktree: <absolute path>
owned_doc: <path to the plan/spec/design doc this session is executing or authoring>
task: <one line — the specific unit of work right now>
status_file: <path to this file — self-referential, but makes a copy self-describing>
```

Then the existing fields below. A handoff's `to:` should increasingly express **role + task**
("planner, autoscaling-viz-panel3-redesign") rather than a bare topic name, and fall back to a
concrete session name only once a reply has established which specific session is on the other
end of an exchange — keep it short regardless; token overhead on handoff routing is a standing
concern, not just a correctness one.

```
last_update: <ISO timestamp>
state: in-progress | blocked | idle | done
current_step: <one line>
blocked_on: <one line, only if state=blocked>
recent_commits:
  - <sha> <subject>
notes: <freeform, optional>
```

### convention: status-files-coder-format
description: Coder-side status file format: fixed path, full-snapshot rewrite (not append-only) at every meaningful checkpoint, state stays in-progress until Dean reviews.
scope: coder agent
trigger: session start, after each commit, after test/build/verification, hitting a blocker, before pausing
status: active
origin: session/CODER-CONVENTIONS.md §5.1 Status file — living progress log (CC12), plus §9.1 template (CC20, status fragment)

**5. Status file (living) and handoffs (one-shot).**

Two separate artifacts under plans/session/. Don't conflate them.

**5.1 Status file — living progress log.**

Your status file is your continuous heartbeat. One file per branch,
fixed path, overwritten in place at every meaningful checkpoint:

```
plans/session/status/<branch>.md
```

A monitoring agent or Dean reads it to see where you are without
interrupting your session. Stale status looks like a crashed session.

**Format** — see §9.1 template. Suggested fields per CONVENTIONS:

```
last_update: <ISO timestamp>
state: in-progress | blocked | idle | done
current_step: <one line>
blocked_on: <one line, only if state=blocked>
recent_commits:
  - <sha> <subject>
notes: <freeform, optional>
```

Status starts as `in-progress` and stays that way until Dean reviews.
Never write `state: done` yourself.

**When to rewrite** (full snapshot each time; not append-only):

- Session start: initial entry with your understanding of scope and
  what you plan to land.
- After each commit: update `recent_commits` and `current_step`.
- After each test run / build / verification: reflect in `notes` if
  something noteworthy.
- When you hit a question, blocker, or judgment call: flip
  `state: blocked` and fill `blocked_on`; keep working if you can on a
  different track, or stop and wait if it gates everything.
- Before pausing for any reason (end of session, waiting on review): one
  final write reflecting current state.

The status file is **broadcast, not directive.** Other agents may read
it to inform their own actions, but they never absorb it into CURRENT.md
or take instructions from it. If a sibling needs your output, the
sibling's own plan tells them what to do — your status is just a hint
that something moved.

**9.1 Status file** (plans/session/status/<branch>.md)

Rewrite this file in place at every checkpoint (see §5.1). `state` stays
`in-progress` until Dean reviews; never write `state: done` yourself.

```
last_update: <ISO timestamp>
state: in-progress | blocked
current_step: <one line — what you are doing right now>
blocked_on: <one line, only if state=blocked>

 ## Branch
<branch> at <worktree path> ; tip <commit-sha-short>

 ## Recent commits
- <sha> — <message>
- ...

 ## Tests added / moved
- <test file>:<spec> — <one-line description>
- ...

 ## Verified
- make test — PASS                                      # WVA-specific
- gofmt -l ./internal/... ./pkg/... ./cmd/... — clean   # WVA-specific
- go build ./... — clean
- (any -race or scenario-specific runs)

 ## Developer guide
- <path> — <what was added/changed>

 ## Open questions for Dean
- <question 1>
- ...

 ## Not done / known limitations
- <item>
- ...

 ## Notes
<freeform>
```
