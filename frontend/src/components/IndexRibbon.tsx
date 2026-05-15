/**
 * Indices ribbon — horizontal strip of major-index quotes.
 *
 * Used on the Markets page (full width) and on the Dashboard (compact
 * variant) so the home view has a market heartbeat alongside the
 * user's portfolio.
 */

import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { api } from "@/api/client";
import { cn } from "@/lib/utils";
import { formatNumber, formatSignedPercent } from "@/lib/format";

interface IndexRibbonProps {
  variant?: "default" | "compact";
  className?: string;
}

export function IndexRibbon({ variant = "default", className }: IndexRibbonProps) {
  const { t } = useTranslation("common");
  const indices = useQuery({
    queryKey: ["markets", "indices"],
    queryFn: () => api.indices(),
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

  if (indices.isLoading) {
    return (
      <div className={cn("text-xs text-foreground/60", className)}>
        {t("markets.loading")}
      </div>
    );
  }

  if (indices.isError || !indices.data?.length) {
    return null;
  }

  return (
    <div className={cn("space-y-2", className)}>
      {variant === "default" && (
        <h2 className="text-xs font-medium uppercase tracking-wide text-foreground/60">
          {t("markets.indices")}
        </h2>
      )}
      <div
        className={cn(
          "flex gap-3 overflow-x-auto pb-2",
          variant === "compact" ? "" : "flex-wrap",
        )}
      >
        {indices.data.map((idx) => {
          const change = idx.change_pct ?? 0;
          const tone = change > 0 ? "text-positive" : change < 0 ? "text-negative" : "text-foreground/70";
          return (
            <div
              key={idx.ticker}
              className={cn(
                "min-w-[10rem] flex-shrink-0 rounded-lg border border-border bg-background px-3 py-2",
                variant === "compact" ? "min-w-[9rem]" : "",
              )}
              data-testid={`index-${idx.ticker}`}
            >
              <div className="flex items-center justify-between text-xs text-foreground/60">
                <span>{idx.name}</span>
                <span className="font-mono text-[10px]">{idx.ticker}</span>
              </div>
              <div className="mt-1 flex items-baseline justify-between gap-2">
                <span className="font-mono text-base">{formatNumber(idx.price, 2)}</span>
                <span className={cn("font-mono text-sm", tone)}>
                  {idx.change_pct != null ? formatSignedPercent(idx.change_pct) : "—"}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
