"use client";

import type { Slot } from "./types";
import { classNames, slotLabel } from "./utils";

const SLOTS: Slot[] = ["AM", "PM", "Evening"];

export function SlotTabs({
  value,
  onChange,
}: {
  value: Slot;
  onChange: (slot: Slot) => void;
}) {
  return (
    <div className="inline-flex rounded-2xl border border-slate-200 bg-white p-1">
      {SLOTS.map((slot) => {
        const active = slot === value;
        return (
          <button
            key={slot}
            type="button"
            onClick={() => onChange(slot)}
            className={classNames(
              "rounded-xl px-3 py-1.5 text-sm font-medium transition",
              active
                ? "bg-slate-900 text-white"
                : "text-slate-700 hover:bg-slate-50",
            )}
          >
            {slotLabel(slot)}
          </button>
        );
      })}
    </div>
  );
}
