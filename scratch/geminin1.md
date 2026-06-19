This refined topology solves the workspace mapping problem perfectly. It preserves your exact VS Code multi-workspace layout, aligns data ownership with access control boundaries, and eliminates multi-session synchronization friction by offloading it entirely to Git.

## **1\. Unified Workspace Topology**

By separating **Project Invariants** (Source, Tests, Team-Shareable Drafts) from **Execution Frameworks** (Global Modes, System Prompts, Private Session State), you achieve a clean, modular structure.

📁 \<workspace-root\>/                              ← Open as a VS Code Multi-Root Workspace  
├── 📁 llm-d-workload-variant-autoscaler/        ← Main OS Project Root (Your Fork / Private Team Origin)  
│   ├── 📁 main/                                 ← VS Code Folder 1 (Code Branch)  
│   ├── 📁 TA1/                                  ← VS Code Folder 2 (Code Branch)  
│   └── 📁 plans/                                ← VS Code Folder 3 (Orphan branch, team-shared Type 1-3 docs)  
│  
└── 📁 os-plans/                                 ← Separate Central Private Repo (Your Eyes Only)  
    ├── 📁 .modes/                               ← Global, reusable prompt boundaries  
    │   ├── 📄 brainstorm.md  
    │   └── 📄 code.md  
    └── 📁 session/                              ← Private transient execution states  
        └── 📁 wva-autoscaler/                   ← Project tracking data

## ---

**2\. Strict Data Ownership & Lifecycle Splits**

Your approach sets clean boundaries for where files live based on their purpose:

| File Type / Taxonomy | Primary Location | Access Controls | Team Alignment Strategy |
| :---- | :---- | :---- | :---- |
| **Source & Type 4 Docs** | wva-autoscaler/\<branch\>/ | Public / Team Upstream | Standard Git PR workflow via code branches. |
| **Types 1, 2, 3 Drafts** | wva-autoscaler/plans/ | Team Fork (Private/Internal) | Pushed to *your origin fork* of the OS repo. Shared with internal teammates, completely hidden from public upstream PR diffs. |
| **Global Modes & Rules** | os-plans/main/ | Personal Private Repo | Cherry-picked or dynamically evaluated across all your OS projects. |
| **Type 5 Session State** | os-plans/\<project-branch\> | Personal Private Repo | Uses Git branches as isolated state machines for parallel execution. |

## ---

**3\. Git Branches as Isolation & Synchronization Engines**

Instead of treating the private os-plans repo as a static folder, **give each active OS project its own tracking branch inside os-plans**.

                                      ┌───► branch: wva-autoscaler  (Private Session State)  
                                      │  
\[os-plans.git\] ──► branch: main ──────┼───► branch: project-b       (Private Session State)  
              (Global Modes & Rules)  │  
                                      └───► branch: project-c       (Private Session State)

## **The State Synchronization Protocol**

1. **Isolation:** When you run parallel terminal windows on different features (e.g., TA1 vs TA2), you spin up your execution agent by targeting the corresponding tracking branch inside os-plans.  
2. **Zero Conflict Execution:** If Agent 1 writes a session log for TA1 and Agent 2 writes a session log for TA2, they write to different tracking areas or independent commit histories within os-plans.  
3. **Merging Invariant Updates:** If you refine a universal rule inside \[Mode: Code\] while working on the autoscaler project, you commit it to your local tracking branch, then merge it back upstream:  
   git \-C os-plans checkout main  
   git \-C os-plans cherry-pick \<commit\_id\_from\_wva\_branch\>

## ---

**4\. Mode Profile: Environment Synchronization (sync-env)**

To automate this workflow without manual script execution, create a dedicated operational mode file within your private hub at **os-plans/.modes/sync-env.md**:

\# Mode Profile: Sync Environment  
Role: Workspace Orchestrator  
Scope: Cross-repository synchronization, state reconciliation, and prompt injection.

\#\# Allowed Tool Boundaries  
\- READ/WRITE: Authorized to operate across both the local OS Project tracking layers and the private \`os-plans/\` directory tree.  
\- PROHIBITED: Under no circumstances may this mode modify application source files (\`\*.go\`) or execute test suites.

\#\# Execution Directives  
When called, your job is to run the following sequence:  
1\. Parse the current active branch of the code worktree using \`git branch \--show-current\`.  
2\. Pull latest state tracks from the private \`os-plans\` repository for this project.  
3\. If structural updates exist in the global \`os-plans/main\` branch, safely rebase or cherry-pick them into the current active project execution context.  
4\. Output a clean session readiness profile for the incoming Coder or Plan agent.

## ---

**5\. Transition Strategy**

To apply this pattern to your current setup, run through these next steps:

* **Provision Private Core:** Initialize your private os-plans repository locally alongside your existing workspace components.  
* **Migrate Modes:** Place the modular .modes/ directory directly into the private repository's main branch.  
* **Establish Team Plans:** Ensure the plans/ worktree under your main OS folder is tracked as an independent branch pushed only to your internal team's origin fork.  
* **Wire Dynamic Walk-Ups:** Update your workspace global shortcuts so your execution agent reads constraints from your private os-plans tree while working inside the local code workspaces.

Would you like to build out the **exact shell initialization sequences** for wiring your cross-repository dynamic walk-ups, or look at how to structure a **GitHub Action file for your private team fork** to validate the team-shared plans branch?