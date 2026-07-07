# Deployment

Production splits by latency requirement:

- **Equinix NY4 colo** — the execution hot path (algo engine, smart order
  router, FIX gateway, feed handlers) runs on bare metal with kernel-bypass
  networking and direct venue cross-connects.
- **AWS us-east-1** — middle- and back-office workloads (OMS services,
  risk, databases) run on EKS and managed data stores, linked to the colo
  by Direct Connect.

See the *Production – Full Estate* deployment view for the complete map.
