# Findings & Decisions

## Requirements
- Move scheduling from local cron to GitHub Actions (Option C)
- Vercel deployment for React/Tailwind dashboard reads digests from a GitHub repo folder on `main`
- Send emails 3x/day (Morning/Afternoon/Evening)
- Timezone: America/Chicago (CDT)

## Research Findings
- GitHub Actions `schedule` triggers are specified in UTC.
- Existing agent runner supports `--slot AM|PM|Evening` and uses Gmail SMTP.
- Prior local issues found: parent `.env` overriding keys; tool approval in server mode required auto-approve; strict tool schema required JSON-string tool args.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Use GitHub Actions secrets for all keys | Avoid unattended local credentials; centralized access control |
| Commit digest JSON output into repo under `digests/archive/` | Vercel can read static JSON from the repo at build/runtime |
| Use schedule mapping to slots | Different UTC times for AM/PM/Evening |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| `.env` precedence caused wrong `OPENAI_BASE_URL`/`SERPAPI_API_KEY` | In local runner, forced `override=True` and passed env to subprocess |
| Custom tools failed strict schema | Changed tool signatures to accept/return JSON strings |
| Email tool approval caused hang in server mode | Scheduler auto-approved `ui.request_tool_approval` |
| `send_digest_email` crashed with `'FunctionTool' object is not callable` | `send_gmail_email` was decorated with `@function_tool`, making it a FunctionTool object instead of a callable. Removed decorator and renamed to `_send_gmail_email` as a plain helper |
| Emails sent as plain unstyled HTML | Agent was composing its own HTML body. Changed `send_digest_email` to accept `digest_json` and render styled HTML internally via `_render_email_html` |
| Evening digest filed under wrong date (March 31 instead of March 30) | Agent rounded `generated_at` to midnight, pushing it to the next day. Fixed `_date_key` to use `datetime.now()` in local timezone instead of agent's `generated_at` |
| `TIMEZONE` env var empty string bypassed default | `os.getenv("TIMEZONE", "America/Chicago")` returns `""` when secret is missing (not the default). Fixed with `os.getenv("TIMEZONE") or "America/Chicago"` |
| `run_if_due.py` old version required exact hour match | Old script used `slot_map.get(now.hour)` which only matched hours 8, 14, 20 exactly. Combined with GitHub Actions cron delays, the window was nearly impossible to hit. Fixed to iterate slots and check `now >= due` |

## Technical Decisions (continued)
| Decision | Rationale |
|----------|-----------|
| Slot-based email color themes (AM=amber, PM=blue, Evening=indigo) | Visual alignment with time-of-day; matches dashboard dark aesthetic |
| `_render_email_html` uses table-based layout | Email client compatibility (Gmail, Outlook, Apple Mail) |
| Date format "Month Day, Year" in emails | Human-readable over ISO format |
| Category color-coded badges in emails | Quick visual scanning of digest item types |

## Resources
- Reference article layout to match for detail pages: https://www.aiunderstanding.org/news/disney-openai

## Visual/Browser Findings
- AIUnderstanding article page: clean editorial layout with strong typography, clear hierarchy, and link-forward sourcing.
