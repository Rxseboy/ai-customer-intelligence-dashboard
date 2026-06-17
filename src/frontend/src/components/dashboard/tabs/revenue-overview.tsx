import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  Cell,
  Pie,
  PieChart,
} from "recharts";
import { CircleDollarSign, ShoppingCart, Users, Wallet } from "lucide-react";
import { api, type DateRange, type Granularity, type StatusBreakdown, type TrendPoint } from "@/lib/api";
import { useDashboard } from "@/lib/dashboard-context";
import { KpiCard } from "@/components/dashboard/kpi-card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

const currency = (n: number | undefined) =>
  typeof n === "number"
    ? new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0,
      }).format(n)
    : "—";

const number = (n: number | undefined) =>
  typeof n === "number" ? new Intl.NumberFormat("en-US").format(n) : "—";

function useKpis(r: DateRange, segments: string[]) {
  return useQuery({ queryKey: ["kpis", r, segments], queryFn: () => api.kpis(r, segments) });
}
function useTrend(r: DateRange, g: Granularity, segments: string[]) {
  return useQuery({ queryKey: ["trend", r, g, segments], queryFn: () => api.trend(r, g, segments) });
}
function useStatus(r: DateRange, segments: string[]) {
  return useQuery({ queryKey: ["status", r, segments], queryFn: () => api.status(r, segments) });
}

const STATUS_COLORS = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
];

function TooltipBox({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-lg px-3 py-2 text-xs">
      {label && <div className="mb-1 font-semibold">{label}</div>}
      {payload.map((p: any) => (
        <div key={p.dataKey} className="flex items-center gap-2">
          <span
            className="h-2 w-2 rounded-full"
            style={{ backgroundColor: p.color }}
          />
          <span className="text-muted-foreground">{p.name}:</span>
          <span className="font-semibold">
            {typeof p.value === "number"
              ? p.dataKey === "revenue"
                ? currency(p.value)
                : number(p.value)
              : p.value}
          </span>
        </div>
      ))}
    </div>
  );
}

export function RevenueOverviewTab() {
  const { range, granularity, segments } = useDashboard();
  const kpisQ = useKpis(range, segments);
  const trendQ = useTrend(range, granularity, segments);
  const statusQ = useStatus(range, segments);

  const k = kpisQ.data ?? {};
  
  const { trend, status } = useMemo(() => {
    const t: TrendPoint[] = (trendQ.data ?? []).map((d) => ({
      ...d,
      period: String(d.period ?? ""),
      revenue: Number(d.revenue ?? 0),
      orders: Number(d.orders ?? 0),
    }));
    const s: StatusBreakdown[] = (statusQ.data ?? []).map((d: any) => ({
      status: String(d.status ?? "unknown"),
      count: Number(d.count ?? d.cnt ?? 0),
      revenue: typeof d.revenue === "number" ? d.revenue : undefined,
    }));
    return { trend: t, status: s };
  }, [trendQ.data, statusQ.data]);

  return (
    <div className="space-y-6">
      {/* KPIs */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard
          label="Total Revenue"
          value={currency(k.revenue as number | undefined)}
          icon={<CircleDollarSign className="h-4 w-4" />}
          loading={kpisQ.isLoading}
          accent="primary"
        />
        <KpiCard
          label="Total Orders"
          value={number(k.orders as number | undefined)}
          icon={<ShoppingCart className="h-4 w-4" />}
          loading={kpisQ.isLoading}
          accent="teal"
        />
        <KpiCard
          label="Avg Order Value"
          value={currency(k.aov as number | undefined)}
          icon={<Wallet className="h-4 w-4" />}
          loading={kpisQ.isLoading}
          accent="violet"
        />
        <KpiCard
          label="Unique Customers"
          value={number(k.customers as number | undefined)}
          icon={<Users className="h-4 w-4" />}
          loading={kpisQ.isLoading}
          accent="amber"
        />
      </div>

      {/* Main chart + donut */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        <div className="glass rounded-2xl p-5 xl:col-span-2">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-semibold">Revenue & Orders</h3>
              <p className="text-xs text-muted-foreground">
                {granularity === "weekly" ? "Weekly" : "Monthly"} trend over the
                selected period
              </p>
            </div>
          </div>
          <div className="mt-4 h-[320px]">
            {trendQ.isError ? (
              <ErrorState />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={trend} margin={{ top: 8, right: 24, left: 8, bottom: 0 }}>
                  <defs>
                    <linearGradient id="revFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--color-chart-1)" stopOpacity={0.9} />
                      <stop offset="100%" stopColor="var(--color-chart-1)" stopOpacity={0.25} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
                  <XAxis dataKey="period" tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis yAxisId="left" tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${Math.round(v / 1000)}k`} />
                  <YAxis yAxisId="right" orientation="right" tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }} tickLine={false} axisLine={false} />
                  <Tooltip content={<TooltipBox />} cursor={{ fill: "var(--color-accent)", opacity: 0.3 }} />
                  <Legend wrapperStyle={{ fontSize: 11, color: "var(--color-muted-foreground)" }} />
                  <Bar yAxisId="left" dataKey="revenue" name="Revenue" fill="url(#revFill)" radius={[6, 6, 0, 0]} maxBarSize={36} isAnimationActive={false} />
                  <Line yAxisId="right" type="monotone" dataKey="orders" name="Orders" stroke="var(--color-chart-2)" strokeWidth={2.5} dot={{ r: 3, fill: "var(--color-chart-2)" }} activeDot={{ r: 5 }} isAnimationActive={false} />
                </ComposedChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="glass rounded-2xl p-5">
          <h3 className="text-sm font-semibold">Order Status</h3>
          <p className="text-xs text-muted-foreground">Breakdown by status</p>
          <div className="mt-4 h-[320px]">
            {statusQ.isError ? (
              <ErrorState />
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Tooltip content={<TooltipBox />} />
                  <Pie
                    data={status}
                    dataKey="count"
                    nameKey="status"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    stroke="var(--color-background)"
                    strokeWidth={2}
                    isAnimationActive={false}
                  >
                    {status.map((_, i) => (
                      <Cell key={i} fill={STATUS_COLORS[i % STATUS_COLORS.length]} />
                    ))}
                  </Pie>
                  <Legend wrapperStyle={{ fontSize: 11, color: "var(--color-muted-foreground)" }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="glass rounded-2xl p-5">
        <div className="mb-3 flex items-center justify-between">
          <div>
            <h3 className="text-sm font-semibold">Period Summary</h3>
            <p className="text-xs text-muted-foreground">
              {trend.length} {granularity === "weekly" ? "weeks" : "months"} in range
            </p>
          </div>
        </div>
        <div className="overflow-hidden rounded-lg border border-border/50">
          <Table>
            <TableHeader>
              <TableRow className="bg-background/40 hover:bg-background/40">
                <TableHead>Period</TableHead>
                <TableHead className="text-right">Revenue</TableHead>
                <TableHead className="text-right">Orders</TableHead>
                <TableHead className="text-right">AOV</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {trend.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground">
                    {trendQ.isLoading ? "Loading…" : "No data for selected range."}
                  </TableCell>
                </TableRow>
              )}
              {trend.map((row) => {
                const aov = row.orders > 0 ? row.revenue / row.orders : 0;
                return (
                  <TableRow key={row.period}>
                    <TableCell className="font-medium">{row.period}</TableCell>
                    <TableCell className="text-right">{currency(row.revenue)}</TableCell>
                    <TableCell className="text-right">{number(row.orders)}</TableCell>
                    <TableCell className="text-right">{currency(aov)}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      </div>
    </div>
  );
}

function ErrorState() {
  return (
    <div className="grid h-full place-items-center text-sm text-muted-foreground">
      Failed to load. Check API connection.
    </div>
  );
}
