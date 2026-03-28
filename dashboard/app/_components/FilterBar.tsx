"use client";

import type { DigestCategory } from "./types";
import { CATEGORY_LABEL, CATEGORY_ORDER, classNames } from "./utils";

export function FilterBar({
  selected,
  onToggle,
  query,
  onQuery,
}: {
  selected: Set<DigestCategory>;
  onToggle: (cat: DigestCategory) => void;
  query: string;
  onQuery: (next: string) => void;
}) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        {CATEGORY_ORDER.map((cat) => {
          const isOn = selected.has(cat);
          return (
            <button
              key={cat}
              type="button"
              onClick={() => onToggle(cat)}
              className={classNames(
                "rounded-full border px-3 py-1 text-sm transition",
                isOn
                  ? "border-blue-600 bg-blue-50 text-blue-900"
                  : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50",
              )}
            >
              {CATEGORY_LABEL[cat]}
            </button>
          );
        })}
      </div>

      <div className="flex items-center gap-2">
        <div className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2">
          <input
            value={query}
            onChange={(e) => onQuery(e.target.value)}
            placeholder="Search titles, briefs, sources…"
            className="w-full bg-transparent text-sm outline-none placeholder:text-slate-400"
          />
        </div>
      </div>
    </div>
  );
}
