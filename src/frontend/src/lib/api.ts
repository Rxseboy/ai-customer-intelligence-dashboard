// API client for Customer Intelligence System
// Configure backend URL via VITE_API_BASE_URL (defaults to http://localhost:8000)

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "http://localhost:8000";

// ---------- Types ----------
export interface CustomerRFM {
  recency: number;
  frequency: number;
  monetary: number;
  avg_order_value?: number | null;
}

export interface ChurnResponse {
  churn_probability: number;
  risk_level: string;
  prediction: string;
  recency_days: number;
  message: string;
}

export interface CLVResponse {
  customer_id: number;
  predicted_purchases: number;
  expected_revenue: number;
  clv: number;
  generated_at?: string;
}

export interface SegmentResponse {
  segment: string;
  rfm_score: number;
  r_score: number;
  f_score: number;
  m_score: number;
  action: string;
}

export interface InsightResponse {
  total_customers: number;
  total_revenue: number;
  avg_monetary: number;
  avg_recency_days: number;
  churn_rate_pct: number;
  pareto_top20_pct: number;
  generated_at?: string;
}

export interface DriftStatusResponse {
  retrain_signal_active: boolean;
  last_drift_log?: Record<string, unknown> | null;
  baseline_exists: boolean;
  checked_at: string;
}

export interface RAGQueryRequest {
  question: string;
  language?: "id" | "en" | null;
  d_from?: string;
  d_to?: string;
  granularity?: string;
  segments?: string[];
}

export interface RAGQueryResponse {
  answer: string;
  sql?: string | null;
  cached?: boolean;
  error?: string | null;
  generated_at?: string;
}

export interface HealthResponse {
  status: string;
  model_ready: boolean;
  data_ready: boolean;
  mlflow_ready: boolean;
  timestamp: string;
  cache_stats?: Record<string, unknown> | null;
}

export type DateRange = {
  d_from: string; // ISO date YYYY-MM-DD
  d_to: string;
};

export type Granularity = "monthly" | "weekly" | "daily";

// Loose response types for insight endpoints (backend returns flexible shapes)
export type KpisResponse = {
  revenue?: number;
  orders?: number;
  aov?: number;
  customers?: number;
  [k: string]: unknown;
};

export type TrendPoint = {
  period: string;
  revenue: number;
  orders: number;
  [k: string]: unknown;
};

export type StatusBreakdown = { status: string; count: number; revenue?: number };

export type ProductRow = {
  product_id?: string | number;
  product_name?: string;
  name?: string;
  revenue: number;
  units?: number;
  brand?: string;
  [k: string]: unknown;
};

export type CategoryRow = {
  category: string;
  revenue: number;
  avg_price?: number;
  units?: number;
  [k: string]: unknown;
};

export type RFMRow = {
  customer_id: number | string;
  recency: number;
  frequency: number;
  monetary: number;
  segment: string;
  [k: string]: unknown;
};

export type DateBounds = { min_date: string; max_date: string };

// ---------- Core fetcher ----------
class ApiError extends Error {
  status: number;
  payload: unknown;
  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

async function request<T>(
  path: string,
  init?: Omit<RequestInit, "body"> & {
    body?: BodyInit | null;
    query?: Record<string, unknown>;
    timeout?: number;
  },
): Promise<T> {
  const { query, timeout = 25000, ...rest } = init ?? {};
  const url = new URL(
    path.replace(/^\//, ""),
    API_BASE_URL.endsWith("/") ? API_BASE_URL : `${API_BASE_URL}/`,
  );
  if (query) {
    Object.entries(query).forEach(([k, v]) => {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v));
    });
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const res = await fetch(url.toString(), {
      ...rest,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
        "X-API-Key": (import.meta.env.VITE_API_KEY as string | undefined) ?? "your-secure-api-key-here",
        ...(rest.headers ?? {}),
      },
    });
    
    clearTimeout(timeoutId);
    const text = await res.text();
    const payload = text ? safeJson(text) : null;
    
    if (!res.ok) {
      throw new ApiError(
        typeof payload === "object" && payload && "detail" in payload
          ? String((payload as { detail: unknown }).detail)
          : `Request failed: ${res.status}`,
        res.status,
        payload,
      );
    }
    return payload as T;
  } catch (err) {
    clearTimeout(timeoutId);
    if (err instanceof Error && err.name === "AbortError") {
      throw new ApiError("Request timed out after 25 seconds. The server might be busy or unavailable.", 408, null);
    }
    throw err;
  }
}

function safeJson(s: string): unknown {
  try {
    return JSON.parse(s);
  } catch {
    return s;
  }
}

// ---------- Endpoints ----------
export const api = {
  health: () => request<HealthResponse>("/health"),

  // Predictions
  predictChurn: (body: CustomerRFM) =>
    request<ChurnResponse>("/predict/churn", { method: "POST", body: JSON.stringify(body) }),
  predictSegment: (body: CustomerRFM) =>
    request<SegmentResponse>("/predict/segment", { method: "POST", body: JSON.stringify(body) }),
  predictCLV: (body: CustomerRFM, customer_id?: number) =>
    request<CLVResponse>("/predict/clv", {
      method: "POST",
      body: JSON.stringify(body),
      query: { customer_id },
    }),
  recommendations: (customer_id: number, limit?: number) =>
    request<unknown>("/predict/recommendations", { query: { customer_id, limit } }),

  // Customers
  topCustomers: (limit?: number) => request<{customers: RFMRow[]}>("/customers/top", { query: { limit } }).then(r => r.customers),

  // Insights
  insights: (r?: DateRange, segments?: string[]) => request<InsightResponse>("/insights", { query: { ...r, segments: segments?.join(",") } }),
  segmentsSummary: () => request<{segments: unknown[]}>("/segments/summary").then(r => r.segments),
  dateBounds: () => request<DateBounds>("/api/insights/date-bounds"),
  kpis: (r: DateRange, segments?: string[]) => request<KpisResponse>("/api/insights/kpis", { query: { ...r, segments: segments?.join(",") } }),
  trend: (r: DateRange, granularity: Granularity = "monthly", segments?: string[]) =>
    request<{trend: TrendPoint[]}>("/api/insights/trend", { query: { ...r, granularity, segments: segments?.join(",") } }).then(r => r.trend),
  status: (r: DateRange, segments?: string[]) => request<{status_breakdown: StatusBreakdown[]}>("/api/insights/status", { query: { ...r, segments: segments?.join(",") } }).then(r => r.status_breakdown),
  products: (r: DateRange, limit = 20, segments?: string[]) =>
    request<{products: ProductRow[]}>("/api/insights/products", { query: { ...r, limit, segments: segments?.join(",") } }).then(r => r.products),
  categories: (r: DateRange, segments?: string[]) => request<{categories: CategoryRow[]}>("/api/insights/categories", { query: { ...r, segments: segments?.join(",") } }).then(r => r.categories),
  rfm: (r: DateRange, segments?: string[]) => request<{rfm: RFMRow[]}>("/api/insights/rfm", { query: { ...r, segments: segments?.join(",") } }).then(r => r.rfm),
  segmentCategories: (r: DateRange, segments?: string[]) =>
    request<unknown>("/api/insights/segment-categories", { query: { ...r, segments: segments?.join(",") } }),

  // RAG
  ask: (body: RAGQueryRequest) =>
    request<RAGQueryResponse>("/insights/ask", { method: "POST", body: JSON.stringify(body) }),
  tables: () => request<unknown>("/insights/tables"),

  // Monitoring
  drift: () => request<DriftStatusResponse>("/monitoring/drift"),
  driftCheck: () => request<DriftStatusResponse>("/monitoring/drift/check", { method: "POST" }),
};

export { ApiError };
