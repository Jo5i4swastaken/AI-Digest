import { NextResponse } from "next/server";

export const runtime = "nodejs";

type Slot = "AM" | "PM" | "Evening";

export async function POST(req: Request) {
  const runKey = process.env.RUN_DIGEST_KEY;
  if (runKey) {
    const provided = req.headers.get("x-run-key") ?? "";
    if (provided !== runKey) {
      return NextResponse.json({ error: "unauthorized" }, { status: 401 });
    }
  }

  const owner = process.env.GITHUB_OWNER;
  const repo = process.env.GITHUB_REPO;
  const workflowId = process.env.GITHUB_WORKFLOW_ID;
  const token = process.env.GITHUB_DISPATCH_TOKEN;

  if (!owner || !repo || !workflowId || !token) {
    return NextResponse.json({ error: "missing_env" }, { status: 500 });
  }

  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "bad_json" }, { status: 400 });
  }

  const slot = (body as { slot?: string }).slot;
  const email = Boolean((body as { email?: unknown }).email);

  const allowed: Slot[] = ["AM", "PM", "Evening"];
  if (!slot || !allowed.includes(slot as Slot)) {
    return NextResponse.json({ error: "bad_slot" }, { status: 400 });
  }

  const ghRes = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflowId}/dispatches`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
      },
      body: JSON.stringify({
        ref: "main",
        inputs: {
          slot,
          email: email ? "true" : "false",
        },
      }),
    },
  );

  if (!ghRes.ok) {
    const text = await ghRes.text();
    return NextResponse.json(
      { error: "github_error", status: ghRes.status, details: text.slice(0, 2000) },
      { status: 502 },
    );
  }

  return NextResponse.json({ ok: true });
}
