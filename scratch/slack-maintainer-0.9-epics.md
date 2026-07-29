# Slack note — 0.9 epics (DRAFT, send by hand)

*Slack mrkdwn; `<url|text>` renders as an inline link. Replace `@maintainer`.*

---

Hi @maintainer — small bit of 0.9 project cleanup on the WVA autoscaler. I organized the analyzer / optimizer / observability work (0.9 plus the 0.8 groundwork it builds on) into four epics so the release tracks cleanly:

• *Multi-analyzer pipeline & analyzer lifecycle* (new) — <https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1492|#1492>
• *ThroughputAnalyzer* — reusing the existing epic <https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1005|#1005>, adding 0.9 children
• *P/D-aware optimizer: role capacity & paired allocation* (new) — <https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1493|#1493>
• *Observability: scaling-decision visibility* (new; successor to the closed <https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/911|#911>) — <https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1494|#1494>

I filed the three new epics plus short trackers for my own untracked 0.9 items — opt-in analyzer participation (<https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1495|#1495>), scale-down veto liveness gate (<https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1496|#1496>), and a planned warning when a runtime ConfigMap analyzer-enable needs a controller restart (<https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1497|#1497>). All are labeled `triage/accepted` + `release/v0.9`; shipped-0.8 work is captured as checklists in the epic bodies rather than as retro issues.

A couple of notes:
• Existing issues are linked, not duplicated.
• I did *not* create trackers for other contributors' PRs — I'll reach out to those authors directly. Their work is still credited in the 0.9 release notes.
• Observability epic is intentionally left unassigned for now.

Flag anything you'd like assigned, relabeled, or milestoned differently. Thanks!
