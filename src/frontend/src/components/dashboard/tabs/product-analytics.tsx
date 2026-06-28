import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend,
  ResponsiveContainer, Tooltip, Treemap, XAxis, YAxis,
} from "recharts";
import { TrendingUp, Package, Tag, Layers } from "lucide-react";
import { api } from "@/lib/api";
import { useDashboard } from "@/lib/dashboard-context";

const currency = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
const number = (n: number) => new Intl.NumberFormat("en-US").format(n);

const BRAND_COLORS = [
  "#6366f1", "#22d3ee", "#f59e0b", "#10b981", "#f43f5e",
  "#8b5cf6", "#14b8a6", "#fb923c", "#a3e635", "#e879f9",
  "#38bdf8", "#fbbf24", "#34d399", "#f87171", "#818cf8",
];

// ── Treemap Block ─────────────────────────────────────────────────────────────
const TREEMAP_COLORS = [
  "#6366f1", "#8b5cf6", "#a855f7", "#ec4899", "#f43f5e",
  "#f59e0b", "#10b981", "#14b8a6", "#22d3ee", "#38bdf8",
];

function TreemapBlock(props: any) {
  const { x, y, width, height, name, value, index } = props;
  if (width < 30 || height < 20) return null;
  const color = TREEMAP_COLORS[index % TREEMAP_COLORS.length];
  return (
    <g>
      <rect
        x={x} y={y} width={width} height={height}
        style={{ fill: color, fillOpacity: 0.82, stroke: "#0f0f0f", strokeWidth: 2, rx: 4 }}
      />
      {width > 55 && height > 28 && (
        <>
          <text
            x={x + width / 2} y={y + height / 2 - (height > 50 ? 8 : 0)}
            textAnchor="middle" fill="#fff" fontSize={Math.min(12, width / 8)}
            fontWeight={700} style={{ filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.9))" }}
          >
            {name.length > 14 ? name.slice(0, 13) + "…" : name}
          </text>
          {height > 46 && (
            <text
              x={x + width / 2} y={y + height / 2 + 12}
              textAnchor="middle" fill="rgba(255,255,255,0.85)" fontSize={10} fontWeight={500}
            >
              {currency(value)}
            </text>
          )}
        </>
      )}
    </g>
  );
}

// ── Custom Tooltip ─────────────────────────────────────────────────────────────
function TooltipBox({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-lg px-3 py-2 text-xs shadow-xl">
      {payload.map((p: any) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-muted-foreground">{p.name}:</span>
          <span className="font-semibold">
            {p.name === "Revenue" ? currency(p.value) : number(p.value)}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────────
export function ProductAnalyticsTab() {
  const { range, segments } = useDashboard();

  const productsQ = useQuery({
    queryKey: ["products", range, segments],
    queryFn: () => api.products(range, 25, segments),
  });
  const categoriesQ = useQuery({
    queryKey: ["categories", range, segments],
    queryFn: () => api.categories(range, segments),
  });

  const products   = productsQ.data ?? [];
  const categories = categoriesQ.data ?? [];

  const { brands, treemapData, topProducts, maxRevenue } = useMemo(() => {
    const brandMap = products.reduce<Record<string, { revenue: number; units: number }>>((acc, p) => {
      const brand = String(p.brand ?? "Unknown");
      if (!acc[brand]) acc[brand] = { revenue: 0, units: 0 };
      acc[brand].revenue += Number(p.revenue ?? 0);
      acc[brand].units   += Number(p.units ?? 0);
      return acc;
    }, {});

    const brands = Object.entries(brandMap)
      .map(([brand, v]) => ({ brand, ...v }))
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 15);

    const treemapData = categories.slice(0, 30).map((c, i) => ({
      name:  String(c.category),
      size:  Number(c.revenue ?? 0),
      value: Number(c.revenue ?? 0),
      index: i,
    }));

    const topProducts = products.slice(0, 25).map((p) => ({
      product: String(p.product ?? p.name ?? "Unknown"),
      revenue: Number(p.revenue ?? 0),
      units:   Number(p.units ?? 0),
    }));

    const maxRevenue = topProducts.length > 0 ? topProducts[0].revenue : 1;

    return { brands, treemapData, topProducts, maxRevenue };
  }, [products, categories]);

  const isLoading = productsQ.isLoading || categoriesQ.isLoading;
  const isError   = productsQ.isError   || categoriesQ.isError;

  if (isLoading) {
    return (
      <div className="grid min-h-[400px] place-items-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Loading product analytics…</p>
        </div>
      </div>
    );
  }
  if (isError) {
    return (
      <div className="grid min-h-[400px] place-items-center">
        <p className="text-sm text-destructive">Failed to load products. Check API connection.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">

      {/* ── Row 1: Top Products table + Category Treemap ── */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-5">

        {/* Top 25 Products — ranked table with inline revenue bar */}
        <div className="glass rounded-2xl p-5 xl:col-span-3 flex flex-col">
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded-lg bg-primary/10 text-primary"><Package className="h-4 w-4" /></div>
            <h3 className="text-sm font-semibold">Top 25 Products by Revenue</h3>
          </div>
          <p className="text-xs text-muted-foreground mb-4 pl-8">Sorted by total revenue · hover for full name</p>

          <div className="overflow-auto flex-1">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border/60">
                  <th className="text-left py-2 px-1 text-muted-foreground font-medium w-7">#</th>
                  <th className="text-left py-2 px-2 text-muted-foreground font-medium">Product</th>
                  <th className="text-left py-2 px-2 text-muted-foreground font-medium w-32 hidden sm:table-cell">Revenue bar</th>
                  <th className="text-right py-2 px-2 text-muted-foreground font-medium">Revenue</th>
                  <th className="text-right py-2 px-2 text-muted-foreground font-medium hidden md:table-cell">Units</th>
                </tr>
              </thead>
              <tbody>
                {topProducts.map((p, i) => {
                  const pct = Math.max(4, (p.revenue / maxRevenue) * 100);
                  const medal = i === 0 ? "🥇" : i === 1 ? "🥈" : i === 2 ? "🥉" : null;
                  return (
                    <tr key={i} className="border-b border-border/30 hover:bg-white/5 transition-colors group">
                      <td className="py-2 px-1 text-muted-foreground font-mono text-[10px]">
                        {medal ?? <span className="text-muted-foreground/50">{i + 1}</span>}
                      </td>
                      <td className="py-2 px-2 font-medium max-w-[180px] xl:max-w-[240px]">
                        <span className="block truncate group-hover:text-primary transition-colors" title={p.product}>
                          {p.product}
                        </span>
                      </td>
                      <td className="py-2 px-2 hidden sm:table-cell">
                        <div className="h-1.5 w-full rounded-full bg-white/10 overflow-hidden">
                          <div
                            className="h-full rounded-full bg-gradient-to-r from-primary to-chart-2 transition-all duration-500"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </td>
                      <td className="py-2 px-2 text-right font-semibold text-primary tabular-nums">
                        {currency(p.revenue)}
                      </td>
                      <td className="py-2 px-2 text-right text-muted-foreground tabular-nums hidden md:table-cell">
                        {number(p.units)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Category Treemap */}
        <div className="glass rounded-2xl p-5 xl:col-span-2 flex flex-col">
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded-lg bg-chart-2/10 text-chart-2"><Layers className="h-4 w-4" /></div>
            <h3 className="text-sm font-semibold">Category Performance</h3>
          </div>
          <p className="text-xs text-muted-foreground mb-4 pl-8">Block area = total revenue share</p>
          <div className="flex-1 min-h-[460px]">
            <ResponsiveContainer width="100%" height="100%">
              {treemapData.length > 0 ? (
                <Treemap
                  data={treemapData}
                  dataKey="value"
                  nameKey="name"
                  content={<TreemapBlock />}
                  isAnimationActive={false}
                />
              ) : (
                <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                  No category data available
                </div>
              )}
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* ── Row 2: Brand performance bar chart ── */}
      <div className="glass rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-1">
          <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400"><Tag className="h-4 w-4" /></div>
          <h3 className="text-sm font-semibold">Top 15 Brand Performance</h3>
        </div>
        <p className="text-xs text-muted-foreground mb-4 pl-8">Revenue vs units sold per brand</p>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={brands} margin={{ top: 8, right: 32, left: 8, bottom: 60 }}>
              <CartesianGrid vertical={false} stroke="var(--color-border)" strokeDasharray="3 3" />
              <XAxis
                dataKey="brand"
                tick={{ fill: "var(--color-muted-foreground)", fontSize: 9 }}
                tickLine={false} axisLine={false}
                angle={-35} textAnchor="end" interval={0}
              />
              <YAxis
                yAxisId="rev"
                tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }}
                tickLine={false} axisLine={false}
                tickFormatter={(v) => `$${Math.round(v / 1000)}k`}
              />
              <YAxis
                yAxisId="units" orientation="right"
                tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }}
                tickLine={false} axisLine={false}
              />
              <Tooltip content={<TooltipBox />} />
              <Legend
                wrapperStyle={{ fontSize: 11, color: "var(--color-muted-foreground)", paddingTop: 8 }}
                formatter={(value) => <span style={{ color: "var(--color-muted-foreground)" }}>{value}</span>}
              />
              <Bar yAxisId="rev" dataKey="revenue" name="Revenue" radius={[6, 6, 0, 0]} maxBarSize={30} isAnimationActive={false}>
                {brands.map((_, i) => (
                  <Cell key={i} fill={BRAND_COLORS[i % BRAND_COLORS.length]} fillOpacity={0.88} />
                ))}
              </Bar>
              <Bar
                yAxisId="units" dataKey="units" name="Units Sold"
                fill="#22d3ee" fillOpacity={0.35} radius={[4, 4, 0, 0]}
                maxBarSize={14} isAnimationActive={false}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
}
