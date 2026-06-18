import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Brain, DollarSign, Activity, AlertCircle, TrendingDown, Users } from "lucide-react";
import { api, type CustomerRFM } from "@/lib/api";
import { KpiCard } from "@/components/dashboard/kpi-card";


import { useDashboard } from "@/lib/dashboard-context";

export function AiClvTab() {
  const { range, segments: selectedSegKeys } = useDashboard();
  const [rfm, setRfm] = useState<CustomerRFM>({
    recency: 30,
    frequency: 5,
    monetary: 500,
  });

  const driftQ = useQuery({ queryKey: ["drift"], queryFn: () => api.drift() });
  const insightsQ = useQuery({ queryKey: ["insights", range, selectedSegKeys], queryFn: () => api.kpis(range, selectedSegKeys) });

  const churnRate = insightsQ.data?.churn_rate_pct;
  const totalCustomers = insightsQ.data?.total_customers;

  const predictM = useMutation({
    mutationFn: (data: CustomerRFM) => api.predictCLV(data),
  });

  const handlePredict = (e: React.FormEvent) => {
    e.preventDefault();
    predictM.mutate(rfm);
  };

  const currency = (n: number) =>
    new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: 2,
    }).format(n);

  return (
    <div className="space-y-6">
      {/* Global KPIs from insights */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          label="Churn Rate"
          value={churnRate != null ? `${churnRate.toFixed(1)}%` : "—"}
          icon={<TrendingDown className="h-5 w-5" />}
          loading={insightsQ.isLoading}
        />
        <KpiCard
          label="Total Customers"
          value={totalCustomers != null ? totalCustomers.toLocaleString() : "—"}
          icon={<Users className="h-5 w-5" />}
          loading={insightsQ.isLoading}
        />
        <KpiCard
          label="Model Status"
          value={driftQ.data?.retrain_signal_active ? "⚠️ Retrain" : "✅ Healthy"}
          icon={<Brain className="h-5 w-5" />}
          loading={driftQ.isLoading}
        />
        <KpiCard
          label="Baseline Status"
          value={driftQ.data?.baseline_exists ? "✅ Baseline Set" : "⚠️ No Baseline"}
          icon={<Activity className="h-5 w-5" />}
          loading={driftQ.isLoading}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* CLV Prediction Form */}
        <div className="glass rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-primary/10 rounded-lg text-primary">
              <DollarSign className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">CLV Predictor</h3>
              <p className="text-xs text-muted-foreground">BG/NBD & Gamma-Gamma Model</p>
            </div>
          </div>
          
          <form onSubmit={handlePredict} className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <label className="text-xs font-medium text-foreground">Recency</label>
                <input
                  type="number"
                  required
                  min={0}
                  value={rfm.recency}
                  onChange={(e) => setRfm({ ...rfm, recency: Number(e.target.value) })}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium text-foreground">Frequency</label>
                <input
                  type="number"
                  required
                  min={1}
                  value={rfm.frequency}
                  onChange={(e) => setRfm({ ...rfm, frequency: Number(e.target.value) })}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
              <div className="space-y-2">
                <label className="text-xs font-medium text-foreground">Monetary</label>
                <input
                  type="number"
                  required
                  min={1}
                  value={rfm.monetary}
                  onChange={(e) => setRfm({ ...rfm, monetary: Number(e.target.value) })}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={predictM.isPending}
              className="w-full bg-primary text-primary-foreground font-medium py-2 px-4 rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              {predictM.isPending ? "Calculating..." : "Calculate Lifetime Value"}
            </button>
          </form>

          {predictM.data && (
            <div className="mt-6 p-4 border border-primary/20 bg-primary/5 rounded-xl space-y-4 animate-in fade-in">
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Predicted 30-Day Purchases:</span>
                <span className="font-semibold">{predictM.data.predicted_purchases.toFixed(2)} orders</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-muted-foreground">Expected AOV:</span>
                <span className="font-semibold">{currency(predictM.data.expected_revenue)}</span>
              </div>
              <div className="pt-4 border-t border-primary/10 flex justify-between items-center">
                <span className="text-sm font-semibold">Total Predicted CLV:</span>
                <span className="text-xl font-bold text-primary">{currency(predictM.data.clv)}</span>
              </div>
            </div>
          )}
          {predictM.isError && (
            <div className="mt-6 p-4 border border-red-500/20 bg-red-500/10 rounded-xl text-red-500 text-sm text-center">
              Failed to predict CLV. Ensure models are trained.
            </div>
          )}
        </div>

        {/* System Health & Drift */}
        <div className="glass rounded-2xl p-6">
          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 bg-amber-500/10 rounded-lg text-amber-500">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-semibold">ML System Health</h3>
              <p className="text-xs text-muted-foreground">Data Drift & Model Monitoring</p>
            </div>
          </div>

          {driftQ.isLoading ? (
            <div className="h-40 grid place-items-center text-muted-foreground">Loading...</div>
          ) : driftQ.isError || !driftQ.data ? (
            <div className="h-40 grid place-items-center text-red-500">Failed to load drift status</div>
          ) : (
            <div className="space-y-4">
              <div className={`p-4 rounded-xl border flex items-start gap-3 ${driftQ.data?.retrain_signal_active ? 'bg-red-500/10 border-red-500/20 text-red-500' : 'bg-green-500/10 border-green-500/20 text-green-500'}`}>
                {driftQ.data?.retrain_signal_active ? <AlertCircle className="w-5 h-5 mt-0.5" /> : <Activity className="w-5 h-5 mt-0.5" />}
                <div>
                  <h4 className="font-semibold text-sm">
                    {driftQ.data?.retrain_signal_active ? "Data Drift Detected" : "System Healthy"}
                  </h4>
                  <p className="text-xs opacity-80 mt-1">
                    {driftQ.data?.retrain_signal_active
                      ? "A significant change in data distribution has been detected. Models should be retrained."
                      : "No significant data drift detected. Models are operating within expected parameters."}
                  </p>
                </div>
              </div>

              <div className="bg-background/50 rounded-xl p-4 border border-border/50 text-sm">
                <div className="flex justify-between py-2 border-b border-border/50">
                  <span className="text-muted-foreground">Baseline Set:</span>
                  <span className="font-medium">True</span>
                </div>
                <div className="flex justify-between py-2">
                  <span className="text-muted-foreground">Last Checked:</span>
                  <span className="font-medium">
                    {driftQ.data?.checked_at ? new Date(driftQ.data.checked_at).toLocaleString() : "Never"}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

      </div>

      {/* RAG AI Info Panel */}
      <div className="glass rounded-2xl p-8 bg-gradient-to-r from-primary/5 to-transparent border-primary/20 flex flex-col md:flex-row items-center gap-8">
        <div className="flex-1">
          <h2 className="text-2xl font-bold flex items-center gap-2 mb-2">
            <Brain className="w-6 h-6 text-primary" />
            AI Insight Analyst
          </h2>
          <p className="text-muted-foreground text-sm max-w-2xl">
            Your Customer Intelligence System is equipped with a Llama 3 powered Text-to-SQL RAG agent. 
            It can instantly answer complex business questions by querying the data warehouse securely.
            Click the floating chat button in the bottom right to start exploring your data.
          </p>
        </div>
      </div>
    </div>
  );
}

