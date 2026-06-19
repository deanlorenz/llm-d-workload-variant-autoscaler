last_update: 2026-06-19
state: paused
current_step: Discovery done; 3-task pilot ran via sonnet sub-agents + findings verified against code. BULK RUN PAUSED — spec FORMAT is being redesigned in a separate brainstorming thread; do not generate the remaining 37 specs until the format is settled.
blocked_on: spec-format decision (owned by the original brainstorming thread, NOT this orchestration session)

## Branch
spec-poc at /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/spec-poc
Role: orchestrator for the spec-as-code reverse-coding kit (REV-SPEC.md).
All work is UNCOMMITTED on disk (untracked: REV-SPEC.md, docs/agents/, spec/). Zero source files touched.

## Done so far
- Discovery Phase (spawned discovery-agent, model=sonnet): spec/index.md (D1 api-crd-layer, D2 metrics-collection, D3 scaling-engine, D4 infrastructure; 19 components C01–C19, 9 workflows W01–W09, 12 contracts CT01–CT12) + spec/status.md (6 open questions).
- 40 pending task files in spec/tasks/todo/: 12 contract (P8), 19 component (P6), 9 workflow (P4, Depends-On = participating components).
- Confinement: "## Worktree Confinement" in all 4 agent docs + docs/agents/worker-launch-protocol.md; orchestrator.md references it.
- Code-only decision + step 6 "Doc & intent reconciliation" (REV-SPEC.md + docs/agents/reconciliation-agent.md).

## Done 2026-06-19 (this session)
- PARALLEL SAFETY (Dean's main concern): verified all 40 Targets unique (no write collisions). Guarantees written into worker-launch-protocol.md § Parallel execution safety (unique target, create-only+LOCK, single-file write scope, index/status orchestrator-owned, dirs pre-created, Depends-On advisory only → all 40 safe to run fully parallel).
- Pre-created full spec/domains/** tree (now incl. contracts/internal + contracts/external) → no concurrent-mkdir race.
- CONTRACTS split internal vs external (Dean): edited Target path in all 12 contract task files (file names unchanged, so status.md checklist still valid). Internal (Go interface seams): CT02 Analyzer, CT03 MetricsSource, CT10 Engine, CT11 Actuator. External (boundaries): CT01 VA-CRD, CT04 Prometheus, CT05 K8s-scale, CT06 KEDA, CT07 InferencePool, CT08 LWS, CT09 ConfigMap, CT12 EPP-scrape. Re-verified 40/40 targets unique after edit.
- PLUGGABILITY rule (Dean): added "Abstraction status" content rule to contract-extractor.md (internal vs external + note hardcoded/missing seams; e.g. optimizer has no interface) and component-extractor.md (Public Interfaces must state pluggable-vs-hardcoded). Rules live in agent docs, NOT task files (keeps tasks schema-pure + parallel-safe).

## Done 2026-06-19 (handoff prep)
- Created spec-poc/next-step.md (worktree root) — canonical agent-agnostic tracker: Completed log + Current next step (EXTRACTION, pilot-first) + ⛔ PERMISSION GATE (no agent runs the next step without explicit human go-ahead; continuity note ≠ authorization).
- status.md "Next Step" trimmed to a pointer at next-step.md (single source of truth).
- orchestrator.md: added "## Permission gate" section (don't start a phase without explicit authorization).
- worker-launch-protocol.md: added "Worker execution model" — each worker = one `bob --yolo` instance, DEFAULT model, single task; no Claude model pinning anywhere (the earlier sonnet workaround was a quirk of the Agent-tool harness, not the bob pipeline).
- Handoff model: human starts bob in spec-poc (confined, can't leave); bob reads next-step.md and MUST ask before executing.

## Pilot ran 2026-06-19 (sonnet sub-agents, replacing bob)
- Gave up on bob (worktree-unfriendly: flailed on spawning, DONE-misuse, tried to repoint shared core.hooksPath for its checkpointing). Cleaned up bob's CT02 target + stray .DONE + bob-worktree-smoke.txt.
- Fixed worker-launch-protocol.md lifecycle (explicit running→review→done state table; .DONE ⇒ task file in review/, before the review; done/ only after verification).
- Ran a 3-task pilot via confined sonnet sub-agents (Agent tool, model=sonnet, YOLO/autonomous): CT02 (contract), C05 (component), W07 (workflow). All template-conformant, correct markers, 0 source touched. Now in spec/tasks/review/.
- VERIFIED all sub-agent findings against code (4/4 true): config-injection mismatch (engine_v2.go:124 — all analyzers get *SaturationScalingConfig; masked because non-sat results discarded; cites already-merged PR#1228 = stale comment); QueueingModel not registered via RegisterAnalyzer (typed field + special-case switch engine.go:415-443); Name() "saturation-token-based" vs key "saturation"; no RoleDecode constant. Sub-agent pipeline produces accurate current-state findings.

## NOT done / next — BLOCKED on format
- DO NOT run the remaining 37 tasks yet. Spec FORMAT is under redesign in the original brainstorming thread. Decided there (per Dean 2026-06-19): UML rejected; spec is AI-read/edited (consistency via AI authoring like memory files, NOT a strict DL/schema/checker); markdown w/ structure via md constructs (renders in GH); REVIEW on DERIVED artifacts (AI-generated prose + mermaid, cached in GH), not raw spec. ⇒ current prose extractor templates + the 3 pilot specs are PROVISIONAL; will be re-cast in the new format.
- The format design itself belongs to that other thread ("should be documented somewhere" — possible doc gap). This session = orchestration only.
- When format settles: update the 4 extractor docs to the new md-structured format, re-run the 3 pilot specs, review, then bulk-run the remaining 37 (parallel sonnet sub-agents, pilot-first).
- The 6 open questions in spec/status.md (V1/V2 switch, C19 legacy pkg/ deprecation, pkg/config vs internal/config, EPP token, ns-vs-cluster) — resolve LATER (Dean: documenting current state now; reconciliation + later refactor will fix). Deprecated/inconsistent code to be identified, correct path understood, spec fixed, then deprecated stuff moved to separate package + consistent renames — all FUTURE work, post-rev-coding.
- Discovery-agent omitted Evidence/Confidence sections in index.md/status.md (minor; could backfill).

## Notes
- Agent tool defaults to model claude-opus-4-8 which the subagent key rejects (400) — pass model:"sonnet" when spawning kit agents.
- Nothing committed; nothing pushed. No git/GitHub actions taken.

## 2026-06-19 — foundational brainstorm recovered + relocated; format thread owns next
- The origin discussion (ChatGPT, format vision + pipeline design) was found at spec-poc/chatgpt.md (user-copied). Relocated to plans:
  - RAW (verbatim): scratch/spec-as-code-brainstorm-raw.md
  - SUMMARY (Type-1, rewritten): planning/spec-as-code-design.md  ← settled principles + frameworks-considered + open format items (§6)
- spec-poc cleaned: removed bob hook debris (nested home/ tree) + junk chatgpt.text(56B) + subset chatgpt.txt. RESIDUAL: spec-poc/chatgpt.md still on disk — could NOT auto-remove (harness refuses to re-enter the non-managed spec-poc worktree; deleting a sibling from plans seat is out of scope). Content fully preserved in plans above; remove spec-poc/chatgpt.md manually or in a future spec-poc session.
- REV-CODING PAUSED until the spec FORMAT is decided (open items in planning/spec-as-code-design.md §6). Pilot specs in spec/tasks/review/ are provisional. Rev-coder output quality was excellent; only the result STRUCTURE is undecided.
- These plans-branch additions (scratch + planning + this status) are uncommitted.
