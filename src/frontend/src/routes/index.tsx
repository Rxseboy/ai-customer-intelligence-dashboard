import { useState } from "react";
import { createFileRoute } from "@tanstack/react-router";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { DashboardProvider } from "@/lib/dashboard-context";
import { DashboardHeader } from "@/components/dashboard/header";
import { ChatFab } from "@/components/dashboard/chat-fab";
import { RevenueOverviewTab } from "@/components/dashboard/tabs/revenue-overview";
import { CustomerRFMTab } from "@/components/dashboard/tabs/customer-rfm";
import { ProductAnalyticsTab } from "@/components/dashboard/tabs/product-analytics";
import { RecommendationTab } from "@/components/dashboard/tabs/recommendation-tab";
import { AiClvTab } from "@/components/dashboard/tabs/ai-clv-tab";
import { AIAnalystTab } from "@/components/dashboard/tabs/ai-analyst";
import { ChurnTab } from "@/components/dashboard/tabs/churn-tab";
import { BarChart3, Brain, Package, Users, Bot, Activity } from "lucide-react";
import { useTranslation } from "react-i18next";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Customer Intelligence Dashboard" },
      {
        name: "description",
        content:
          "Premium e-commerce customer intelligence dashboard — revenue analytics, RFM segmentation, product performance, and AI-powered insights.",
      },
      { property: "og:title", content: "Customer Intelligence Dashboard" },
      {
        property: "og:description",
        content:
          "Premium e-commerce customer intelligence dashboard — revenue analytics, RFM segmentation, product performance, and AI-powered insights.",
      },
    ],
  }),
  component: DashboardPage,
});

const TABS = [
  { value: "revenue",  label: "Revenue",         labelKey: "dashboard.revenue_overview",  icon: BarChart3 },
  { value: "rfm",      label: "Customer RFM",     labelKey: "dashboard.customer_rfm",      icon: Users },
  { value: "products", label: "Products",         labelKey: "dashboard.product_analytics", icon: Package },
  { value: "churn",    label: "Churn Analytics",  labelKey: "dashboard.churn",             icon: Activity },
  { value: "clv",      label: "Analytics & AI",   labelKey: "dashboard.clv",               icon: Brain },
  { value: "ai",       label: "AI Analyst",       labelKey: "dashboard.ai_analyst",        icon: Bot },
] as const;

type TabValue = typeof TABS[number]["value"];

function DashboardPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabValue>("revenue");

  return (
    <DashboardProvider>
      <div className="min-h-screen">
        <DashboardHeader />
        <main className="mx-auto max-w-[1500px] px-6 py-6">
          <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as TabValue)} className="w-full">
            <TabsList className="glass mb-6 inline-flex h-auto flex-wrap gap-1 p-1">
              {TABS.map(({ value, label, labelKey, icon: Icon }) => (
                <TabsTrigger key={value} value={value} className="gap-2 px-4 py-2 text-sm">
                  <Icon className="h-4 w-4" />
                  {t(labelKey, label)}
                </TabsTrigger>
              ))}
            </TabsList>

            <ErrorBoundary>
              <TabsContent value="revenue">
                {activeTab === "revenue" && <RevenueOverviewTab />}
              </TabsContent>

              <TabsContent value="rfm">
                {activeTab === "rfm" && <CustomerRFMTab />}
              </TabsContent>

              <TabsContent value="products">
                {activeTab === "products" && (
                  <div className="space-y-10 animate-in fade-in duration-300">
                    <ProductAnalyticsTab />
                    <div className="border-t border-border/50 my-8" />
                    <RecommendationTab />
                  </div>
                )}
              </TabsContent>

              <TabsContent value="churn">
                {activeTab === "churn" && <ChurnTab />}
              </TabsContent>

              <TabsContent value="clv">
                {activeTab === "clv" && <AiClvTab />}
              </TabsContent>

              <TabsContent value="ai">
                {activeTab === "ai" && <AIAnalystTab />}
              </TabsContent>
            </ErrorBoundary>
          </Tabs>
        </main>
        {activeTab !== "ai" && <ChatFab />}
      </div>
    </DashboardProvider>
  );
}
