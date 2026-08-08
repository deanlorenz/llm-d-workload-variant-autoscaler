from: review
to: planner
session: dataflow-map PR-1 delta + §1 cleanup notes (durable capture before session reset)

**Why this handoff exists.** During the anchor-refactor review I did a §0–§7 reverse-read walkthrough
of `planning/multi-analyzer-dataflow-map.md` (your doc) and derived "what PR-1 changes in the map."
That analysis is currently **transcript-only**. Dean is about to clear this session; this handoff
preserves the durable residue so nothing is lost. The map is your doc — this is input for a possible
**§9 "What PR-1 (ta-anchor-refactor-v2) changes in this map"** section; I make no edits to it.

No action is *required* — treat as reference. The full line-by-line §4.x/§3.x walkthrough remains
**deferred** (Dean: "resume on go back to 3"); it is recoverable from this session's transcript. What
follows is the crisp conclusion set.

---

## PR-1 map delta (conclusions)

- **§4.2 "Binding-entry resolution (`saturationEntry`)" is the ONE section PR-1 rewrites.**
  `saturationEntry` (index-0 scan returning the *stored* sat `AnalyzerResult`) → **`bindingAnchor`**
  (per-variant merge builder, keyed by `VariantName`, deriving a **fresh** `*domain.AnalyzerResult` on
  demand; returns **nil → hold** when nothing binds). Same signature, same call-site. The (a)/(b) field
  split lives here: (a) identity `AcceleratorName/Cost/Role/ReplicaCount/PendingReplicas` from sat;
  (b) sizing `PerReplicaCapacity/Reason/TotalDemand/Utilization` from the binding analyzer;
  `TotalCapacity` recomputed.

- **§5 "where does multi-analyzer combine actually happen" — headline UNCHANGED by PR-1.** Combine math
  is untouched; only the **identity source** moves (from "the sat entry" to "the merged anchor"). The
  `saturationEntry` loose-end §5 flags (the hardcoded special role) is **not dissolved** by PR-1 — PR-1
  *relocates* the special role into `bindingAnchor` rather than removing it. Full dissolution is **PR-2
  territory** (multi-vote combine + anchor deletion).

- **§4.7 "Final `VariantDecision` assembly" — same data, new provenance.** What the map calls "the
  binding entry" is now the merged anchor, not the raw stored sat result. No structural change to
  assembly.

- **§2 dispatch / §3.3 QM / §6 "QM in one paragraph" — QM becomes an explicit ERROR path.** PR-1 makes
  V2-dispatch of a present QM ConfigMap **refuse with an error** — no silent sat-v2 fallback. Map §2/§6
  should note "V2 + QM → refuse-with-error (DEFERRED, §12 of the plan)."

- **§8 Dean's review annotations — PR-1 flips:** RESOLVED by PR-1 = **E1, E4, E5 (refined), A1, G1**;
  still-deferred = **B2, B3, B4, C4, A3, A4, C5, D1, §2.4**. (Cross-check against the current §8 text
  before folding — annotation IDs may have shifted since the walkthrough.)

- **Net conceptual shift:** the pipeline **spine survives**; only the identity source moves. Review-doc
  Part 3 findings **V6/V7** (copy-vs-contract, list-completeness) are the anchor-**deletion** roadmap
  (PR-2), not PR-1.

---

## §1 cleanup notes (discussion record — Dean: do NOT fold into plan or review)

Dean's call on these three (2026-08-05): "don't think they require plan changes at this point." Kept
here only so they survive the session reset — clean-code observations from the §1 walkthrough, not
verified against current line refs, not scoped to any PR:

1. **Uniform per-analyzer loop.** Phase-1 could iterate analyzers uniformly instead of special-casing
   sat at index 0. Relates to design F1 "pre-analysis extraction". PR-1 does not do this — the anchor
   mechanism is a step toward it but keeps index-0 sat as the (a)-identity carrier.
2. **Collapse `applyUniversalThreshold`.** Candidate simplification noted during the walkthrough;
   discussion-level only.
3. **Single liveness-step owner.** Liveness is set in one place and read in another; a single owner for
   the liveness step was flagged as a clean-up. PR-1 keeps `updateLivenessAndSetLive` setting `.Live`
   on every entry incl. sat, with the binding rule reading `satNR.Live` — sufficient for PR-1, but the
   clean-up remains open.

If you fold any of these anywhere, they belong in the map (§7 "loose ends") or a forward-plan item —
**not** in `ta-anchor-refactor-v2-plan.md` or the review doc, per Dean.
