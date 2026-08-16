to: benchmark
reason: re-read plan
refs:
  - planning/ta-pokprod-testing-plan.md §7.6.1 T9 bullet (corrected 2026-08-12) — log-follower apply is not a Dean step, needs wiring into the run playbook
  - planning/ta-pokprod-testing-plan.md §9.1 T9 row — corrected owner, same content
note: Verified this session -- gateway-log-follower.yaml's resources are all namespace-scoped (Role/RoleBinding/ServiceAccount/Deployment, dhl-wva-209), and the Makefile has no reference to gateway-log-follower today. Dean's framing (2026-08-12): "log watching should be part of running a benchmark, invoked only when a benchmark actually runs" -- no permission beyond what a benchmark run already needs.
