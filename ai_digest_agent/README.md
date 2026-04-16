# AI Digest Agent

Runs an OmniAgents agent that collects AI news (Google + YouTube + X via Google), writes a simple dashboard, and can send emails via Gmail.

## Setup

1) Install deps:

```bash
pip install -r ../requirements.txt
pip install websockets
```

2) Create `.env`:

```bash
cp .env.example .env
```

Fill in:
- `OPENAI_BASE_URL`, `OPENAI_API_KEY`
- `SERPAPI_API_KEY`
- `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`
- `EMAIL_TO`
 - `TIMEZONE` (set to `America/Chicago` for McAllen, TX)

## Run manually (interactive)

```bash
omniagents run -c agent.yml
```

## Run once (non-interactive, cron-friendly)

```bash
python scripts/run_scheduled.py --slot AM --mode brief --email
python scripts/run_scheduled.py --slot PM --mode brief --email
python scripts/run_scheduled.py --slot Evening --mode brief --email
```

This also writes:
- `output/latest.json`
- `output/latest.html`
- `output/index.html` (dashboard)
- `output/archive/YYYY-MM-DD/<slot>.html` (history)

## Cron examples

Edit your crontab with `crontab -e`:

```cron
0 8 * * *  cd /absolute/path/to/ai_digest_agent && /usr/bin/env python scripts/run_scheduled.py --slot AM --mode brief --email
0 14 * * * cd /absolute/path/to/ai_digest_agent && /usr/bin/env python scripts/run_scheduled.py --slot PM --mode brief --email
0 20 * * * cd /absolute/path/to/ai_digest_agent && /usr/bin/env python scripts/run_scheduled.py --slot Evening --mode brief --email
```

Note: cron uses your machine's timezone. For McAllen, TX use `America/Chicago`.

## GitHub Actions (Option C)

This repo includes `.github/workflows/ai-digest.yml` to run the digest on a schedule and commit JSON outputs into `digests/archive/`.

The workflow runs every 10 minutes and will:
- Generate any missing due digest for the current or previous day (backfill window)
- Emit `ai_digest_agent/output/monitor.json` and open a GitHub issue if a slot is late or missed

Delivery guardrails:
- Evening digest is not generated if it would arrive after 9pm local time (60 minutes after the 8pm slot); it is alerted instead.

Required GitHub Secrets:
- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`
- `SERPAPI_API_KEY`
- `GMAIL_ADDRESS`
- `GMAIL_APP_PASSWORD`
- `EMAIL_TO`

Outputs committed to `main`:
- `digests/archive/YYYY-MM-DD/<slot>.json`
- `digests/archive/index.json`
