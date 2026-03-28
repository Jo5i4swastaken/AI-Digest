import { NextResponse } from "next/server";
import { readFile } from "node:fs/promises";
import path from "node:path";

export const runtime = "nodejs";

export async function GET(
  _req: Request,
  {
    params,
  }: {
    params: Promise<{ date: string; slot: string }>;
  },
) {
  const { date, slot } = await params;
  const safeDate = date.replace(/[^0-9-]/g, "");
  const safeSlot = slot.replace(/[^A-Za-z0-9_-]/g, "");

  const filePath = path.join(
    process.cwd(),
    "..",
    "digests",
    "archive",
    safeDate,
    `${safeSlot}.json`,
  );

  try {
    const raw = await readFile(filePath, "utf-8");
    return NextResponse.json(JSON.parse(raw));
  } catch {
    return NextResponse.json({ error: "not_found" }, { status: 404 });
  }
}
