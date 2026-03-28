# AI Digest Dashboard (Next.js + Tailwind)

Reads digest JSON committed to `digests/archive/` and renders a light-mode dashboard + an editorial detail view.

## Local dev

```bash
cd dashboard
npm install
npm run dev
```

Then open:
- http://localhost:3000

## Manual test runs (pre-production)

The dashboard can trigger a GitHub Actions run (AM/PM/Evening) via a server-side API route.

Set these env vars in Vercel (or a local `.env.local` inside `dashboard/`):

- `GITHUB_OWNER`
- `GITHUB_REPO`
- `GITHUB_WORKFLOW_ID` (workflow file name like `ai-digest.yml` or numeric workflow id)
- `GITHUB_DISPATCH_TOKEN` (GitHub PAT with Actions:write + Contents:read)
- `RUN_DIGEST_KEY` (optional; if set, the UI prompts for it and sends it as `x-run-key`)

## Deploy (Vercel)

- Import this repo into Vercel
- Set **Root Directory** to `dashboard/`
- Build command: `npm run build`
- Output: Next.js

The dashboard reads digest JSON from the repo at `digests/archive/`.

## Data contract
- `digests/archive/index.json`
- `digests/archive/YYYY-MM-DD/<slot>.json`

Slots: `AM`, `PM`, `Evening`
