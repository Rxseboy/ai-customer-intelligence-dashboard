import type { ReactNode } from "react";
import { ArrowUpRight, TrendingDown, TrendingUp } from "lucide-react";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

interface KpiCardProps {
  label: string;
  value: ReactNode;
  delta?: number; // pct
  icon?: ReactNode;
  loading?: boolean;
  accent?: "primary" | "teal" | "violet" | "amber";
}

const accents: Record<NonNullable<KpiCardProps["accent"]>, string> = {
  primary: "from-primary/30 to-primary/0",
  teal: "from-chart-2/30 to-chart-2/0",
  violet: "from-chart-3/30 to-chart-3/0",
  amber: "from-chart-4/30 to-chart-4/0",
};

export function KpiCard({
  label,
  value,
  delta,
  icon,
  loading,
  accent = "primary",
}: KpiCardProps) {
  const positive = (delta ?? 0) >= 0;
  return (
    <div className="glass glass-hover relative overflow-hidden rounded-2xl p-5">
      <div
        className={cn(
          "pointer-events-none absolute -right-10 -top-10 h-40 w-40 rounded-full bg-gradient-to-br blur-2xl opacity-60",
          accents[accent],
        )}
      />
      <div className="relative">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {label}
          </span>
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-background/50 text-muted-foreground">
            {icon ?? <ArrowUpRight className="h-4 w-4" />}
          </div>
        </div>
        <div className="mt-3">
          {loading ? (
            <Skeleton className="h-8 w-32" />
          ) : (
            <div className="text-2xl font-bold tracking-tight">{value}</div>
          )}
        </div>
        {typeof delta === "number" && !loading && (
          <div
            className={cn(
              "mt-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
              positive
                ? "bg-success/15 text-[color:var(--success)]"
                : "bg-destructive/15 text-destructive",
            )}
          >
            {positive ? (
              <TrendingUp className="h-3 w-3" />
            ) : (
              <TrendingDown className="h-3 w-3" />
            )}
            {positive ? "+" : ""}
            {delta.toFixed(1)}%
          </div>
        )}
      </div>
    </div>
  );
}
