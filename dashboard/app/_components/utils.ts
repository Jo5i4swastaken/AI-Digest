import type { DigestCategory, Slot } from "./types";

export function slotLabel(slot: Slot): string {
  if (slot === "AM") return "Morning";
  if (slot === "PM") return "Afternoon";
  return "Evening";
}

export const CATEGORY_LABEL: Record<DigestCategory, string> = {
  product: "Product",
  open_source: "Open source",
  agent_tooling: "Agent tooling",
  hardware: "Hardware",
  funding: "Funding",
  ways_to_use: "Ways to use",
};

export const CATEGORY_ORDER: DigestCategory[] = [
  "product",
  "open_source",
  "agent_tooling",
  "hardware",
  "funding",
  "ways_to_use",
];

export function formatDateLabel(isoDate: string): string {
  const [y, m, d] = isoDate.split("-").map((v) => Number(v));
  if (!y || !m || !d) return isoDate;
  const dt = new Date(Date.UTC(y, m - 1, d));
  return dt.toLocaleDateString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function classNames(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(" ");
}
