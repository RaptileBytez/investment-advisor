/**
 * Engine-ranked BUY candidates from the universe.
 *
 * Backend filters to action="buy" and sorts by confidence; we just render.
 * Rationale text is already localised because the request carries the
 * active i18n language.
 */

import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { api } from "@/api/client";
import { Card } from "@/components/Card";
import { VerdictBadge } from "@/components/VerdictBadge";
import { cn } from "@/lib/utils";
import { formatCurrency, formatSignedPercent } from "@/lib/format";

interface TopPicksListProps {
  region?: string;
  limit?: number;
}

export function TopPicksList({ region, limit = 10 }: TopPicksListProps) {
  const { t, i18n } = useTranslation("common");
  const lang = i18n.resolvedLanguage ?? "en";

  const picks = useQuery({
    queryKey: ["markets", "top-picks", region ?? "all", limit, lang],
    queryFn: () => api.topPicks({ region, limit, lang }),
    // Heavy server path — keep results across navigations.
    staleTime: 10 * 60_000,
  });

  if (picks.isLoading) {
    return <p className="text-sm text-foreground/60">{t("markets.loading")}</p>;
  }
  if (picks.isError) {
    return (
      <Card className="border-negative/30">
        <p className="text-sm text-negative">{t("markets.error")}</p>
      </Card>
    );
  }
  if (!picks.data || picks.data.length === 0) {
    return (
      <Card>
        <p className="text-sm text-foreground/60">{t("markets.no_picks")}</p>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      {picks.data.map((p) => {
        const change = p.change_pct ?? 0;
        const tone = change > 0 ? "text-positive" : change < 0 ? "text-negative" : "text-foreground/70";
        return (
          <Card key={p.ticker} data-testid={`top-pick-${p.ticker}`}>
            <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div className="flex-1">
                <div className="flex items-baseline gap-3">
                  <Link
                    to={`/stocks/${encodeURIComponent(p.ticker)}`}
                    className="text-lg font-semibold text-accent hover:underline"
                  >
                    {p.ticker}
                  </Link>
                  <span className="text-sm text-foreground/80">{p.name}</span>
                  <span className="text-xs text-foreground/60">{p.exchange}</span>
                </div>
                <p className="mt-2 text-sm text-foreground/80">{p.rationale}</p>
              </div>
              <div className="md:min-w-[14rem] md:text-right">
                <div className="flex items-baseline justify-between gap-3 md:justify-end">
                  <span className="font-mono text-base">
                    {formatCurrency(p.price, p.currency)}
                  </span>
                  <span className={cn("font-mono text-sm", tone)}>
                    {p.change_pct != null ? formatSignedPercent(p.change_pct) : ""}
                  </span>
                </div>
                <div className="mt-2 md:flex md:justify-end">
                  <VerdictBadge verdict={p.action} confidence={p.confidence} />
                </div>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}
