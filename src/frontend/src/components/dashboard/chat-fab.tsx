import { useState, useRef, useEffect } from "react";
import { MessageSquareText, Send, Sparkles, X, Database, Terminal, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useTranslation } from "react-i18next";
import { useAppStore } from "@/state/app-store";
import { useChatStore } from "@/state/chat-store";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

export function ChatFab() {
  const { t } = useTranslation();
  const { language, isChatOpen, setChatOpen } = useAppStore();
  const { messages, addMessage, clearHistory } = useChatStore();
  const [question, setQuestion] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const ask = useMutation({
    mutationFn: (q: string) => api.ask({ question: q, language }),
    onSuccess: (r) => {
      addMessage({
        role: "ai",
        content: r.answer,
        sql: r.sql,
      });
    },
    onError: () => {
      addMessage({
        role: "ai",
        content: t("chat.failed", "Failed to query. Try again."),
      });
    }
  });

  const submit = () => {
    const q = question.trim();
    if (q.length < 2) return;
    addMessage({ role: "user", content: q });
    setQuestion("");
    ask.mutate(q);
  };

  return (
    <>
      {/* Panel */}
      <div
        className={cn(
          "fixed bottom-24 right-6 z-50 w-[420px] max-w-[calc(100vw-3rem)] origin-bottom-right transition-all flex flex-col shadow-2xl rounded-2xl glass",
          isChatOpen
            ? "scale-100 opacity-100 h-[600px] max-h-[80vh]"
            : "pointer-events-none scale-95 opacity-0 h-0"
        )}
      >
        <div className="flex items-center justify-between p-4 border-b border-border/50">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            <h3 className="text-sm font-semibold">{t("chat.ask_ai", "Ask AI Analyst")}</h3>
          </div>
          <div className="flex items-center gap-1">
            <Button size="icon" variant="ghost" className="h-7 w-7 text-muted-foreground" onClick={clearHistory} title="Clear history">
              <Database className="h-3 w-3" />
            </Button>
            <Button size="icon" variant="ghost" className="h-7 w-7" onClick={() => setChatOpen(false)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-4" ref={scrollRef}>
          {messages.length === 0 && (
            <div className="text-center text-sm text-muted-foreground mt-10">
              <p>{t("chat.description", "Natural language query against your warehouse.")}</p>
              <p className="mt-2 text-xs italic opacity-70">{t("chat.hint", 'e.g. "Top 5 customers by revenue this month"')}</p>
            </div>
          )}

          {messages.map((msg) => (
            <div key={msg.id} className={cn("flex flex-col gap-1 text-sm", msg.role === "user" ? "items-end" : "items-start")}>
              <div
                className={cn(
                  "px-4 py-2.5 rounded-2xl max-w-[90%]",
                  msg.role === "user"
                    ? "bg-primary text-primary-foreground rounded-tr-sm"
                    : "bg-background/60 border border-border/50 text-foreground rounded-tl-sm"
                )}
              >
                {msg.role === "user" ? (
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                ) : (
                  <div className="prose prose-sm dark:prose-invert max-w-none">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>

              {/* SQL Explanation Accordion for AI responses */}
              {msg.role === "ai" && msg.sql && (
                <div className="w-full mt-1 max-w-[90%]">
                  <Accordion type="single" collapsible className="w-full">
                    <AccordionItem value="sql" className="border-none">
                      <AccordionTrigger className="py-1 px-2 text-xs text-muted-foreground hover:no-underline bg-background/40 rounded-md border border-border/40 justify-start gap-2">
                        <Terminal className="h-3 w-3" />
                        <span>View SQL Query</span>
                      </AccordionTrigger>
                      <AccordionContent className="pt-2">
                        <div className="bg-zinc-950 p-3 rounded-md overflow-x-auto text-xs text-emerald-400 font-mono border border-zinc-800">
                          <pre>{msg.sql}</pre>
                        </div>
                      </AccordionContent>
                    </AccordionItem>
                  </Accordion>
                </div>
              )}
            </div>
          ))}

          {ask.isPending && (
            <div className="flex items-start">
              <div className="bg-background/60 border border-border/50 px-4 py-3 rounded-2xl rounded-tl-sm flex items-center gap-2 text-sm text-muted-foreground">
                <span className="flex gap-1">
                  <span className="h-1.5 w-1.5 bg-primary/60 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                  <span className="h-1.5 w-1.5 bg-primary/60 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                  <span className="h-1.5 w-1.5 bg-primary/60 rounded-full animate-bounce"></span>
                </span>
              </div>
            </div>
          )}
        </div>

        <div className="p-3 bg-background/50 border-t border-border/50">
          <div className="flex items-end gap-2 relative">
            <Textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              rows={1}
              placeholder={t("chat.placeholder", "Ask anything about your data…")}
              className="min-h-[44px] max-h-32 resize-none bg-background/80 pr-12 rounded-xl"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit();
                }
              }}
            />
            <Button 
              size="icon" 
              onClick={submit} 
              disabled={ask.isPending || question.trim().length === 0}
              className="absolute right-1.5 bottom-1.5 h-8 w-8 rounded-lg shadow-sm"
            >
              <Send className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* FAB */}
      <Button
        onClick={() => setChatOpen(!isChatOpen)}
        className="fixed bottom-6 right-6 z-50 h-14 w-14 rounded-full bg-gradient-to-br from-primary to-chart-3 shadow-[var(--glow-primary)] transition-transform hover:scale-105"
        size="icon"
      >
        {isChatOpen ? <X className="h-5 w-5" /> : <MessageSquareText className="h-5 w-5" />}
      </Button>
    </>
  );
}
