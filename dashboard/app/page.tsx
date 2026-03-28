import { readFile } from "node:fs/promises";
import path from "node:path";

import { DashboardClient } from "./_components/DashboardClient";
import type { DigestIndex } from "./_components/types";

async function getIndex(): Promise<DigestIndex> {
  const filePath = path.join(process.cwd(), "..", "digests", "archive", "index.json");
  try {
    const raw = await readFile(filePath, "utf-8");
    return JSON.parse(raw) as DigestIndex;
  } catch {
    return { timezone: "America/Chicago", days: [] };
  }
}

export default async function Page() {
  const index = await getIndex();
  return <DashboardClient index={index} />;
}
