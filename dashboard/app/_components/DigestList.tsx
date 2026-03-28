"use client";

import Link from "next/link";
import type { Digest, DigestCategory } from "./types";
import { CATEGORY_LABEL, classNames } from "./utils";

export function DigestList({
  digest,
  selectedCats,
  query,
  date,
  slot,
}: {
  digest: Digest | null;
  selectedCats: Set<DigestCategory>;
  query: string;
  date: string;
  slot: string;
}) {
  if (!digest) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-600">
        No digest found for this slot.
      </div>
    );
  }

  const q = query.trim().toLowerCase();
  const items = digest.items.filter((it) => {
    if (selectedCats.size > 0 && !selectedCats.has(it.category)) return false;
    if (!q) return true;
    const hay = `${it.title} ${it.brief} ${it.details} ${it.source}`.toLowerCase();
    return hay.includes(q);
  });

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between gap-4">
        <div className="text-sm text-slate-600">
          Showing <span className="font-semibold text-slate-900">{items.length}</span> items
        </div>
        <Link
          href={`/digest/${encodeURIComponent(date)}/${encodeURIComponent(slot)}`}
          className="text-sm font-semibold text-blue-700 hover:text-blue-800"
        >
          Open as article
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-3">
        {items.map((it) => (
          <a
            key={`${it.url}-${it.title}`}
            href={it.url}
            target="_blank"
            rel="noreferrer"
            className="group rounded-2xl border border-slate-200 bg-white p-4 transition hover:border-slate-300"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <div className="text-[15px] font-semibold leading-snug text-slate-950 group-hover:underline">
                  {it.title}
                </div>
                <div className="mt-1 text-sm leading-relaxed text-slate-700">{it.brief}</div>
              </div>
              <div
                className={classNames(
                  "shrink-0 rounded-full border px-2.5 py-1 text-xs font-medium",
                  it.is_update
                    ? "border-amber-200 bg-amber-50 text-amber-900"
                    : "border-slate-200 bg-slate-50 text-slate-700",
                )}
              >
                {CATEGORY_LABEL[it.category]}
              </div>
            </div>

            <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-500">
              <span className="font-medium text-slate-600">{it.source}</span>
              <span className="text-slate-300">•</span>
              <span className="italic text-slate-600">{it.why_it_matters}</span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
