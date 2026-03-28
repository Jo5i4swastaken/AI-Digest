import { readFile } from "node:fs/promises";
import path from "node:path";

import Link from "next/link";

import type { Digest } from "../../../_components/types";
import { CATEGORY_LABEL, formatDateLabel, slotLabel } from "../../../_components/utils";

async function getDigest(date: string, slot: string): Promise<Digest | null> {
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
    return JSON.parse(raw) as Digest;
  } catch {
    return null;
  }
}

export default async function DigestPage({
  params,
}: {
  params: Promise<{ date: string; slot: string }>;
}) {
  const { date, slot } = await params;
  const digest = await getDigest(date, slot);

  if (!digest) {
    return (
      <div className="mx-auto max-w-3xl px-4 pb-16 pt-10">
        <Link href="/" className="text-sm font-semibold text-blue-700 hover:text-blue-800">
          Back
        </Link>
        <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6">
          <div className="text-lg font-semibold">Digest not found</div>
          <div className="mt-1 text-sm text-slate-600">
            No digest JSON exists for this date/slot.
          </div>
        </div>
      </div>
    );
  }

  const title = `${slotLabel(digest.slot)} AI Digest`;

  return (
    <div className="min-h-screen bg-[#fbfbfd]">
      <div className="mx-auto max-w-5xl px-4 pb-20 pt-10">
        <div className="flex items-center justify-between gap-4">
          <Link href="/" className="text-sm font-semibold text-blue-700 hover:text-blue-800">
            Dashboard
          </Link>
          <div className="text-xs text-slate-500">{digest.timezone}</div>
        </div>

        <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-[1fr_240px]">
          <article className="min-w-0">
            <header>
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                {formatDateLabel(date)} · {slotLabel(digest.slot)}
              </div>
              <h1 className="mt-2 text-3xl font-semibold tracking-tight text-slate-950 sm:text-4xl">
                {title}
              </h1>
              <p className="mt-4 max-w-2xl text-base leading-relaxed text-slate-700">
                Ultra-brief, high-signal updates. Click any item to open its primary source.
              </p>
            </header>

            <div className="mt-8 flex flex-col gap-6">
              {digest.items.map((it, idx) => (
                <section
                  key={`${it.url}-${idx}`}
                  className="rounded-3xl border border-slate-200 bg-white p-6"
                >
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      {CATEGORY_LABEL[it.category]}
                    </div>
                    <div className="text-xs text-slate-500">{it.source}</div>
                  </div>

                  <a
                    href={it.url}
                    target="_blank"
                    rel="noreferrer"
                    className="mt-2 block text-xl font-semibold leading-snug text-slate-950 hover:underline"
                  >
                    {it.title}
                  </a>

                  <div className="mt-3 text-sm leading-relaxed text-slate-700">{it.brief}</div>

                  <div className="mt-4 rounded-2xl bg-slate-50 px-4 py-3">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Why it matters
                    </div>
                    <div className="mt-1 text-sm leading-relaxed text-slate-700">
                      {it.why_it_matters}
                    </div>
                  </div>

                  <div className="mt-4 border-t border-slate-100 pt-4">
                    <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Detail
                    </div>
                    <div className="mt-2 text-sm leading-relaxed text-slate-700">{it.details}</div>
                  </div>
                </section>
              ))}
            </div>
          </article>

          <aside className="lg:sticky lg:top-10 lg:self-start">
            <div className="rounded-3xl border border-slate-200 bg-white p-5">
              <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                Snapshot
              </div>
              <div className="mt-2 text-sm text-slate-800">
                <div className="font-semibold">{formatDateLabel(date)}</div>
                <div className="mt-1 text-slate-600">{slotLabel(digest.slot)}</div>
                <div className="mt-3 text-slate-600">Items: {digest.items.length}</div>
              </div>

              <div className="mt-5 border-t border-slate-100 pt-5">
                <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Source links
                </div>
                <div className="mt-3 flex flex-col gap-2">
                  {digest.items.slice(0, 10).map((it, idx) => (
                    <a
                      key={`${it.url}-${idx}`}
                      href={it.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm text-blue-700 hover:text-blue-800"
                    >
                      {it.title}
                    </a>
                  ))}
                </div>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
