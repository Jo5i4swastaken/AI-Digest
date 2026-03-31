# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An OmniAgents-based AI digest system with two agents and a Next.js dashboard. The primary agent (`ai_digest_agent/`) collects AI news 3x/day (AM, PM, Evening), writes JSON digests, and optionally emails them. The root-level agent is a starter-kit demo.

## Commands

### Python / Agent

```bash
# Install dependencies (uses private Gemfury registry)
pip install -r requirements.txt

# Run the basic starter agent (root)
omniagents run -c agent.yml              # Web UI
omniagents run -c agent.yml --mode ink   # Terminal UI

# Run the digest agent interactively
cd ai_digest_agent && omniagents run -c agent.yml

# Run a single digest slot (non-interactive, cron-friendly)
python ai_digest_agent/scripts/run_scheduled.py --slot AM --mode brief --email
python ai_digest_agent/scripts/run_scheduled.py --slot PM --mode brief --email
python ai_digest_agent/scripts/run_scheduled.py --slot Evening --mode brief --email

# Run the cron-style "if due" check (used by GitHub Actions)
python ai_digest_agent/scripts/run_if_due.py --timezone America/Chicago --mode brief --email
```

### Dashboard (Next.js)

```bash
cd dashboard
npm install
npm run dev     # Starts on port 3000, opens browser
npm run build   # Production build
npm run lint    # ESLint
```

## Architecture

### Two OmniAgents agents

- **Root agent** (`agent.yml`, `tools/utils.py`): Starter-kit demo with `get_current_time`, `calculate`, `flip_coin`, `roll_dice`.
- **Digest agent** (`ai_digest_agent/agent.yml`, `ai_digest_agent/tools/digest_tools.py`): Searches web/YouTube for AI news via SerpAPI, deduplicates against `ai_digest_agent/data/state.json`, writes JSON digests, renders HTML emails, and sends via Gmail SMTP.

Custom tools use `@function_tool` from `omniagents` (not from `agents`). Tools are auto-discovered from `tools/` directories.

### Digest pipeline

`run_if_due.py` (called hourly by GitHub Actions) checks the schedule (8h=AM, 14h=PM, 20h=Evening) against the configured timezone, skips if `digests/archive/YYYY-MM-DD/<slot>.json` already exists, then delegates to `run_scheduled.py`.

`run_scheduled.py` starts the agent in server mode on a random port, connects via WebSocket (JSON-RPC 2.0), sends a prompt, auto-approves tool calls, and waits for `run_end`. The agent writes:
- `ai_digest_agent/output/latest.json` + `latest.html` (local)
- `ai_digest_agent/output/archive/YYYY-MM-DD/<slot>.json` (local archive)
- `digests/archive/YYYY-MM-DD/<slot>.json` + `digests/archive/index.json` (repo, committed by CI)

### Dashboard

Next.js 15 + React 19 + Tailwind CSS 4 app in `dashboard/`. Reads digest JSON from `../digests/archive/` at build/request time. API routes at `/api/digests` and `/api/digests/[date]/[slot]`. Types defined in `dashboard/app/_components/types.ts`.

### GitHub Actions

`.github/workflows/ai-digest.yml` runs on cron (`1 * * * *` — first minute of each hour) and supports manual dispatch with slot/email inputs. Commits digest JSON files to `main` via `github-actions[bot]`. Required secrets: `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `SERPAPI_API_KEY`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `EMAIL_TO`, `TIMEZONE`.

### OmniAgents framework

Installed from private registry `https://pypi.fury.io/ericmichael/`. Key concepts documented in `.omni_code/skills/omniagents-basic/SKILL.md`: YAML agent config, `@function_tool` decorator, `@context_factory` for dynamic instructions, safe agent options, handoffs, MCP servers, skills system, and voice mode. The API endpoint uses `OPENAI_BASE_URL` (currently pointed at `rgvaiclass.com/v1`).

## Digest JSON schema

Each digest follows this structure (see `ai_digest_agent/instructions.md` for the full spec):
```
{generated_at, slot, timezone, items: [{category, title, url, source, published_at, why_it_matters, brief, details, is_update}]}
```
Categories: `product`, `open_source`, `agent_tooling`, `hardware`, `funding`, `ways_to_use`.