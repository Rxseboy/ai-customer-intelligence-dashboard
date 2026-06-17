import { useState } from "react";
import { format } from "date-fns";
import { Calendar as CalIcon, ChevronDown, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import { SEGMENTS, useDashboard, type SegmentKey } from "@/lib/dashboard-context";

import { useTranslation } from "react-i18next";
import { useAppStore } from "@/state/app-store";

function toISO(d: Date) {
  return d.toISOString().slice(0, 10);
}

export function DashboardHeader() {
  const { t } = useTranslation();
  const { language, setLanguage } = useAppStore();
  const { range, setRange, granularity, setGranularity, segments, setSegments } = useDashboard();
  const [openFrom, setOpenFrom] = useState(false);
  const [openTo, setOpenTo] = useState(false);

  const from = new Date(range.d_from);
  const to = new Date(range.d_to);

  const toggleSegment = (key: SegmentKey) => {
    setSegments(
      segments.includes(key) ? segments.filter((s) => s !== key) : [...segments, key],
    );
  };

  return (
    <header className="sticky top-0 z-30 glass border-x-0 border-t-0 px-6 py-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-primary to-chart-2 shadow-[var(--glow-primary)]">
            <span className="text-base font-bold text-primary-foreground">CI</span>
          </div>
          <div>
            <h1 className="text-base font-semibold leading-tight text-gradient">
              {t("dashboard.title", "Customer Intelligence")}
            </h1>
            <p className="text-xs text-muted-foreground">
              Real-time insights · {granularity} view
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Language Switcher */}
          <ToggleGroup
            type="single"
            value={language}
            onValueChange={(v) => v && setLanguage(v as "en" | "id")}
            className="glass rounded-md p-0.5 mr-2"
          >
            <ToggleGroupItem value="en" className="h-8 px-3 text-xs">EN</ToggleGroupItem>
            <ToggleGroupItem value="id" className="h-8 px-3 text-xs">ID</ToggleGroupItem>
          </ToggleGroup>

          {/* From */}
          <Popover open={openFrom} onOpenChange={setOpenFrom}>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm" className="glass border-border/60">
                <CalIcon className="h-4 w-4" />
                <span className="ml-2 text-xs font-medium text-muted-foreground">From</span>
                <span className="ml-1 text-xs font-semibold">{format(from, "MMM d, yyyy")}</span>
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="end">
              <Calendar
                mode="single"
                selected={from}
                onSelect={(d) => {
                  if (d) setRange({ ...range, d_from: toISO(d) });
                  setOpenFrom(false);
                }}
                className={cn("p-3 pointer-events-auto")}
              />
            </PopoverContent>
          </Popover>

          {/* To */}
          <Popover open={openTo} onOpenChange={setOpenTo}>
            <PopoverTrigger asChild>
              <Button variant="outline" size="sm" className="glass border-border/60">
                <CalIcon className="h-4 w-4" />
                <span className="ml-2 text-xs font-medium text-muted-foreground">To</span>
                <span className="ml-1 text-xs font-semibold">{format(to, "MMM d, yyyy")}</span>
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="end">
              <Calendar
                mode="single"
                selected={to}
                onSelect={(d) => {
                  if (d) setRange({ ...range, d_to: toISO(d) });
                  setOpenTo(false);
                }}
                className={cn("p-3 pointer-events-auto")}
              />
            </PopoverContent>
          </Popover>

          {/* Granularity */}
          <ToggleGroup
            type="single"
            value={granularity}
            onValueChange={(v) => v && setGranularity(v as typeof granularity)}
            className="glass rounded-md p-0.5"
          >
            <ToggleGroupItem value="weekly" className="h-8 px-3 text-xs">
              Weekly
            </ToggleGroupItem>
            <ToggleGroupItem value="monthly" className="h-8 px-3 text-xs">
              Monthly
            </ToggleGroupItem>
          </ToggleGroup>

          {/* Segments */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm" className="glass border-border/60">
                <Filter className="h-4 w-4" />
                <span className="ml-2 text-xs">
                  Segments · <span className="font-semibold">{segments.length}</span>
                </span>
                <ChevronDown className="ml-1 h-3.5 w-3.5 opacity-60" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="glass">
              <DropdownMenuLabel>RFM Segments</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {SEGMENTS.map((s) => (
                <DropdownMenuCheckboxItem
                  key={s.key}
                  checked={segments.includes(s.key)}
                  onCheckedChange={() => toggleSegment(s.key)}
                  onSelect={(e) => e.preventDefault()}
                >
                  <span className="mr-2">{s.emoji}</span>
                  {s.label}
                </DropdownMenuCheckboxItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
