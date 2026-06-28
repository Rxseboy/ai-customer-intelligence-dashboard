import React, { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children?: ReactNode;
  fallback?: ReactNode;
  /** Label for the section that crashed — shown in the error card */
  label?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Catches runtime errors in any child component (e.g. recharts crashing on
 * undefined data) and shows a clean fallback instead of a blank white screen.
 *
 * Usage:
 *   <TabErrorBoundary label="Product Analytics">
 *     <ProductAnalyticsTab />
 *   </TabErrorBoundary>
 */
export class ErrorBoundary extends Component<Props, State> {
  public state: State = { hasError: false, error: null };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[ErrorBoundary]", error, info.componentStack);
  }

  private handleReset = () => this.setState({ hasError: false, error: null });

  public render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div className="glass rounded-2xl p-8 flex flex-col items-center gap-4 text-center">
          <div className="p-3 rounded-xl bg-destructive/10 text-destructive">
            <AlertTriangle className="h-6 w-6" />
          </div>
          <div>
            <h3 className="font-semibold text-sm">
              {this.props.label ? `${this.props.label} failed to render` : "Something went wrong"}
            </h3>
            <p className="text-xs text-muted-foreground mt-1">
              {this.state.error?.message ?? "An unexpected error occurred in this component."}
            </p>
          </div>
          <button
            onClick={this.handleReset}
            className="flex items-center gap-2 text-xs px-4 py-2 rounded-lg border border-border hover:bg-white/10 transition-colors"
          >
            <RefreshCw className="h-3 w-3" />
            Try again
          </button>
          <details className="w-full text-left">
            <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
              Technical details
            </summary>
            <pre className="mt-2 text-[10px] text-muted-foreground overflow-auto bg-background/40 p-3 rounded-lg max-h-40">
              {this.state.error?.stack ?? this.state.error?.toString()}
            </pre>
          </details>
        </div>
      );
    }

    return this.props.children;
  }
}
