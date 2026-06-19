# Spec-as-Code — Design Synthesis

**Type:** 1 (design). **Status:** DESIGN INPUT — vision + principles settled; the concrete
spec **format is not yet finalized** (open item below). Do not treat as implementable yet.

**Sources:**
- [`scratch/spec-as-code-brainstorm-raw.md`](../scratch/spec-as-code-brainstorm-raw.md) — full origin
  discussion (ChatGPT transcript, 2026-06). Verbatim; this doc is the rewrite/summary.
- `spec-poc` worktree — the reverse-coding **kit** that operationalizes the pipeline half
  (`REV-SPEC.md`, `docs/agents/*`). See also memory `project-spec-poc-rev-coding`.
- Related: `project-workflow-architecture-directions` (memory), `scratch/gemini{1,2,3}.md`.

---

## 1. Goal / vision

Move "one level up the stack": the artifact a human reviews and an AI authors becomes a
**structured, high-level spec — "logical code"** — and source code becomes **evidence that the
spec was implemented**. Not `spec → codegen → code` (the failed MDA/UML model), but
`spec → AI coder → code`. AI changes the economics: the spec only needs to be precise enough for
an agent to regenerate/modify code correctly — far lower fidelity than mechanical codegen.

The spec is the primary review surface and must support three projections:
- **→ code** — an agent regenerates/modifies implementation from it.
- **→ docs/diagrams** — derived human views (mermaid, prose, architecture docs).
- **→ "evaluation"** — an agent *reads* it to find gaps, contradictions, orphans (AI-evaluated,
  **not** a strict schema/validator).

This is *reverse* now (code → spec) only to learn the format and seed content; the real direction
is prose proposal → spec → code.

## 2. Settled principles

1. **Don't invent a modeling language — build a maintenance workflow.** No bespoke DSL, no new
   schema language. (This supersedes the "contract-DSL + grammar + checker" idea explored in the
   orchestration session.)
2. **Markdown only.** Renders natively in GitHub; reviewable via PRs; no external tooling to
   browse. Backstage/YAML-catalog tools rejected for this reason (must live in GH with the repo).
3. **Constrained markdown is the canonical source — make the schema much tighter.** Markdown
   stays the source of truth (GH renders text, tables, mermaid, workflows). The fix for
   "specs read like prose" is **not** to switch to YAML-blocks-as-source — it's to constrain the
   markdown hard: canonical headings only, **no prose outside sections**, no path-derived metadata
   in the body, treat the document as a **typed AST**. See §8.
4. **Folder hierarchy carries structure.** `spec/domains/<domain>/components/<component>/…` — don't
   repeat domain/component names inside the files.
5. **Spec = source of truth; code = evidence.** **Attach spec → code** (the spec names its
   implementation paths), *not* code → spec — because implementation moves, the spec is stable.
6. **Diagrams are derived, disposable, cached.** Mermaid (GH-native; preferred) or D2 — generated
   from the spec, regenerated anytime, never the source of truth. Review happens on these derived
   views, not the raw spec text.
7. **AI-maintained, human-reviewed — never hand-edited.** Exactly like agent memory: the human
   reviews and requests fixes; the human does not edit spec files directly. This is what keeps the
   format consistent without a strict schema.
8. **Separate normative spec from analysis.** The spec body is the source of truth; gaps / TODOs /
   limitations / findings are non-normative annotations kept apart from it.

## 3. Frameworks considered

| Area | Option | Verdict |
|---|---|---|
| Modeling | UML / MDA / codegen | **Rejected** — dual-maintenance pain, rigid generated code, inevitable drift |
| Structure | C4 model | Liked — component level is the sweet spot; AI-friendly |
| Structure | Structurizr / LikeC4 | Architecture-as-code; structural only (weak on behavior/failure/impl) |
| Contracts | OpenAPI / AsyncAPI | Successful "spec as code"; reuse for interface/event contracts |
| Diagrams | **Mermaid** | **Chosen render layer** — GH renders natively, AI generates easily |
| Diagrams | D2 | Cleaner than PlantUML; viable alternative to mermaid |
| Diagrams | PlantUML | Older; fine for sequence diagrams |
| Catalog | Backstage | Rejected — needs its own portal; must stay in GH with the project |
| Reverse-eng | Tree-sitter / Sourcegraph / Semgrep / CodeQL | Optional AST/dep-graph aids; AI does the semantic extraction |

Conclusion: **no single tool fits**; don't adopt one wholesale and don't build a new one — compose
a markdown-based workflow, mermaid for views.

## 4. Spec model

- **Source of truth = structured markdown; everything else is a derived view** (diagrams, tickets,
  architecture docs, AI context, implementation tasks).
- **Two hierarchies**, both useful — `code → component → subsystem → system`, and (more valuable
  for AI) `system → use-case → flow → component → code`.
- **Layered content** (the "logical code"): architecture (components + dependencies) / data-flow /
  state-machines / contracts (interfaces) / behavioral-rules.
- **Repository shape** (as in the kit): `spec/{index.md,status.md}`,
  `spec/domains/<domain>/{components,workflows,contracts}/…`, `spec/generated/` (derived diagrams).
- **Artifact types:** `component`, `workflow`, `contract` (+ future `consistency-checker`,
  `diagram-generator`).
- **GitHub fit:** the spec is the thing under review in a PR; affected spec nodes → generated
  diagrams + impact report + test suggestions; code is the evidence it was implemented.

## 5. Reverse-coding pipeline (implemented in the `spec-poc` kit)

Orchestrator (interactive) owns discovery → task generation → spawning workers → review; confined
workers each own exactly one target spec file (create-only; `LOCK`/`STATUS`/`DONE`); task lifecycle
`todo → running → review → done`; code-only extraction; reconciliation against existing docs is a
separate later phase. Full detail in the kit's `REV-SPEC.md` and `docs/agents/*`. The pipeline is
proven (pilot ran, findings verified); only the **output format** is unsettled.

## 6. Open items — to finalize in the format brainstorming thread

1. **The constrained-markdown section schema per artifact type** (component / workflow / contract):
   strict enough for lossless round-trip and AI evaluation, still GH-readable. **This is the
   blocker** for the bulk extraction run.
2. **Behavioral-layer depth** — workflows as step-lists vs state-machines; whether to carry
   pre/post-conditions and invariants, and how.
3. **Normative ↔ findings separation mechanism** — delimited sections in one file vs sibling files.
4. **"Evaluation" check set** — what an AI pass verifies (dangling refs, unimplemented interfaces,
   orphan specs, workflow↔component consistency). Overlaps the deferred Consistency Agent.
5. **YAML↔MD convertibility convention** — the rule that keeps "YAML disguised as Markdown" honest.

## 7. POC status (2026-06-19)

Discovery complete (4 domains, 19 components, 9 workflows, 12 contracts); a 3-task pilot
(contract + component + workflow) ran via confined sonnet sub-agents and its findings were verified
accurate against code. **Bulk run is PAUSED** pending the format decision; the 3 pilot specs (in the
current prose template) are **provisional** and will be re-cast once the format above is settled.

## 8. Schema-tightening round (2026-06-19)

> **Brainstorm ongoing — no final conclusion yet.** The points below are diagnosis + working
> positions to resume from, not settled decisions.

Reviewing the pilot specs surfaced *why* they read like design docs. Diagnosis and working
positions (full exchange in [`scratch/spec-as-code-brainstorm-raw.md`](../scratch/spec-as-code-brainstorm-raw.md),
"ROUND 2"):

**Observed failure modes** (current extractor templates produce these):
1. **Prose, not structure** — agents drift to narrative ("The autoscaler receives queue
   depth metrics…") instead of typed lists (`## Inputs` → `- Name: / Type: / Source:`). Most common LLM failure.
2. **Repeated hierarchy** — body restates path-derived metadata (`Domain:`, `Component:`)
   already implied by `spec/domains/<d>/components/<c>/component.md`.
3. **Invented schema variants** — "Failure Modes" vs "Failures" vs "Error Handling" across
   workers; breaks automation.
4. **Markdown too free-form** — sections under-specified, so quality varies per worker.

**Working position (Dean) — markdown stays; the schema gets much tighter (to revisit):**
- **Keep markdown.** It is the right format *because* GitHub renders it (text, tables, mermaid,
  workflows). Reject ChatGPT's "pure Markdown is too weak → make YAML-blocks-in-MD the canonical
  source" conclusion. The problem is loose schema, not the medium.
- **Treat the spec as a typed AST.** Agent instruction shifts from "Required sections" to
  *"Output must conform exactly to this schema. No additional headings. No prose outside sections."*
  Canonical headings, fixed field shapes (`Name:/Type:/Source:`), one canonical name per concept.
- **Forbid path-derived metadata** in the body (the folder path already carries it).
- **Contracts/APIs model on Swagger/OpenAPI shape** — structured endpoint/field definitions —
  **plus** explicit *semantic reasoning* and *responsibilities* (the "why"/guarantees that
  OpenAPI alone doesn't carry). This is the concrete target for the strict contract schema.
- **Add a schema-validation step** before review: `revcoder → schema validator → review`. The
  validator checks headings/fields exactly (compatible with the md-first, AI-authored model —
  it's enforcement, not a new language). Overlaps the deferred Consistency Agent.

**Net (working):** §6 item 1 (the per-artifact section schema) is the blocker, and the *emerging*
bar to refine next session is: *strict, typed-AST-like markdown; Swagger-style contracts + semantics
+ responsibilities; no prose outside sections; validated.* Not finalized.
