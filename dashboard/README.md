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
