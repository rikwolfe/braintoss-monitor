# braintoss-monitor

Small GitHub Actions monitor for the public Braintoss URLs. Alerts go to the ntfy app on Braintoss's own topic.

**This repo is public on purpose** (scheduled Actions on a private Free repo would use more than the 2,000 free minutes). It contains **no secrets**: only public URLs. It needs no cloud login. Cloud-spend monitoring is not here: it lives in [ops-monitor](https://github.com/rikwolfe/ops-monitor).

## What is checked

Every URL in `sites.yml`: braintoss.app, www.braintoss.app, braintoss.com, www.braintoss.com and the email backend's `send.braintoss.app/health`.

| Workflow | When | What |
|---|---|---|
| `uptime.yml` | every 15 min | HTTP check of every URL in `sites.yml` (2xx/3xx, follows redirects, 2 retries) and TLS expiry (< 14 days). Alerts **only when the state flips** (down: high priority, recovered: default). State lives in `state/status.json`. |
| `weekly.yml` | Monday 06:30 Amsterdam (winter) | "braintoss-monitor alive" summary. **If this stops arriving, the monitor is broken.** |
| `heartbeat.yml` | 1st of the month | Small commit so GitHub doesn't disable the schedules after 60 days without activity. |
| `test.yml` | by hand | Sends "braintoss-monitor test" to ntfy. |

## Secrets (names only)

- `NTFY_TOPIC`: the ntfy.sh topic. **It is a secret**: anyone who knows it can read and send the alerts. It is only in GitHub Actions secrets and in Richard's local `_security` folder, never in this repo.

## Changing the URL list

Edit `sites.yml`. A removed URL drops out of the state on the next run.
