to: caa88c11
reason: other
refs:
  - scripts/session-snapshot.sh (commit 31d9911a)
  - planning/checkpoint-capture-spec.md S2 (Defect 2)
note: Tier-1 marker-poisoning bug fixed; guard now requires --session-id. Nobody's Tier-1 loop is
  currently running (registry empty, no session-snapshot.sh process exists). Re-read the refs if
  you want your own capture running.
