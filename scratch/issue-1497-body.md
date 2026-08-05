Part of #1492 (Epic A — Multi-analyzer pipeline & analyzer lifecycle).

Enabling an analyzer by editing the saturation ConfigMap at runtime is silently ignored until the controller restarts. Emit a warning (log + Kubernetes Event) so the operator knows a restart is required to pick up the change.

Fixed by #1502 (merged, 1d5553ee).
