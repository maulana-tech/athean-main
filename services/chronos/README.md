# Chronos — Scheduler

Thin APScheduler-backed cron service that fires deterministic jobs on
the rest of the Athean stack. Chronos itself does no heavy lifting —
every job pushes a trigger message onto Redis (or fires an HTTP call)
so the consumer service stays independently deployable.

## What It Schedules

| Cron env var | Default | Trigger |
|---|---|---|
| `CHRONOS_APOLLO_CRON` | `*/5 * * * *` | Apollo prefilter sweep of the Polymarket CLOB |
| `CHRONOS_BOULE_SWEEP_CRON` | `*/15 * * * *` | Boule deliberation backlog flush |
| `CHRONOS_ANCHOR_RETRY_CRON` | `*/30 * * * *` | Areopagus PoR anchor-retry sweep |

All three accept any 5-field cron expression. Disable a job by setting
its env var to an empty string.

## Setup

```bash
cd services/chronos
cp .env.example .env  # if added; otherwise inherit root .env
uv run python -m chronos.cli
```

Required env:
- `REDIS_URL` — same Redis instance the rest of the stack uses

Optional env:
- `POLYMARKET_CLOB_URL` — override the upstream URL (defaults to
  `https://clob.polymarket.com/markets`). Useful behind the Vercel
  geo-proxy.

## Structure

```
src/chronos/
  cli.py          Entry point — wires the schedule from env
  scheduler.py    APScheduler wrapper (timezone, missed-job policy)
  jobs.py         The three jobs above
```

## Tests

```bash
uv run pytest tests/ -q
```

## Why a separate service

Cron logic is the easiest thing in a system to make a runtime
dependency by accident. Keeping Chronos isolated means:
- Apollo + Boule + Areopagus never import scheduling libraries
- A scheduler outage cannot take down the trading pipeline — it just
  pauses the periodic sweeps
- The cron schedule is reconfigurable per environment without
  redeploying any consumer service
