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

// Custom treemap content block with high-contrast text
function TreemapBlock(props: any) {
  const { x, y, width, height, name, value } = props;
  if (width < 30 || height < 20) return null;
  return (
    <g>
      <rect x={x} y={y} width={width} height={height}
        style={{
          fill: "var(--color-chart-1)",
          fillOpacity: 0.75,
          stroke: "var(--color-background)",
          strokeWidth: 2,
        }}
      />
      {width > 60 && height > 30 && (
        <>
          <text x={x + width / 2} y={y + height / 2 - 8}
            textAnchor="middle" fill="#ffffff" fontSize={11} fontWeight={700}
            style={{ textShadow: "0 1px 3px rgba(0,0,0,0.8)" }}
          >
            {name}
          </text>
          <text x={x + width / 2} y={y + height / 2 + 10}
            textAnchor="middle" fill="#ffffff" fontSize={10} fontWeight={500}
            style={{ textShadow: "0 1px 3px rgba(0,0,0,0.8)" }}
          >
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

    // Top products — show in a horizontal table instead of chart to avoid name overlap
    const topProducts = products.slice(0, 25).map((p) => ({
      product: String(p.product ?? p.name ?? "Unknown"),
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
        {/* Top 25 Products Table */}
        <div className="glass rounded-2xl p-5 xl:col-span-2 overflow-auto">
          <h3 className="text-sm font-semibold">Top 25 Products by Revenue</h3>
          <p className="text-xs text-muted-foreground mb-4">Sorted by total revenue in selected period</p>
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 px-2 text-muted-foreground font-medium w-6">#</th>
                <th className="text-left py-2 px-2 text-muted-foreground font-medium">Product</th>
                <th className="text-right py-2 px-2 text-muted-foreground font-medium">Revenue</th>
                <th className="text-right py-2 px-2 text-muted-foreground font-medium">Units</th>
              </tr>
            </thead>
            <tbody>
              {topProducts.map((p, i) => (
                <tr key={i} className="border-b border-border/40 hover:bg-white/5 transition-colors">
                  <td className="py-2 px-2 text-muted-foreground">{i + 1}</td>
                  <td className="py-2 px-2 font-medium max-w-[280px]">
                    <span className="block truncate" title={p.product}>{p.product}</span>
                  </td>
                  <td className="py-2 px-2 text-right text-primary font-semibold">{currency(p.revenue)}</td>
                  <td className="py-2 px-2 text-right text-muted-foreground">{number(p.units)}</td>
                </tr>
              ))}
            </tbody>
          </table>
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
