import { createContext, useContext, useMemo, useState, useEffect, type ReactNode } from "react";
import type { DateRange, Granularity } from "@/lib/api";
import { api } from "@/lib/api";

export const SEGMENTS = [
  { key: "Champion", label: "Champion", emoji: "🏆" },
  { key: "Loyal", label: "Loyal", emoji: "💚" },
  { key: "Potential", label: "Potential", emoji: "🌱" },
  { key: "At Risk", label: "At Risk", emoji: "⚠️" },
  { key: "Lost", label: "Lost", emoji: "❌" },
] as const;

export type SegmentKey = (typeof SEGMENTS)[number]["key"];

interface DashboardCtx {
  range: DateRange;
  setRange: (r: DateRange) => void;
  granularity: Granularity;
  setGranularity: (g: Granularity) => void;
  segments: SegmentKey[];
  setSegments: (s: SegmentKey[]) => void;
}

const Ctx = createContext<DashboardCtx | null>(null);

function toISO(d: Date) {
  return d.toISOString().slice(0, 10);
}

export function DashboardProvider({ children }: { children: ReactNode }) {
  const today = new Date();
  const past = new Date();
  past.setDate(today.getDate() - 90);

  const [range, setRange] = useState<DateRange>({
    d_from: toISO(past),
    d_to: toISO(today),
  });
  const [granularity, setGranularity] = useState<Granularity>("monthly");
  const [segments, setSegments] = useState<SegmentKey[]>([
    "Champion",
    "Loyal",
    "Potential",
    "At Risk",
    "Lost",
  ]);

  useEffect(() => {
    let mounted = true;
    api.dateBounds()
      .then((bounds) => {
        if (mounted && bounds.min_date && bounds.max_date) {
          setRange({ d_from: bounds.min_date, d_to: bounds.max_date });
        }
      })
      .catch((err) => console.error("Failed to fetch date bounds:", err));
    return () => {
      mounted = false;
    };
  }, []);

  const value = useMemo(
    () => ({ range, setRange, granularity, setGranularity, segments, setSegments }),
    [range, granularity, segments],
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useDashboard() {
  const v = useContext(Ctx);
  if (!v) throw new Error("useDashboard must be used inside <DashboardProvider>");
  return v;
}
