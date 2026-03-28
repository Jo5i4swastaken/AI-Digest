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

## Resources
- Reference article layout to match for detail pages: https://www.aiunderstanding.org/news/disney-openai

## Visual/Browser Findings
- AIUnderstanding article page: clean editorial layout with strong typography, clear hierarchy, and link-forward sourcing.
