# AGENTS.md: braintoss-monitor

- **Public repo.** Never commit secrets, tokens, the ntfy topic or private data. Only public URLs.
- **Scope:** uptime and TLS expiry of public Braintoss URLs only. No cloud login, no cost or billing checks: cloud spend (GCP, AWS, Anthropic) is monitored by `rikwolfe/ops-monitor`.
- **What goes live on merge:** the workflows on `main` run on their schedules right away. No deploy step.
- **Merge gate:** small changes may go to `main` directly; run `python3 monitor.py uptime` locally first (needs `pyyaml`; without `NTFY_TOPIC` it only prints).
- **State:** `state/status.json` is written by the uptime workflow; don't hand-edit unless resetting.
- **Secret:** `NTFY_TOPIC` (GitHub Actions secret). Never print it; pipe it between stores. Ask Richard before deleting anything.
