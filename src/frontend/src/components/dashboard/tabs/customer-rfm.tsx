import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis,
  Line, LineChart, ReferenceLine,
} from "recharts";
import { api } from "@/lib/api";
import { useDashboard, SEGMENTS } from "@/lib/dashboard-context";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";

const SEGMENT_COLORS: Record<string, string> = {
  "🏆 Champion": "var(--color-chart-1)",
  "💚 Loyal":    "var(--color-chart-2)",
  "🌱 Potential":"var(--color-chart-3)",
  "⚠️ At Risk": "var(--color-chart-4)",
  "❌ Lost":     "var(--color-chart-5)",
};

const currency = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
const number = (n: number) => new Intl.NumberFormat("en-US").format(n);

function TooltipBox({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-lg px-3 py-2 text-xs">
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-muted-foreground">{p.name}:</span>
          <span className="font-semibold">{typeof p.value === "number" ? number(p.value) : p.value}</span>
        </div>
      ))}
    </div>
  );
}

export function CustomerRFMTab() {
  const { range, segments: selectedSegKeys } = useDashboard();

  const rfmQ = useQuery({
    queryKey: ["rfm", range, selectedSegKeys],
    queryFn: () => api.rfm(range, selectedSegKeys),
    staleTime: 5 * 60 * 1000, // cache for 5 minutes
  });



  // Ensure rfmQ.data is always a proper array (api.rfm unwraps .rfm key)
  const allRows = Array.isArray(rfmQ.data) ? rfmQ.data : [];

  // All heavy computations wrapped in useMemo — only re-runs when data or filter changes
  const { rows, segCounts, segRevenue, pareto } = React.useMemo(() => {
    // Build the full emoji labels to match against API response
    const selectedSegLabels = SEGMENTS
      .filter((s) => selectedSegKeys.includes(s.key))
      .map((s) => `${s.emoji} ${s.label}`);

    // Filter bins by selected segments
    const filteredRows = allRows.filter((r) => selectedSegLabels.includes(r.segment));

    // Segment distribution: sum bin counts per segment
    const segCountMap: Record<string, number> = {};
    for (const r of filteredRows) {
      segCountMap[r.segment] = (segCountMap[r.segment] ?? 0) + ((r as any).count ?? 1);
    }
    const computedSegCounts = Object.entries(segCountMap).map(([segment, count]) => ({ segment, count }));

    // Revenue per segment: monetary × count per bin, summed
    const segRevMap: Record<string, number> = {};
    for (const r of filteredRows) {
      const rev = Number(r.monetary ?? 0) * ((r as any).count ?? 1);
      segRevMap[r.segment] = (segRevMap[r.segment] ?? 0) + rev;
    }
    const computedSegRevenue = Object.entries(segRevMap).map(([segment, revenue]) => ({ segment, revenue }));

    // Pareto — use ALL rows (not filtered) sorted by monetary descending
    const sortedBins = [...allRows].sort((a, b) => Number(b.monetary) - Number(a.monetary));
    const totalRev  = sortedBins.reduce((s, r) => s + Number(r.monetary ?? 0) * ((r as any).count ?? 1), 0);
    const totalCust = sortedBins.reduce((s, r) => s + ((r as any).count ?? 1), 0);

    let cumRev = 0;
    let cumCust = 0;
    const rawPareto: { pct_customers: number; pct_revenue: number }[] = [];
    rawPareto.push({ pct_customers: 0, pct_revenue: 0 });
    
    for (const bin of sortedBins) {
      const cnt = (bin as any).count ?? 1;
      cumCust += cnt;
      cumRev  += Number(bin.monetary ?? 0) * cnt;
      rawPareto.push({
        pct_customers: totalCust > 0 ? +((cumCust / totalCust) * 100).toFixed(1) : 0,
        pct_revenue:   totalRev  > 0 ? +((cumRev  / totalRev)  * 100).toFixed(1) : 0,
      });
    }

    // Decimate to max 100 points for Recharts performance
    const step = Math.max(1, Math.ceil(rawPareto.length / 100));
    const finalPareto = rawPareto.filter((_, idx) => idx % step === 0 || idx === rawPareto.length - 1);

    return { rows: filteredRows, segCounts: computedSegCounts, segRevenue: computedSegRevenue, pareto: finalPareto };
  }, [allRows, selectedSegKeys]);



  if (rfmQ.isLoading) {
    return <div className="grid min-h-[300px] place-items-center text-sm text-muted-foreground">Loading RFM data…</div>;
  }
  if (rfmQ.isError) {
    return <div className="grid min-h-[300px] place-items-center text-sm text-destructive">Failed to load RFM data. Check API connection.</div>;
  }

  return (
    <div className="space-y-6">
      {/* Segment distribution + Revenue share */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="glass rounded-2xl p-5">
          <h3 className="text-sm font-semibold">Segment Distribution</h3>
          <p className="text-xs text-muted-foreground">Customer count per RFM segment</p>
          <div className="mt-4 h-[280px]">
            {segCounts.length === 0 ? (
              <div className="grid h-full place-items-center text-xs text-muted-foreground">No segment data available</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={segCounts} layout="vertical" margin={{ left: 16, right: 24 }}>
                  <CartesianGrid horizontal={false} stroke="var(--color-border)" strokeDasharray="3 3" />
                  <XAxis type="number" tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }} tickLine={false} axisLine={false} />
                  <YAxis dataKey="segment" type="category" tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }} tickLine={false} axisLine={false} width={120} />
                  <Tooltip content={<TooltipBox />} />
                  <Bar dataKey="count" name="Customers" radius={[0, 6, 6, 0]} maxBarSize={28} isAnimationActive={false}>
                    {segCounts.map((e) => (
                      <Cell key={e.segment} fill={SEGMENT_COLORS[e.segment] ?? "var(--color-chart-1)"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="glass rounded-2xl p-5">
          <h3 className="text-sm font-semibold">Revenue by Segment</h3>
          <p className="text-xs text-muted-foreground">Total monetary value per segment</p>
          <div className="mt-4 h-[280px]">
            {segRevenue.length === 0 ? (
              <div className="grid h-full place-items-center text-xs text-muted-foreground">No revenue data available</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Tooltip content={<TooltipBox />} />
                  <Pie data={segRevenue} dataKey="revenue" nameKey="segment" innerRadius={60} outerRadius={100} paddingAngle={2} stroke="var(--color-background)" strokeWidth={2} isAnimationActive={false}>
                    {segRevenue.map((e) => (
                      <Cell key={e.segment} fill={SEGMENT_COLORS[e.segment] ?? "var(--color-chart-1)"} />
                    ))}
                  </Pie>
                  <Legend wrapperStyle={{ fontSize: 11, color: "var(--color-muted-foreground)" }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Scatter plot — Frequency vs Monetary, per segment */}
      <div className="glass rounded-2xl p-5">
        <h3 className="text-sm font-semibold">RFM Scatter — Frequency vs Monetary</h3>
        <p className="text-xs text-muted-foreground">Each dot = a customer group bin. Dot size = number of customers in bin.</p>
        <div className="mt-4 h-[380px]">
          {rows.length === 0 ? (
            <div className="grid h-full place-items-center text-xs text-muted-foreground">No scatter data — try selecting more segments</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <ScatterChart margin={{ top: 8, right: 24, left: 8, bottom: 0 }}>
                <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
                <XAxis
                  dataKey="frequency"
                  name="Frequency"
                  type="number"
                  tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  label={{ value: "Frequency (orders)", position: "insideBottom", offset: -4, fill: "var(--color-muted-foreground)", fontSize: 11 }}
                />
                <YAxis
                  dataKey="monetary"
                  name="Revenue"
                  type="number"
                  tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => `$${Math.round(v / 1000)}k`}
                />
                <ZAxis dataKey="count" range={[20, 400]} name="Customers in bin" />
                <Tooltip cursor={{ strokeDasharray: "3 3" }} content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const d = payload[0]?.payload;
                  return (
                    <div className="glass rounded-lg px-3 py-2 text-xs">
                      <div className="font-semibold mb-1">{d?.segment}</div>
                      <div>Frequency: {d?.frequency} orders</div>
                      <div>Revenue bin: {currency(Number(d?.monetary ?? 0))}</div>
                      <div>Avg recency: {Math.round(d?.recency ?? 0)} days</div>
                      <div className="font-semibold mt-1">Customers: {number((d as any)?.count ?? 1)}</div>
                    </div>
                  );
                }} />
                {SEGMENTS.map((s) => {
                  const segLabel = `${s.emoji} ${s.label}`;
                  const segData = rows
                    .filter((r) => r.segment === segLabel)
                    .map((r) => ({
                      ...r,
                      frequency: Number(r.frequency ?? 0),
                      monetary:  Number(r.monetary ?? 0),
                      recency:   Number(r.recency ?? 0),
                      // ZAxis dataKey="count" — must be a number, never undefined
                      count: Math.max(1, Number((r as any).count ?? 1)),
                    }));
                  if (segData.length === 0) return null;
                  return (
                    <Scatter
                      key={s.key}
                      name={segLabel}
                      data={segData}
                      fill={SEGMENT_COLORS[segLabel] ?? "var(--color-chart-1)"}
                      fillOpacity={0.75}
                      isAnimationActive={false}
                    />
                  );
                })}
                <Legend wrapperStyle={{ fontSize: 11, color: "var(--color-muted-foreground)" }} />
              </ScatterChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Pareto chart */}
      <div className="glass rounded-2xl p-5">
        <h3 className="text-sm font-semibold">Pareto — Revenue Concentration</h3>
        <p className="text-xs text-muted-foreground">Cumulative % of revenue generated by top X% of customers</p>
        <div className="mt-4 h-[260px]">
          {pareto.length === 0 ? (
            <div className="grid h-full place-items-center text-xs text-muted-foreground">No pareto data available</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={pareto} margin={{ top: 8, right: 24, left: 8, bottom: 0 }}>
                <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
                <XAxis
                  dataKey="pct_customers"
                  tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => `${v}%`}
                  label={{ value: "% Customers", position: "insideBottom", offset: -4, fill: "var(--color-muted-foreground)", fontSize: 11 }}
                />
                <YAxis
                  tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  tickFormatter={(v) => `${v}%`}
                  domain={[0, 100]}
                />
                <Tooltip content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  return (
                    <div className="glass rounded-lg px-3 py-2 text-xs">
                      <div>Top {payload[0]?.payload?.pct_customers}% customers</div>
                      <div className="font-semibold">→ {payload[0]?.value}% of revenue</div>
                    </div>
                  );
                }} />
                <ReferenceLine y={80} stroke="var(--color-chart-4)" strokeDasharray="3 3" label={{ position: 'insideTopLeft', value: '80% Revenue', fill: 'var(--color-muted-foreground)', fontSize: 10 }} />
                <ReferenceLine x={20} stroke="var(--color-chart-4)" strokeDasharray="3 3" label={{ position: 'insideBottomRight', value: '20% Customers', fill: 'var(--color-muted-foreground)', fontSize: 10 }} />
                <Line type="monotone" dataKey="pct_revenue" stroke="var(--color-chart-1)" strokeWidth={2.5} dot={false} name="Cumulative Revenue %" isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

    </div>
  );
}
