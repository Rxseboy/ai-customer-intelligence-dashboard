import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { Send, Sparkles, User, Bot, RotateCcw, DollarSign, Activity } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { api, type RAGQueryResponse, type ChurnResponse, type CLVResponse } from "@/lib/api";
import { cn } from "@/lib/utils";

// ─── Sub-tab A: RAG Chat ─────────────────────────────────────────────────────

interface Message {
  role: "user" | "assistant" | "error";
  content: string;
  sql?: string | null;
  cached?: boolean;
}

const EXAMPLE_QUESTIONS = [
  "What is the total revenue last month?",
  "Who are the top 5 customers by spending?",
  "Which product category has the highest sales?",
  "How many customers are at risk of churning?",
];

import { useDashboard } from "@/lib/dashboard-context";

function RAGChat() {
  const { range, granularity, segments } = useDashboard();
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [language, setLanguage] = useState<"en" | "id">("en");
  const bottomRef = useRef<HTMLDivElement>(null);

  const ask = useMutation({
    mutationFn: (q: string) => api.ask({ question: q, language, d_from: range.d_from, d_to: range.d_to, granularity, segments }),
    onSuccess: (r: RAGQueryResponse) => {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: r.answer,
          sql: r.sql,
          cached: r.cached,
        },
      ]);
    },
    onError: () => {
      setMessages((prev) => [
        ...prev,
        { role: "error", content: "Failed to get a response. Please check your API connection and RAG configuration." },
      ]);
    },
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, ask.isPending]);

  const submit = () => {
    const q = question.trim();
    if (q.length < 3) return;
    setMessages((prev) => [...prev, { role: "user", content: q }]);
    setQuestion("");
    ask.mutate(q);
  };

  const reset = () => {
    setMessages([]);
    ask.reset();
  };

  return (
    <div className="flex h-[calc(100vh-220px)] min-h-[500px] flex-col">
      {/* Chat area */}
      <div className="glass flex-1 overflow-y-auto rounded-2xl p-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-primary to-chart-2 shadow-[var(--glow-primary)]">
              <Sparkles className="h-7 w-7 text-primary-foreground" />
            </div>
            <div>
              <h3 className="text-base font-semibold">AI Insight Assistant</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Ask anything about your data in natural language.<br />
                Powered by Llama 3.3 (Groq) + RAG over your warehouse.
              </p>
            </div>
            <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
              {EXAMPLE_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => setQuestion(q)}
                  className="glass rounded-xl px-3 py-2 text-left text-xs text-muted-foreground transition hover:border-primary/40 hover:text-foreground"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="space-y-4">
          {messages.map((msg, i) => (
            <div key={i} className={cn("flex gap-3", msg.role === "user" ? "justify-end" : "justify-start")}>
              {msg.role !== "user" && (
                <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gradient-to-br from-primary to-chart-2">
                  {msg.role === "error" ? <span className="text-xs">⚠️</span> : <Bot className="h-4 w-4 text-primary-foreground" />}
                </div>
              )}
              <div className={cn("max-w-[80%] rounded-2xl px-4 py-3 text-sm",
                msg.role === "user"
                  ? "bg-primary text-primary-foreground rounded-br-sm"
                  : msg.role === "error"
                  ? "glass border-destructive/40 bg-destructive/10 text-destructive rounded-bl-sm"
                  : "glass rounded-bl-sm"
              )}>
                <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                {msg.sql && (
                  <details className="mt-2">
                    <summary className="cursor-pointer text-xs text-muted-foreground opacity-70 hover:opacity-100">
                      View generated SQL {msg.cached && "(cached)"}
                    </summary>
                    <pre className="mt-1 overflow-x-auto rounded-lg bg-background/40 p-2 text-xs">{msg.sql}</pre>
                  </details>
                )}
              </div>
              {msg.role === "user" && (
                <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-secondary">
                  <User className="h-4 w-4 text-secondary-foreground" />
                </div>
              )}
            </div>
          ))}

          {ask.isPending && (
            <div className="flex gap-3">
              <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-gradient-to-br from-primary to-chart-2">
                <Bot className="h-4 w-4 text-primary-foreground" />
              </div>
              <div className="glass flex items-center gap-1 rounded-2xl rounded-bl-sm px-4 py-3">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.3s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary [animation-delay:-0.15s]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-primary" />
              </div>
            </div>
          )}
        </div>
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div className="mt-3 flex items-end gap-2">
        <div className="flex items-center gap-1 rounded-lg glass px-2 py-1 text-xs">
          <button onClick={() => setLanguage("en")} className={cn("rounded px-2 py-0.5", language === "en" ? "bg-primary text-primary-foreground" : "text-muted-foreground")}>EN</button>
          <button onClick={() => setLanguage("id")} className={cn("rounded px-2 py-0.5", language === "id" ? "bg-primary text-primary-foreground" : "text-muted-foreground")}>ID</button>
        </div>
        <Textarea
          id="chat-input"
          name="chat-input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          rows={2}
          placeholder="Ask anything about your data… (Enter to send)"
          className="flex-1 resize-none bg-background/40"
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
          }}
        />
        {messages.length > 0 && (
          <Button size="icon" variant="outline" className="glass border-border/60" onClick={reset} title="Clear chat">
            <RotateCcw className="h-4 w-4" />
          </Button>
        )}
        <Button size="icon" onClick={submit} disabled={ask.isPending || question.trim().length < 3} className="bg-gradient-to-br from-primary to-chart-2 shadow-[var(--glow-primary)]">
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

// ─── Sub-tab B: Predictive Engine ────────────────────────────────────────────

interface PredictForm {
  customer_id: number;
  recency: number;
  frequency: number;
  monetary: number;
  avg_order_value: number;
}

function PredictiveEngine() {
  const [form, setForm] = useState<PredictForm>({
    customer_id: 0,
    recency: 30,
    frequency: 5,
    monetary: 500,
    avg_order_value: 100,
  });
  const [churnResult, setChurnResult] = useState<ChurnResponse | null>(null);
  const [clvResult, setClvResult] = useState<CLVResponse | null>(null);

  const churnMut = useMutation({
    mutationFn: () => api.predictChurn({
      recency: form.recency,
      frequency: form.frequency,
      monetary: form.monetary,
      avg_order_value: form.avg_order_value,
    }),
    onSuccess: setChurnResult,
  });

  const clvMut = useMutation({
    mutationFn: () => api.predictCLV({
      recency: form.recency,
      frequency: form.frequency,
      monetary: form.monetary,
    }, form.customer_id),
    onSuccess: setClvResult,
  });

  const isPending = churnMut.isPending || clvMut.isPending;

  const runPrediction = () => {
    churnMut.mutate();
    clvMut.mutate();
  };

  const updateField = (key: keyof PredictForm, value: number) =>
    setForm((f) => ({ ...f, [key]: value }));

  const riskColor = churnResult
    ? churnResult.churn_probability >= 0.6 ? "text-red-400" : churnResult.churn_probability >= 0.3 ? "text-amber-400" : "text-emerald-400"
    : "";

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {/* Input form */}
      <div className="glass rounded-2xl p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-primary/10 rounded-lg text-primary">
            <Activity className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold">Customer RFM Input</h3>
            <p className="text-xs text-muted-foreground">Predict churn risk & lifetime value</p>
          </div>
        </div>
        <div className="space-y-3">
          {([
            { label: "Customer ID (optional)", key: "customer_id" as const, min: 0 },
            { label: "Recency (days since last order)", key: "recency" as const, min: 0 },
            { label: "Frequency (total orders)", key: "frequency" as const, min: 1 },
            { label: "Monetary (total spend, $)", key: "monetary" as const, min: 0 },
            { label: "Avg Order Value ($)", key: "avg_order_value" as const, min: 0 },
          ] as const).map(({ label, key, min }) => (
            <div key={key}>
              <label className="text-xs font-medium text-muted-foreground">{label}</label>
              <input
                type="number"
                min={min}
                value={form[key]}
                onChange={(e) => updateField(key, Number(e.target.value))}
                className="mt-1 w-full rounded-lg border border-border/60 bg-background/40 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-primary"
              />
            </div>
          ))}
        </div>
        <Button
          className="mt-5 w-full bg-gradient-to-br from-primary to-chart-2 shadow-[var(--glow-primary)]"
          onClick={runPrediction}
          disabled={isPending}
        >
          {isPending ? "Running predictions…" : "Run Prediction"}
        </Button>
      </div>

      {/* Results */}
      <div className="space-y-4">
        {/* Churn result */}
        <div className="glass rounded-2xl p-6">
          <h3 className="mb-3 text-sm font-semibold">Churn Prediction — XGBoost Model</h3>
          {churnMut.isError && <p className="text-sm text-destructive">Prediction failed. Check API/model status.</p>}
          {churnResult ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-muted-foreground">Risk Level</span>
                <span className={cn("text-sm font-bold", riskColor)}>{churnResult.risk_level}</span>
              </div>
              <div>
                <div className="mb-1 flex justify-between text-xs text-muted-foreground">
                  <span>Churn Probability</span>
                  <span className={cn("font-semibold", riskColor)}>{(churnResult.churn_probability * 100).toFixed(1)}%</span>
                </div>
                <div className="h-3 w-full overflow-hidden rounded-full bg-secondary">
                  <div
                    className={cn("h-full rounded-full transition-all duration-700", churnResult.churn_probability >= 0.6 ? "bg-red-400" : churnResult.churn_probability >= 0.3 ? "bg-amber-400" : "bg-emerald-400")}
                    style={{ width: `${churnResult.churn_probability * 100}%` }}
                  />
                </div>
              </div>
              <div className="rounded-lg bg-background/40 px-3 py-2 text-sm">
                <p className="font-medium">{churnResult.prediction}</p>
                <p className="mt-1 text-xs text-muted-foreground">{churnResult.message}</p>
              </div>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Run prediction to see churn results here.</p>
          )}
        </div>

        {/* CLV result */}
        <div className="glass rounded-2xl p-6">
          <div className="flex items-center gap-2 mb-3">
            <DollarSign className="w-4 h-4 text-primary" />
            <h3 className="text-sm font-semibold">Customer Lifetime Value — BG/NBD Model</h3>
          </div>
          {clvMut.isError && <p className="text-sm text-destructive">CLV prediction failed. Ensure CLV models are trained.</p>}
          {clvResult ? (
            <div className="space-y-3">
              {[
                { label: "Predicted CLV (30 days)", value: `$${clvResult.clv?.toFixed(2) ?? "—"}` },
                { label: "Expected Revenue", value: `$${clvResult.expected_revenue?.toFixed(2) ?? "—"}` },
                { label: "Predicted Purchases", value: `${clvResult.predicted_purchases?.toFixed(2) ?? "—"}` },
              ].map((item) => (
                <div key={item.label} className="flex items-center justify-between rounded-lg bg-background/40 px-3 py-2">
                  <span className="text-xs text-muted-foreground">{item.label}</span>
                  <span className="text-sm font-bold text-primary">{item.value}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">Run prediction to see CLV results.</p>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Main Tab component ───────────────────────────────────────────────────────

export function AIAnalystTab() {
  const [subTab, setSubTab] = useState<"rag" | "predict">("rag");

  return (
    <div className="space-y-4">
      {/* Sub-tab switcher */}
      <div className="glass inline-flex rounded-xl p-1">
        {[
          { key: "rag" as const, label: "🤖 RAG Assistant" },
          { key: "predict" as const, label: "📊 Predictive Engine" },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setSubTab(t.key)}
            className={cn(
              "rounded-lg px-4 py-2 text-sm font-medium transition",
              subTab === t.key ? "bg-primary text-primary-foreground shadow" : "text-muted-foreground hover:text-foreground",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {subTab === "rag" ? <RAGChat /> : <PredictiveEngine />}
    </div>
  );
}
