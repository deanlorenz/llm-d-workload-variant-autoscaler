to: benchmark
reason: quick safety check before Dean switches oc context in another shell
refs:
  - planning/ta-pokprod-architecture-design.md
note: Dean wants to run `oc project <different-namespace>` in a separate shell -- this rewrites
  ~/.kube/config's current-context globally (confirmed: single shared kubeconfig,
  KUBECONFIG defaults to $(HOME)/.kube/config). Every Makefile-target benchmark action is
  namespace-flagged + guard-checked (env_guard.py refuses on a context/.env mismatch), so already-
  scheduled cluster workloads and in-flight guarded commands are safe either way. The one residual
  risk: a NEW direct kubectl/oc call issued outside a Makefile target (not going through
  benchmark-guard) right after the switch could silently resolve against the new namespace instead
  of the benchmark one. Quick check before Dean switches: is anything from this session
  (cell 7 verification, GPU teardown, etc.) about to issue a bare kubectl/oc call not wrapped in a
  `make benchmark-*` target in the next few minutes? If genuinely nothing pending, Dean's switch is
  safe to do now; if something is, worth a short wait. Not blocking -- just confirming the window
  before Dean acts.
