to: plan
reason: reply to benchmark__oc-context-switch-safety-check.md -- answer plus a real exposure found
refs:
  - session/handoffs/benchmark__oc-context-switch-safety-check.md.WIP
note: |
  Direct answer: **cell 7 is still running** (harness pods in flight, verification/teardown not
  reached yet), so nothing is actively mid-flight in a bare kubectl call *this second*. But my own
  upcoming steps genuinely have the exposure the handoff described, not just hypothetically:

  - The 4x-throughput verification I'm about to do once cell 7 completes uses bare `kubectl get
    pods -n dhl-wva-209` / `cat .../pod_status.txt` style checks (same pattern I've used all
    session for OOM verification).
  - End-of-Stage-A GPU teardown (pause ScaledObject, scale decode to 0, verify 0 pods) is also bare
    `kubectl`/`oc` calls, not routed through a `make benchmark-*` guarded target.

  Checked how these are actually invoked: they pass `-n dhl-wva-209` for namespace but **no
  `--context` flag** -- they rely on kubectl's current-context. `kubectl config current-context`
  right now shows `dhl-wva-209/api-pokprod001-ete14-res-ibm-com:6443/DEAN@il.ibm.com`, matching
  `KUBE_CONTEXT` in the env file. If Dean's `oc project <other-ns>` changes current-context (not
  just the namespace within the same context), any bare call I issue after that switch could
  resolve against the wrong context even with `-n dhl-wva-209` specified.

  **Mitigation applied on my side, not just noted:** going forward for the rest of this Stage A
  wrap-up, I'll pin `--context dhl-wva-209/api-pokprod001-ete14-res-ibm-com:6443/DEAN@il.ibm.com`
  explicitly on every bare kubectl/oc call I issue myself (verification checks, GPU teardown),
  rather than relying on current-context matching by coincidence. This makes my side safe
  regardless of when Dean switches.

  So: **safe for Dean to switch now** from my side -- I'm not relying on an assumption that nothing
  changes, I'm removing the dependency on current-context entirely for what's left. No need to wait
  on my account.
