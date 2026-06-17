import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, ResponsiveContainer,
  Tooltip, Treemap, XAxis, YAxis,
} from "recharts";
import { api } from "@/lib/api";
import { useDashboard } from "@/lib/dashboard-context";

const currency = (n: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);
const number = (n: number) => new Intl.NumberFormat("en-US").format(n);

const BRAND_COLORS = [
  "var(--color-chart-1)", "var(--color-chart-2)", "var(--color-chart-3)",
  "var(--color-chart-4)", "var(--color-chart-5)",
];

function TooltipBox({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="glass rounded-lg px-3 py-2 text-xs">
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

// Custom treemap content block with gradient intensity
function TreemapBlock(props: any) {
  const { x, y, width, height, name, value } = props;
  if (width < 30 || height < 20) return null;
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} style={{ fill: "var(--color-chart-1)", fillOpacity: 0.6, stroke: "var(--color-border)", strokeWidth: 2 }} />
      {width > 60 && height > 30 && (
        <>
          <text x={x + width / 2} y={y + height / 2 - 6} textAnchor="middle" fill="var(--color-foreground)" fontSize={11} fontWeight={600}>
            {name}
          </text>
          <text x={x + width / 2} y={y + height / 2 + 10} textAnchor="middle" fill="var(--color-muted-foreground)" fontSize={10}>
            {currency(value)}
          </text>
        </>
      )}
    </g>
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

  const products = productsQ.data ?? [];
  const categories = categoriesQ.data ?? [];
  const { brands, treemapData, topProducts } = useMemo(() => {
    // Aggregate brands from products
    const brandMap = products.reduce<Record<string, { revenue: number; units: number }>>((acc, p) => {
      const brand = String(p.brand ?? "Unknown");
      if (!acc[brand]) acc[brand] = { revenue: 0, units: 0 };
      acc[brand].revenue += Number(p.revenue ?? 0);
      acc[brand].units += Number(p.units ?? 0);
      return acc;
    }, {});
    const brands = Object.entries(brandMap)
      .map(([brand, v]) => ({ brand, ...v }))
      .sort((a, b) => b.revenue - a.revenue)
      .slice(0, 15);

    // Treemap data from categories (limit to top 30 to prevent freezing)
    const treemapData = categories.slice(0, 30).map((c) => ({
      name: String(c.category),
      size: Number(c.revenue ?? 0),
      value: Number(c.revenue ?? 0),
    }));

    // Top products
    const topProducts = products.slice(0, 25).map((p) => ({
      product: String(p.product ?? p.name ?? "Unknown").slice(0, 30),
      revenue: Number(p.revenue ?? 0),
      units: Number(p.units ?? 0),
    }));

    return { brands, treemapData, topProducts };
  }, [products, categories]);

  const isLoading = productsQ.isLoading || categoriesQ.isLoading;
  const isError = productsQ.isError || categoriesQ.isError;

  if (isLoading) {
    return <div className="grid min-h-[300px] place-items-center text-sm text-muted-foreground">Loading product data…</div>;
  }
  if (isError) {
    return <div className="grid min-h-[300px] place-items-center text-sm text-destructive">Failed to load products. Check API connection.</div>;
  }

  return (
    <div className="space-y-6">
      {/* Top products + Category treemap */}
      <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
        {/* Top 25 Products Bar chart */}
        <div className="glass rounded-2xl p-5 xl:col-span-2">
          <h3 className="text-sm font-semibold">Top 25 Products by Revenue</h3>
          <p className="text-xs text-muted-foreground">Sorted by total revenue in selected period</p>
          <div className="mt-4 h-[500px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={topProducts}
                layout="vertical"
                margin={{ left: 16, right: 40 }}
              >
                <CartesianGrid horizontal={false} stroke="var(--color-border)" strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${Math.round(v / 1000)}k`} />
                <YAxis dataKey="product" type="category" tick={{ fill: "var(--color-muted-foreground)", fontSize: 9 }} tickLine={false} axisLine={false} width={140} />
                <Tooltip content={<TooltipBox />} />
                <Bar dataKey="revenue" name="Revenue" fill="var(--color-chart-1)" fillOpacity={0.85} radius={[0, 6, 6, 0]} maxBarSize={20} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Category Treemap */}
        <div className="glass rounded-2xl p-5">
          <h3 className="text-sm font-semibold">Category Performance</h3>
          <p className="text-xs text-muted-foreground">Block size = total revenue</p>
          <div className="mt-4 h-[500px]">
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
                <div className="flex h-full items-center justify-center text-xs text-muted-foreground">No category data available</div>
              )}
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Brand performance */}
      <div className="glass rounded-2xl p-5">
        <h3 className="text-sm font-semibold">Top 15 Brand Performance</h3>
        <p className="text-xs text-muted-foreground">Revenue vs units sold per brand</p>
        <div className="mt-4 h-[320px]">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={brands} margin={{ top: 8, right: 24, left: 8, bottom: 40 }}>
              <CartesianGrid vertical={false} stroke="var(--color-border)" strokeDasharray="3 3" />
              <XAxis dataKey="brand" tick={{ fill: "var(--color-muted-foreground)", fontSize: 10 }} tickLine={false} axisLine={false} angle={-30} textAnchor="end" interval={0} />
              <YAxis yAxisId="rev" tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => `$${Math.round(v / 1000)}k`} />
              <YAxis yAxisId="units" orientation="right" tick={{ fill: "var(--color-muted-foreground)", fontSize: 11 }} tickLine={false} axisLine={false} />
              <Tooltip content={<TooltipBox />} />
              <Legend wrapperStyle={{ fontSize: 11, color: "var(--color-muted-foreground)" }} />
              <Bar yAxisId="rev" dataKey="revenue" name="Revenue" radius={[6, 6, 0, 0]} maxBarSize={28} isAnimationActive={false}>
                {brands.map((_, i) => (
                  <Cell key={i} fill={BRAND_COLORS[i % BRAND_COLORS.length]} fillOpacity={0.85} />
                ))}
              </Bar>
              <Bar yAxisId="units" dataKey="units" name="Units Sold" fill="var(--color-chart-4)" fillOpacity={0.5} radius={[6, 6, 0, 0]} maxBarSize={14} isAnimationActive={false} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
