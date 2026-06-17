import React from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer,
  Tooltip, XAxis, YAxis, PieChart, Pie, LineChart, Line, ReferenceLine,
} from "recharts";
import { AlertTriangle, TrendingDown, Users, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useDashboard } from "@/lib/dashboard-context";
import { cn } from "@/lib/utils";

const currency = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
const number = (n: number) => new Intl.NumberFormat("en-US").format(n);
const pct = (n: number) => `${n.toFixed(1)}%`;

// Segment color mapping (must match backend emoji labels)
const SEGMENT_COLORS: Record<string, string> = {
  "🏆 Champion":  "var(--color-chart-1)",
  "💚 Loyal":     "var(--color-chart-2)",
  "🌱 Potential": "var(--color-chart-3)",
  "⚠️ At Risk":  "var(--color-chart-4)",
  "❌ Lost":      "var(--color-chart-5)",
};

// Churn risk level for each segment
const CHURN_RISK: Record<string, number> = {
  "🏆 Champion":  5,
  "💚 Loyal":     12,
  "🌱 Potential": 30,
  "⚠️ At Risk":  65,
  "❌ Lost":      85,
};

function TooltipBox({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-lg px-3 py-2 text-xs">
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-muted-foreground">{p.name}:</span>
          <span className="font-semibold">
            {p.name?.toLowerCase().includes("revenue") ? currency(p.value) : number(p.value)}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Churn Risk Predictor Widget ──────────────────────────────────────────────

function ChurnPredictor() {
  const [recency, setRecency]   = React.useState(60);
  const [frequency, setFreq]    = React.useState(2);
  const [monetary, setMonetary] = React.useState(100);

  const churnMut = useMutation({
    mutationFn: () => api.predictChurn({ recency, frequency, monetary }),
  });

  const result = churnMut.data;
  const riskColor = result && typeof result.churn_probability === 'number'
    ? result.churn_probability >= 0.6 ? "text-red-400"
    : result.churn_probability >= 0.3 ? "text-amber-400"
    : "text-emerald-400"
    : "";

  return (
    <div className="glass rounded-2xl p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="p-2 bg-amber-500/10 rounded-lg text-amber-400">
          <AlertTriangle className="w-5 h-5" />
        </div>
        <div>
          <h3 className="text-sm font-semibold">Real-time Churn Predictor</h3>
          <p className="text-xs text-muted-foreground">XGBoost model — adjust inputs and predict</p>
        </div>
      </div>

      <div className="space-y-3 mb-5">
        {[
          { label: "Recency (days since last order)", val: recency,    setter: setRecency,   min: 0,  max: 365 },
          { label: "Frequency (total orders)",        val: frequency,  setter: setFreq,      min: 1,  max: 100 },
          { label: "Monetary (total spend $)",        val: monetary,   setter: setMonetary,  min: 0,  max: 10000 },
        ].map(({ label, val, setter, min, max }) => (
          <div key={label}>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-muted-foreground">{label}</span>
              <span className="font-medium">{val}</span>
            </div>
            <input
              type="range" min={min} max={max}
              value={val}
              onChange={(e) => setter(Number(e.target.value))}
              className="w-full accent-primary"
            />
          </div>
        ))}
      </div>

      <Button
        className="w-full bg-gradient-to-br from-primary to-chart-2 shadow-[var(--glow-primary)]"
        onClick={() => churnMut.mutate()}
        disabled={churnMut.isPending}
      >
        {churnMut.isPending ? "Predicting…" : "Predict Churn Risk"}
      </Button>

      {churnMut.isError && (
        <p className="mt-3 text-xs text-destructive">Prediction failed — check if backend is running.</p>
      )}

      {result && (
        <div className="mt-4 space-y-3">
          <div className="flex items-center justify-between rounded-lg bg-background/40 px-4 py-3">
            <span className="text-xs text-muted-foreground">Risk Level</span>
            <span className={cn("text-sm font-bold", riskColor)}>{result.risk_level}</span>
          </div>
          <div>
            <div className="flex justify-between text-xs text-muted-foreground mb-1">
              <span>Churn Probability</span>
              <span className={cn("font-semibold", riskColor)}>
                {(result.churn_probability * 100).toFixed(1)}%
              </span>
            </div>
            <div className="h-3 w-full overflow-hidden rounded-full bg-secondary">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-700",
                  result.churn_probability >= 0.6 ? "bg-red-400"
                  : result.churn_probability >= 0.3 ? "bg-amber-400"
                  : "bg-emerald-400"
                )}
                style={{ width: `${result.churn_probability * 100}%` }}
              />
            </div>
          </div>
          <div className="rounded-lg bg-background/40 px-3 py-2 text-xs text-muted-foreground">
            {result.message}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main Tab ──────────────────────────────────────────────────────────────────

export function ChurnTab() {
  const { range, segments: selectedSegKeys } = useDashboard();

  // Use RFM aggregated segment data for churn distribution
  const rfmQ = useQuery({
    queryKey: ["rfm", range, selectedSegKeys],
    queryFn: () => api.rfm(range, selectedSegKeys),
    staleTime: 5 * 60 * 1000,
  });

  const insightsQ = useQuery({
    queryKey: ["insights", range, selectedSegKeys],
    queryFn: () => api.insights(range, selectedSegKeys),
    staleTime: 5 * 60 * 1000,
  });

  const rfmData = rfmQ.data ?? [];
  const insights = insightsQ.data;

  // Aggregate customer counts and revenue per segment from RFM bins
  const segAgg = React.useMemo(() => {
    const map: Record<string, { customers: number; revenue: number; churnRisk: number }> = {};
    for (const row of rfmData) {
      const seg = row.segment as string;
      const cnt = Number((row as any).count ?? 1);
      const rev = Number(row.monetary ?? 0) * cnt;
      if (!map[seg]) map[seg] = { customers: 0, revenue: 0, churnRisk: CHURN_RISK[seg] ?? 50 };
      map[seg].customers += cnt;
      map[seg].revenue   += rev;
    }
    return Object.entries(map).map(([segment, v]) => ({ segment, ...v }))
      .sort((a, b) => b.churnRisk - a.churnRisk);
  }, [rfmData]);

  const atRiskCustomers = segAgg
    .filter(s => s.segment === "⚠️ At Risk" || s.segment === "❌ Lost")
    .reduce((sum, s) => sum + s.customers, 0);

  const totalCustomers = segAgg.reduce((sum, s) => sum + s.customers, 0);
  const atRiskRevenue  = segAgg
    .filter(s => s.segment === "⚠️ At Risk" || s.segment === "❌ Lost")
    .reduce((sum, s) => sum + s.revenue, 0);

  const isLoading = rfmQ.isLoading || insightsQ.isLoading;

  if (isLoading) {
    return <div className="grid min-h-[300px] place-items-center text-sm text-muted-foreground">Loading churn data…</div>;
  }

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        {[
          {
            label: "At-Risk Customers",
            value: number(atRiskCustomers),
            sub: `${totalCustomers > 0 ? ((atRiskCustomers / totalCustomers) * 100).toFixed(1) : 0}% of total`,
            icon: Users,
            color: "text-red-400",
            bg: "bg-red-400/10",
          },
          {
            label: "Revenue at Risk",
            value: currency(atRiskRevenue),
            sub: "From At Risk + Lost segments",
            icon: TrendingDown,
            color: "text-amber-400",
            bg: "bg-amber-400/10",
          },
          {
            label: "Overall Churn Rate",
            value: pct(insights?.churn_rate_pct ?? 0),
            sub: "From ML churn labels",
            icon: Activity,
            color: "text-primary",
            bg: "bg-primary/10",
          },
        ].map(({ label, value, sub, icon: Icon, color, bg }) => (
          <div key={label} className="glass rounded-2xl p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-xs text-muted-foreground">{label}</p>
                <p className={cn("mt-1 text-2xl font-bold", color)}>{value}</p>
                <p className="mt-1 text-xs text-muted-foreground">{sub}</p>
              </div>
              <div className={cn("rounded-xl p-2.5", bg)}>
                <Icon className={cn("h-5 w-5", color)} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Segment risk bar chart + pie */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="glass rounded-2xl p-5">
          <h3 className="text-sm font-semibold">Estimated Churn Risk by Segment</h3>
          <p className="text-xs text-muted-foreground">% probability of churn per RFM segment (business rule)</p>
          <div className="mt-4 h-[280px]">
            {segAgg.length === 0 ? (
              <div className="grid h-full place-items-center text-xs text-muted-foreground">No segment data</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={segAgg} layout="vertical" margin={{ left: 16, right: 40 }}>
                  <CartesianGrid horizontal={false} stroke="var(--color-border)" strokeDasharray="3 3" />
                  <XAxis type="number" domain={[0, 100]} tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => `${v}%`} />
                  <YAxis dataKey="segment" type="category" tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }} tickLine={false} axisLine={false} width={130} />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const d = payload[0]?.payload;
                      return (
                        <div className="glass rounded-lg px-3 py-2 text-xs">
                          <div className="font-semibold mb-1">{d?.segment}</div>
                          <div>Churn risk: <span className="font-bold">{d?.churnRisk}%</span></div>
                          <div>Customers: {number(d?.customers)}</div>
                          <div>Revenue: {currency(d?.revenue)}</div>
                        </div>
                      );
                    }}
                  />
                  <ReferenceLine x={50} stroke="var(--color-destructive)" strokeDasharray="4 2" strokeWidth={1.5} />
                  <Bar dataKey="churnRisk" name="Churn Risk %" radius={[0, 6, 6, 0]} maxBarSize={28} isAnimationActive={false}>
                    {segAgg.map((e) => (
                      <Cell key={e.segment} fill={SEGMENT_COLORS[e.segment] ?? "var(--color-chart-3)"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="glass rounded-2xl p-5">
          <h3 className="text-sm font-semibold">Customer Distribution by Segment</h3>
          <p className="text-xs text-muted-foreground">Proportion of customers in each health status</p>
          <div className="mt-4 h-[280px]">
            {segAgg.length === 0 ? (
              <div className="grid h-full place-items-center text-xs text-muted-foreground">No segment data</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null;
                      const d = payload[0];
                      return (
                        <div className="glass rounded-lg px-3 py-2 text-xs">
                          <div className="font-semibold">{d.name}</div>
                          <div>Customers: {number(d.value as number)}</div>
                          <div>Share: {totalCustomers > 0 ? pct(((d.value as number) / totalCustomers) * 100) : "—"}</div>
                        </div>
                      );
                    }}
                  />
                  <Pie
                    data={segAgg}
                    dataKey="customers"
                    nameKey="segment"
                    innerRadius={55}
                    outerRadius={100}
                    paddingAngle={2}
                    stroke="var(--color-background)"
                    strokeWidth={2}
                    isAnimationActive={false}
                  >
                    {segAgg.map((e) => (
                      <Cell key={e.segment} fill={SEGMENT_COLORS[e.segment] ?? "var(--color-chart-3)"} />
                    ))}
                  </Pie>
                  <Legend wrapperStyle={{ fontSize: 11, color: "var(--color-muted-foreground)" }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>

      {/* Revenue by segment bar chart */}
      <div className="glass rounded-2xl p-5">
        <h3 className="text-sm font-semibold">Revenue at Risk Breakdown</h3>
        <p className="text-xs text-muted-foreground">Total revenue per customer segment — focus recovery on At Risk + Lost</p>
        <div className="mt-4 h-[260px]">
          {segAgg.length === 0 ? (
            <div className="grid h-full place-items-center text-xs text-muted-foreground">No revenue data</div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={segAgg} margin={{ top: 8, right: 24, left: 8, bottom: 0 }}>
                <CartesianGrid vertical={false} stroke="var(--color-border)" strokeDasharray="3 3" />
                <XAxis dataKey="segment" tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }} tickLine={false} axisLine={false} />
                <YAxis tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${Math.round(v / 1000)}k`} />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0]?.payload;
                    return (
                      <div className="glass rounded-lg px-3 py-2 text-xs">
                        <div className="font-semibold mb-1">{d?.segment}</div>
                        <div>Revenue: {currency(d?.revenue ?? 0)}</div>
                        <div>Customers: {number(d?.customers ?? 0)}</div>
                        <div>Churn risk: {d?.churnRisk}%</div>
                      </div>
                    );
                  }}
                />
                <Bar dataKey="revenue" name="Revenue" radius={[6, 6, 0, 0]} maxBarSize={60} isAnimationActive={false}>
                  {segAgg.map((e) => (
                    <Cell key={e.segment} fill={SEGMENT_COLORS[e.segment] ?? "var(--color-chart-3)"} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Retention suggestions table */}
      <div className="glass rounded-2xl p-5">
        <h3 className="mb-1 text-sm font-semibold">Recommended Retention Actions</h3>
        <p className="text-xs text-muted-foreground mb-4">Prioritized actions based on segment churn risk</p>
        <div className="overflow-hidden rounded-lg border border-border/50">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-background/40 text-xs text-muted-foreground">
                <th className="px-4 py-2.5 text-left font-medium">Segment</th>
                <th className="px-4 py-2.5 text-right font-medium">Customers</th>
                <th className="px-4 py-2.5 text-right font-medium">Churn Risk</th>
                <th className="px-4 py-2.5 text-left font-medium">Recommended Action</th>
              </tr>
            </thead>
            <tbody>
              {[
                { seg: "❌ Lost",      action: "Reactivation campaign — last-chance discount", urgency: "Critical" },
                { seg: "⚠️ At Risk",  action: "Win-back email + personalized offer",          urgency: "High" },
                { seg: "🌱 Potential", action: "Loyalty program enrollment + upsell",          urgency: "Medium" },
                { seg: "💚 Loyal",    action: "VIP perks + referral incentive",               urgency: "Low" },
                { seg: "🏆 Champion", action: "Ambassador program + early access",             urgency: "Maintain" },
              ].map(({ seg, action, urgency }) => {
                const info = segAgg.find((s) => s.segment === seg);
                const urgencyColor = urgency === "Critical" ? "text-red-400" : urgency === "High" ? "text-amber-400" : urgency === "Medium" ? "text-yellow-400" : "text-emerald-400";
                return (
                  <tr key={seg} className="border-t border-border/40 hover:bg-background/20">
                    <td className="px-4 py-3 font-medium">{seg}</td>
                    <td className="px-4 py-3 text-right text-muted-foreground">{number(info?.customers ?? 0)}</td>
                    <td className={cn("px-4 py-3 text-right font-semibold", urgencyColor)}>{info?.churnRisk ?? "—"}%</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{action}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Live predictor */}
      <ChurnPredictor />
    </div>
  );
}
