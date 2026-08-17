# role: coder

token:  <branch>
owns:   code, reference, status file and step ledger
reads:  its code spec only

## What

Executes one code spec inside its assigned worktree. Narrowest read-scope of all 11 roles — reads its
own code spec only. Never presumes, never guesses, never makes a judgment call outside the spec's own
scope; a halt routes to the spec owner, never resolved in the coder's own chat (Dean does not watch a
coder work).

## Richest existing coverage of any role

Real, harvestable kernel content already exists: `CODER-CONVENTIONS.md` §7 ("things you may do
without asking") and §8 ("things you may NOT do without asking") are the coder's absolute, always-true
permission boundary — already classified `role:coder` in `harvest-classification.md` (CC6, CC15,
CC17, CC18, CC19). `s-coder` is the fullest-coverage skill of all ten. Harvesting this role is mostly
transcription (Step 2), not authoring.

## One exception, not yet decided

The benchmark tester/coder runs external commands (cluster operations, load generation) that a normal
coder's worktree confinement forbids — Dean, 2026-08-17 (Addendum 14): "not really a coder and should
maybe have its own role." Not resolved here — tracked as an open question, not given its own role file
yet, since inventing one without Dean's decision would be exactly the "define everything upfront"
Dean explicitly said not to do.

## Open, unresolved (carried from Addendum 4/13, not re-litigated here)

Whether "never push to upstream" (C44 in `harvest-classification.md`) is a standing kernel line or a
per-step reaffirmed convention is still the open "posture vs. checklist" question. Kernel content
below should not be treated as fully closed until that resolves.

origin: doc-and-session-model.md § Roles; harvest-classification.md CC6/CC15/CC17/CC18/CC19, C44
