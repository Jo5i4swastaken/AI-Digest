export type Slot = "AM" | "PM" | "Evening";

export type DigestCategory =
  | "product"
  | "open_source"
  | "agent_tooling"
  | "hardware"
  | "funding"
  | "ways_to_use";

export type DigestItem = {
  category: DigestCategory;
  title: string;
  url: string;
  source: string;
  published_at: string | null;
  why_it_matters: string;
  brief: string;
  details: string;
  is_update: boolean;
};

export type Digest = {
  generated_at: string;
  slot: Slot;
  timezone: string;
  items: DigestItem[];
};

export type DigestIndexSlotEntry = {
  slot: Slot;
  label: string;
  path: string;
  generated_at?: string;
  top?: string[];
  counts?: { total?: number };
};

export type DigestIndexDay = {
  date: string;
  slots: DigestIndexSlotEntry[];
};

export type DigestIndex = {
  timezone: string;
  days: DigestIndexDay[];
};
