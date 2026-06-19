*I would like a downloadable document that captures our discussion. Our discussion included both brainstorming and planning \-- the downloadable documents should include the concepts, design, and plan.I will execute the plan in a dedicated session.*

I have structured and packaged our entire architectural discussion into three distinct markdown documents. These are optimized for direct ingestion by an AI agent when you launch your next dedicated execution session.

## **📄 Session Artifacts**

## **📁 CONCEPTS.md (System Concepts)**

`# System Concepts: Modular AI Mode Architecture`

`## 1. Core Paradigm Shift`  
`Instead of relying on monolithic configuration files or complex vendor-specific extensions (like tools or plugins), this architecture treats **AI Session Modes as first-class, immutable markdown profiles**.`

`* **Ephemeral Activation:** Modes are injected dynamically at session startup via initial prompts or slash commands. This ensures complete independence between parallel terminal windows, avoiding file-write synchronization conflicts.`  
``* **Separation of Concerns:** Project-wide coordination rules remain in `CONVENTIONS.md`, while specific tool constraints, read/write permissions, and behavioral boundaries are completely offloaded to dedicated mode profiles.``  
`* **Universal Compatibility:** By framing boundaries in structured markdown tables and XML blocks, the system forces compliance from any advanced LLM system prompt engine (Claude, Bob, Open Interpreter, Aider), making it fully platform-agnostic.`

`## 2. Directory Layout & Discovery Mechanics`  
`The system leverages a filesystem walk-up directory tree resolution strategy to ensure mode files and custom capabilities are discovered dynamically across decoupled git worktrees.`

/  
├── .claude/  
│ ├── commands/  
│ │ └── work.md → Symlink to plans/.claude/commands/work.md  
│ └── skills/  
│ ├── s-sync-current → Symlink to plans/.claude/skills/s-sync-current  
│ └── s-onboard → Symlink to plans/.claude/skills/s-onboard  
├── main/ ← Code Worktree  
├── TA1/ ← Code Worktree  
└── plans/ ← Permanent Orphan Planning Worktree  
├── .modes/ ← Modular Mode Boundaries Directory  
│ ├── brainstorm.md  
│ ├── plan.md  
│ └── code.md  
└── session/  
└── CONVENTIONS.md ← Global Project Governance

## **📁 DESIGN.md (Architecture Design)**

`# Architecture Design: Modular Mode Boundaries`

`This design decouples behavior rules into modular profiles. Each file governs an isolated role.`

`## 1. Mode Rule Contracts`

``### Mode Profile: Brainstorm (`plans/.modes/brainstorm.md`)``  
`* **Role:** Plan Agent`  
`* **Scope:** High-level conceptualization, architectural design, technology selection.`  
`* **Allowed Reads:** Universal workspace-wide read access.`  
``* **Allowed Writes:** Restricted strictly to `plans/planning/` (Type 1 - Design docs) and `plans/scratch/`.``  
`* **Prohibited Actions:** NEVER write, edit, or create implementation source code or task plans. Refuse and emit a scope warning if prompted. No git push operations allowed.`

``### Mode Profile: Plan (`plans/.modes/plan.md`)``  
`* **Role:** Plan Agent`  
`* **Scope:** Decomposing epics/milestones into granular, per-PR task lists.`  
``* **Allowed Reads:** `plans/planning/` (Types 1 & 2), Type 6 Reviews (**FINAL status only**).``  
``* **Allowed Writes:** Restricted strictly to `plans/planning/` (Type 3 - Task Plans).``  
`* **Prohibited Actions:** NEVER edit or write implementation source code. NEVER alter Type 1 docs without architectural replanning authorization.`

``### Mode Profile: Code (`plans/.modes/code.md`)``  
`* **Role:** Coder`  
`* **Scope:** Active implementation of features, unit tests, and reference documentation.`  
``* **Allowed Reads:** `plans/planning/` (Type 3 Task Plans), active worktree `docs/` (Type 4).``  
``* **Allowed Writes:** Active code worktree (`src/`, `test/`), active `docs/` (Type 4).``  
``* **Prohibited Actions:** NEVER edit files inside the `plans/planning/` directory. NEVER edit `session/CURRENT.md` directly; all state must go through handoff files.``

`## 2. Dynamic Command Ephemeral Interface`  
`To invoke a mode without writing active state to disk, custom interfaces convert arguments into inline system instructions dynamically:`

```` ```markdown ````  
`---`  
`description: Initialize a session in a specific workflow mode. Usage: /work <mode_name> <task>`  
`---`  
``Read and strictly adhere to the mode constraints defined in `plans/.modes/$ARGUMENTS[0].md`.``  
`Ensure your tool calls, reading, and writing bounds match its defined profile.`

`Execute the following task within that mode: \$ARGUMENTS[1]`  
```` ``` ````

## **📁 PLAN.md (Execution Blueprint)**

`# Execution Plan: Decoupling CONVENTIONS & Onboarding Modes`

`This step-by-step blueprint transitions the repository from integrated rules to the modular mode architecture. Execute this sequence inside a dedicated session.`

`## Phase 1: Directory Setup & Structural Separation`  
``- [ ] Initialize session within the `plans/` worktree.``  
`` - [ ] Create the target modes directory: `mkdir -p plans/.modes/` ``  
``- [ ] Create files for each profile: `brainstorm.md`, `strategizing.md`, `plan.md`, `code.md`, `review.md`, `fix.md`, `triage.md` under `plans/.modes/`.``  
`- [ ] Populate each mode file with its respective modular constraints, roles, and read/write scopes.`

`## Phase 2: Refactoring CONVENTIONS.md`  
``- [ ] Open `plans/session/CONVENTIONS.md`.``  
``- [ ] Extract and remove any agent-specific or mode-specific rules that have been migrated into `plans/.modes/`.``  
``- [ ] Ensure `CONVENTIONS.md` cleanly retains global invariants: Repository layout, taxonomy tables, worktree-scoping mechanics, shared-state handoff rules, and git pre-push checklists.``  
`` - [ ] Commit these operational changes directly to the permanent plans branch: `git -C plans add . && git -C plans commit -m "chore: modularize session modes and refactor conventions"` ``

`## Phase 3: Interface Wiring & Verification`  
``- [ ] Create or update the global workflow shortcut under `plans/.claude/commands/work.md`.``  
``- [ ] Re-link global configurations by ensuring symlinks at the project root point accurately back to your orphan `plans/` branch tracks.``  
``- [ ] Execute a sandboxed test session running `/work brainstorm` to verify that the agent cleanly reads your new modular boundaries and successfully rejects a mock file-write request to a code file.``

When you are ready to begin the implementation, you can paste the text inside **PLAN.md** directly into your terminal workspace session to orchestrate the refactor step-by-step. Let me know if you would like to expand on any **fallback parameters** before starting\!