"use client";

import { useEffect, useMemo, useState } from "react";
import type { Digest, DigestCategory, DigestIndex, Slot } from "./types";
import { CATEGORY_ORDER, slotLabel } from "./utils";
import { DayRail } from "./DayRail";
import { SlotTabs } from "./SlotTabs";
import { FilterBar } from "./FilterBar";
import { DigestList } from "./DigestList";

export function DashboardClient({ index }: { index: DigestIndex }) {
  const days = index.days;
  const initialDate = days[0]?.date ?? "";

  const [selectedDate, setSelectedDate] = useState(initialDate);
  const [slot, setSlot] = useState<Slot>("AM");
  const [digest, setDigest] = useState<Digest | null>(null);
  const [query, setQuery] = useState("");
  const [selectedCats, setSelectedCats] = useState<Set<DigestCategory>>(
    () => new Set<DigestCategory>(),
  );
  const [loading, setLoading] = useState(false);
  const [runKey, setRunKey] = useState<string>("");
  const [runStatus, setRunStatus] = useState<string>("");

  useEffect(() => {
    const saved = sessionStorage.getItem("run_digest_key") ?? "";
    if (saved) setRunKey(saved);
  }, []);

  const availableSlots = useMemo(() => {
    const d = days.find((x) => x.date === selectedDate);
    const slots = d?.slots.map((s) => s.slot) ?? [];
    return new Set(slots);
  }, [days, selectedDate]);

  useEffect(() => {
    if (!selectedDate) return;

    const preferred: Slot[] = ["AM", "PM", "Evening"];
    const next = preferred.find((s) => availableSlots.has(s)) ?? preferred[0];
    setSlot(next);
  }, [availableSlots, selectedDate]);

  useEffect(() => {
    async function load() {
      if (!selectedDate) return;
      setLoading(true);
      try {
        const res = await fetch(`/api/digests/${selectedDate}/${slot}`, {
          cache: "no-store",
        });
        if (!res.ok) {
          setDigest(null);
          return;
        }
        const data = (await res.json()) as Digest;
        setDigest(data);
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [selectedDate, slot]);

  function toggleCat(cat: DigestCategory) {
    setSelectedCats((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  }

  function clearFilters() {
    setSelectedCats(new Set());
    setQuery("");
  }

  const hasFilters = selectedCats.size > 0 || query.trim().length > 0;

  async function triggerRun(nextSlot: Slot) {
    setRunStatus(`Triggering ${nextSlot}…`);
    try {
      const res = await fetch("/api/run-digest", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(runKey ? { "x-run-key": runKey } : {}),
        },
        body: JSON.stringify({ slot: nextSlot, email: false }),
      });

      if (!res.ok) {
        const txt = await res.text();
        setRunStatus(`Failed (${res.status}): ${txt.slice(0, 140)}`);
        return;
      }

      setRunStatus(`Queued ${nextSlot}. Check Actions for progress.`);
    } catch (e) {
      setRunStatus(`Failed: ${String(e)}`);
    }
  }

  function setAndSaveRunKey() {
    const next = window.prompt("Run key", runKey) ?? "";
    const trimmed = next.trim();
    setRunKey(trimmed);
    if (trimmed) sessionStorage.setItem("run_digest_key", trimmed);
    else sessionStorage.removeItem("run_digest_key");
  }

  return (
    <div className="mx-auto max-w-6xl px-4 pb-14 pt-10">
      <div className="flex flex-col gap-6">
        <header className="flex flex-col gap-3">
          <div className="flex items-end justify-between gap-6">
            <div>
              <div className="text-3xl font-semibold tracking-tight text-slate-950">
                AI Digest
              </div>
              <div className="mt-1 max-w-2xl text-sm leading-relaxed text-slate-600">
                Three snapshots a day. Built for high-signal product releases, open source,
                agent tooling, hardware, funding, and practical workflows.
              </div>
            </div>
            <div className="hidden items-center gap-2 sm:flex">
              <div className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700">
                {index.timezone}
              </div>
              <button
                type="button"
                onClick={setAndSaveRunKey}
                className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                Test runs
              </button>
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                onClick={() => void triggerRun("AM")}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Run AM
              </button>
              <button
                type="button"
                onClick={() => void triggerRun("PM")}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Run PM
              </button>
              <button
                type="button"
                onClick={() => void triggerRun("Evening")}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Run Evening
              </button>
            </div>
            {runStatus ? <div className="text-sm text-slate-600">{runStatus}</div> : null}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <SlotTabs value={slot} onChange={setSlot} />
            <div className="flex items-center gap-2">
              {hasFilters ? (
                <button
                  type="button"
                  onClick={clearFilters}
                  className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                >
                  Clear filters
                </button>
              ) : null}
              <div className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600">
                {slotLabel(slot)}
              </div>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[280px_1fr]">
          <aside className="lg:sticky lg:top-6 lg:self-start">
            <DayRail
              days={days}
              selectedDate={selectedDate}
              onSelectDate={setSelectedDate}
            />
          </aside>

          <main className="flex flex-col gap-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-4">
              <FilterBar
                selected={selectedCats}
                onToggle={toggleCat}
                query={query}
                onQuery={setQuery}
              />
            </div>

            {loading ? (
              <div className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-600">
                Loading…
              </div>
            ) : null}

            {!loading ? (
              <DigestList
                digest={digest}
                selectedCats={selectedCats}
                query={query}
                date={selectedDate}
                slot={slot}
              />
            ) : null}

            <div className="pt-6 text-xs text-slate-500">
              Data source: <code className="rounded bg-slate-100 px-1.5 py-0.5">digests/archive</code>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
