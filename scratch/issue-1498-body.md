The operator-facing WVA guides and values in the **llm-d/llm-d** repo do not document three behaviors an operator needs for the ThroughputAnalyzer in 0.9:

1. The ThroughputAnalyzer is **opt-in** — disabled by default; it must be explicitly enabled in the saturation ConfigMap.
2. Enabling it at runtime **requires a controller restart** — analyzer registration is read once at startup, so a live ConfigMap edit is not picked up until the controller restarts.
3. The ThroughputAnalyzer **must not be enabled without EPP arrival metrics present**. Its decode demand is driven entirely by the model-level request arrival rate (sourced from EPP); if that metric is absent, a busy model reads as idle (zero demand) and can be scaled down. Enabling TA without EPP arrival metrics available will push spurious scale-downs. (Raised in the PR #1480 review.)

Update the guides/values docs to state all three. Tracked in the WVA repo; the doc changes themselves land as PRs against llm-d/llm-d.
