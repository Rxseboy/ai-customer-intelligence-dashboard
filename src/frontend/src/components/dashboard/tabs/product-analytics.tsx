import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar, BarChart, CartesianGrid, Cell,
  ResponsiveContainer, Tooltip, XAxis, YAxis, Legend,
} from "recharts";
import { Package, Tag, Layers } from "lucide-react";
import { api } from "@/lib/api";
import { useDashboard } from "@/lib/dashboard-context";

const currency = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
const number = (n: number) => new Intl.NumberFormat("en-US").format(n);

const BRAND_COLORS = [
  "#6366f1","#22d3ee","#f59e0b","#10b981","#f43f5e",
  "#8b5cf6","#14b8a6","#fb923c","#a3e635","#e879f9",
  "#38bdf8","#fbbf24","#34d399","#f87171","#818cf8",
];

const CATEGORY_COLORS = [
  "#6366f1","#8b5cf6","#a855f7","#ec4899","#f43f5e",
  "#f59e0b","#10b981","#14b8a6","#22d3ee","#38bdf8",
  "#fb923c","#84cc16","#06b6d4","#e11d48","#7c3aed",
];

function TooltipBox({ active, payload }: any) {
  if (!active || !Array.isArray(payload) || payload.length === 0) return null;
  return (
    <div className="glass rounded-lg px-3 py-2 text-xs shadow-xl">
      {payload.map((p: any, i: number) => (
        <div key={i} className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full" style={{ backgroundColor: p.color }} />
          <span className="text-muted-foreground">{p.name}:</span>
          <span className="font-semibold">
            {p.name === "Revenue" || p.dataKey === "revenue"
              ? currency(p.value)
              : number(p.value)}
          </span>
        </div>
      ))}
    </div>
  );
}

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

  // Always coerce to array — never trust cache type
  const products   = Array.isArray(productsQ.data)   ? productsQ.data   : [];
  const categories = Array.isArray(categoriesQ.data) ? categoriesQ.data : [];

  const { brands, categoryBars, topProducts, maxRevenue } = useMemo(() => {
    // ── Brand aggregation ──
    const brandMap: Record<string, { revenue: number; units: number }> = {};
    for (const p of products) {
      const brand = String(p.brand ?? "Unknown");
      if (!brandMap[brand]) brandMap[brand] = { revenue: 0, units: 0 };
      brandMap[brand].revenue += Number(p.revenue ?? 0);
      brandMap[brand].units   += Number(p.units   ?? 0);
    }
    const brands = Object.entries(brandMap)
      .map(([brand, v]) => ({ brand, ...v }))
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 15);

    // ── Category bars (replaces Treemap — 100% crash-free) ──
    const categoryBars = categories
      .filter((c) => Number(c.revenue ?? 0) > 0)
      .slice(0, 20)
      .map((c) => ({
        category: String(c.category ?? "Unknown"),
        revenue:  Number(c.revenue ?? 0),
        orders:   Number(c.orders  ?? 0),
      }))
      .sort((a, b) => b.revenue - a.revenue);

    // ── Top products table ──
    const topProducts = products.slice(0, 25).map((p) => ({
      product: String(p.product ?? (p as any).name ?? "Unknown"),
      revenue: Number(p.revenue ?? 0),
      units:   Number(p.units   ?? 0),
    }));

    const maxRevenue = topProducts.length > 0 ? Math.max(1, topProducts[0].revenue) : 1;

    return { brands, categoryBars, topProducts, maxRevenue };
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

      {/* ── Row 1: Products table + Category horizontal bars ── */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-5">

        {/* Top 25 Products table with inline bar */}
        <div className="glass rounded-2xl p-5 xl:col-span-3 flex flex-col">
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded-lg bg-primary/10 text-primary">
              <Package className="h-4 w-4" />
            </div>
            <h3 className="text-sm font-semibold">Top 25 Products by Revenue</h3>
          </div>
          <p className="text-xs text-muted-foreground mb-4 pl-8">Sorted by total revenue · hover for full name</p>

          {topProducts.length === 0 ? (
            <div className="flex-1 grid place-items-center text-xs text-muted-foreground">
              No product data available for selected period
            </div>
          ) : (
            <div className="overflow-auto flex-1">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-border/60">
                    <th className="text-left py-2 px-1 text-muted-foreground font-medium w-7">#</th>
                    <th className="text-left py-2 px-2 text-muted-foreground font-medium">Product</th>
                    <th className="text-left py-2 px-2 text-muted-foreground font-medium w-32 hidden sm:table-cell">Share</th>
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
                        <td className="py-2 px-1 text-[10px] font-mono">
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
          )}
        </div>

        {/* Category Performance — CSS horizontal bars (replaces crashed Treemap) */}
        <div className="glass rounded-2xl p-5 xl:col-span-2 flex flex-col">
          <div className="flex items-center gap-2 mb-1">
            <div className="p-1.5 rounded-lg bg-violet-500/10 text-violet-400">
              <Layers className="h-4 w-4" />
            </div>
            <h3 className="text-sm font-semibold">Category Performance</h3>
          </div>
          <p className="text-xs text-muted-foreground mb-4 pl-8">Ranked by total revenue</p>

          {categoryBars.length === 0 ? (
            <div className="flex-1 grid place-items-center text-xs text-muted-foreground">
              No category data available
            </div>
          ) : (
            <div className="flex-1 overflow-auto space-y-2.5">
              {(() => {
                const maxCatRev = Math.max(1, categoryBars[0]?.revenue ?? 1);
                return categoryBars.map((c, i) => (
                  <div key={i} className="group">
                    <div className="flex items-center justify-between mb-1">
                      <span
                        className="text-xs font-medium truncate max-w-[160px]"
                        title={c.category}
                        style={{ color: CATEGORY_COLORS[i % CATEGORY_COLORS.length] }}
                      >
                        {c.category}
                      </span>
                      <span className="text-xs tabular-nums text-muted-foreground ml-2 shrink-0">
                        {currency(c.revenue)}
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-white/8 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-700"
                        style={{
                          width: `${(c.revenue / maxCatRev) * 100}%`,
                          backgroundColor: CATEGORY_COLORS[i % CATEGORY_COLORS.length],
                          opacity: 0.85,
                        }}
                      />
                    </div>
                  </div>
                ));
              })()}
            </div>
          )}
        </div>
      </div>

      {/* ── Row 2: Brand performance BarChart ── */}
      <div className="glass rounded-2xl p-5">
        <div className="flex items-center gap-2 mb-1">
          <div className="p-1.5 rounded-lg bg-amber-500/10 text-amber-400">
            <Tag className="h-4 w-4" />
          </div>
          <h3 className="text-sm font-semibold">Top 15 Brand Performance</h3>
        </div>
        <p className="text-xs text-muted-foreground mb-4 pl-8">Revenue vs units sold per brand</p>

        {brands.length === 0 ? (
          <div className="h-[300px] grid place-items-center text-xs text-muted-foreground">
            No brand data available for selected period
          </div>
        ) : (
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
                  wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
                  formatter={(v) => <span style={{ color: "var(--color-muted-foreground)" }}>{v}</span>}
                />
                <Bar yAxisId="rev" dataKey="revenue" name="Revenue"
                  radius={[6, 6, 0, 0]} maxBarSize={30} isAnimationActive={false}>
                  {brands.map((_, i) => (
                    <Cell key={i} fill={BRAND_COLORS[i % BRAND_COLORS.length]} fillOpacity={0.88} />
                  ))}
                </Bar>
                <Bar yAxisId="units" dataKey="units" name="Units Sold"
                  fill="#22d3ee" fillOpacity={0.35}
                  radius={[4, 4, 0, 0]} maxBarSize={14} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

    </div>
  );
}
