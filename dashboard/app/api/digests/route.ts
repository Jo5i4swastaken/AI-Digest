import { NextResponse } from "next/server";
import { readFile } from "node:fs/promises";
import path from "node:path";

export const runtime = "nodejs";

export async function GET() {
  const filePath = path.join(process.cwd(), "..", "digests", "archive", "index.json");
  const raw = await readFile(filePath, "utf-8");
  return NextResponse.json(JSON.parse(raw));
}
