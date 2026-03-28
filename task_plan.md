# Task Plan: GitHub Actions (Option C) + GitHub-backed Digest Storage

## Goal
Move digest generation + email sending to GitHub Actions on a schedule, and publish digest JSON artifacts into a GitHub repo folder that the Vercel dashboard will read.

## Current Phase
Phase 1

## Phases

### Phase 1: Requirements & Discovery
- [x] Confirm user intent (Option C, Vercel, GitHub folder)
- [x] Identify constraints (secrets, schedules in UTC, no local cron)
- [ ] Document findings in findings.md
- **Status:** in_progress

### Phase 2: Planning & Structure
- [ ] Define repo folder contract for digests
- [ ] Define workflow schedules and slot mapping
- [ ] Decide on secret names and required env vars
- **Status:** pending

### Phase 3: Implementation
- [ ] Update digest writer to publish to `digests/archive/...` + `digests/archive/index.json`
- [ ] Add GitHub Actions workflow(s) for AM/PM/Evening
- [ ] Add helper script(s) for commit/push from Actions
- **Status:** pending

### Phase 4: Testing & Verification
- [ ] Validate workflow YAML
- [ ] Run one manual workflow_dispatch
- [ ] Confirm commit lands in `main` and Vercel can read files
- [ ] Confirm email delivery from Actions
- **Status:** pending

### Phase 5: Delivery
- [ ] Summarize setup steps (GitHub secrets, Vercel connect)
- **Status:** pending

## Key Questions
1. Should digests and dashboard live in one repo or split (code vs data)?
2. What GitHub Actions secrets are required for OpenAI endpoint, SerpAPI, Gmail?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Use GitHub Actions cron in UTC | GitHub schedules are UTC; avoids relying on laptop uptime |
| Store digests under `digests/archive/YYYY-MM-DD/<slot>.json` | Simple, static, Vercel-friendly file layout |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
|       | 1       |            |

## Notes
- Target timezone: `America/Chicago` (McAllen, TX)
- Times: 08:00, 14:00, 20:00 local; map to UTC in workflow schedules
