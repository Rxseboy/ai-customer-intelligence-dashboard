import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Sparkles, ShoppingBag } from "lucide-react";
import { api } from "@/lib/api";

export function RecommendationTab() {
  const [searchInput, setSearchInput] = useState("1");
  const [customerId, setCustomerId] = useState<number | null>(null);

  const recsQ = useQuery({
    queryKey: ["recommendations", customerId],
    queryFn: () => api.recommendations(customerId as number, 6),
    enabled: customerId !== null,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const id = parseInt(searchInput, 10);
    if (!isNaN(id)) {
      setCustomerId(id);
    }
  };

  const data = recsQ.data as any;
  const products = data?.products || [];

  return (
    <div className="space-y-6">
      <div className="glass rounded-2xl p-6 mb-6 bg-gradient-to-br from-background to-primary/5 border-primary/20">
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              ALS Recommendation Engine
            </h2>
            <p className="text-sm text-muted-foreground mt-1 max-w-xl">
              Our Implicit Alternating Least Squares (ALS) collaborative filtering model analyzes historical purchase patterns to suggest highly relevant products.
            </p>
          </div>
          <form onSubmit={handleSearch} className="flex items-center gap-2 w-full md:w-auto">
            <div className="relative flex-1 md:w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <input
                type="number"
                min={1}
                required
                placeholder="Customer ID..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                className="w-full bg-background border border-border rounded-full pl-9 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
              />
            </div>
            <button
              type="submit"
              className="bg-primary text-primary-foreground font-medium py-2 px-4 rounded-full hover:bg-primary/90 transition-colors text-sm whitespace-nowrap"
            >
              Generate
            </button>
          </form>
        </div>
      </div>

      {customerId === null ? (
        <div className="glass rounded-2xl min-h-[300px] flex flex-col items-center justify-center text-muted-foreground p-8">
          <Sparkles className="w-12 h-12 opacity-20 mb-4" />
          <p>Enter a Customer ID above to generate personalized recommendations.</p>
        </div>
      ) : recsQ.isLoading ? (
        <div className="glass rounded-2xl min-h-[300px] flex flex-col items-center justify-center text-muted-foreground p-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mb-4"></div>
          <p>Running ML inference for Customer #{customerId}...</p>
        </div>
      ) : recsQ.isError ? (
        <div className="glass rounded-2xl min-h-[300px] flex flex-col items-center justify-center text-red-500 p-8">
          <p>Failed to generate recommendations. Ensure the ML model is trained and backend is running.</p>
        </div>
      ) : products.length === 0 ? (
        <div className="glass rounded-2xl min-h-[300px] flex flex-col items-center justify-center text-muted-foreground p-8">
          <p>No recommendations found for Customer #{customerId}.</p>
        </div>
      ) : (
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            Top {products.length} Recommended Products for Customer #{customerId}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {products.map((product: any, idx: number) => (
              <div key={idx} className="glass rounded-xl p-5 hover:bg-white/5 transition-colors border border-border/50 hover:border-primary/30">
                <div className="flex items-start justify-between mb-4">
                  <div className="p-2 bg-primary/10 rounded-lg text-primary">
                    <ShoppingBag className="w-5 h-5" />
                  </div>
                  <span className="text-xs font-mono text-muted-foreground bg-background px-2 py-1 rounded">
                    ID: {product.product_id}
                  </span>
                </div>
                <h4 className="font-semibold text-base line-clamp-2" title={product.name}>
                  {product.name}
                </h4>
                <p className="text-xs text-muted-foreground mt-2 inline-flex items-center px-2 py-1 bg-secondary rounded-full">
                  {product.category}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
