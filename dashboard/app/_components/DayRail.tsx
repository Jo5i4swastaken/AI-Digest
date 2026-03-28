"use client";

import type { DigestIndexDay } from "./types";
import { classNames, formatDateLabel } from "./utils";

export function DayRail({
  days,
  selectedDate,
  onSelectDate,
}: {
  days: DigestIndexDay[];
  selectedDate: string;
  onSelectDate: (date: string) => void;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-3">
      <div className="px-2 pb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
        Days
      </div>
      <div className="flex flex-col gap-1">
        {days.map((d) => {
          const active = d.date === selectedDate;
          return (
            <button
              key={d.date}
              type="button"
              onClick={() => onSelectDate(d.date)}
              className={classNames(
                "flex w-full items-center justify-between rounded-xl px-2 py-2 text-left text-sm transition",
                active
                  ? "bg-slate-900 text-white"
                  : "text-slate-700 hover:bg-slate-50",
              )}
            >
              <span className="truncate">{formatDateLabel(d.date)}</span>
              <span
                className={classNames(
                  "ml-3 shrink-0 rounded-full px-2 py-0.5 text-xs",
                  active ? "bg-white/15 text-white" : "bg-slate-100 text-slate-600",
                )}
              >
                {d.slots.length}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
