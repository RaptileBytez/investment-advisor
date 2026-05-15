/**
 * Sortable list of today's biggest gainers or losers from the universe.
 * Click a row to drill into Stock Detail.
 */

import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { api } from "@/api/client";
import { Card } from "@/components/Card";
import { cn } from "@/lib/utils";
import { formatCurrency, formatSignedPercent } from "@/lib/format";

interface MoverListProps {
  region?: string;
  kind: "gainers" | "losers";
  limit?: number;
}

export function MoverList({ region, kind, limit = 10 }: MoverListProps) {
  const { t } = useTranslation("common");
  const movers = useQuery({
    queryKey: ["markets", "movers", region ?? "all", kind, limit],
    queryFn: () => api.movers({ region, kind, limit }),
    staleTime: 60_000,
  });

  if (movers.isLoading) {
    return <p className="text-sm text-foreground/60">{t("markets.loading")}</p>;
  }
  if (movers.isError) {
    return (
      <Card className="border-negative/30">
        <p className="text-sm text-negative">{t("markets.error")}</p>
      </Card>
    );
  }
  if (!movers.data || movers.data.length === 0) {
    return (
      <Card>
        <p className="text-sm text-foreground/60">{t("markets.no_movers")}</p>
      </Card>
    );
  }

  return (
    <Card>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-foreground/60">
              <th className="py-1">{t("markets.col.ticker")}</th>
              <th className="py-1">{t("markets.col.name")}</th>
              <th className="py-1 hidden md:table-cell">{t("markets.col.exchange")}</th>
              <th className="py-1 text-right">{t("markets.col.price")}</th>
              <th className="py-1 text-right">{t("markets.col.change")}</th>
            </tr>
          </thead>
          <tbody>
            {movers.data.map((m) => {
              const change = m.change_pct ?? 0;
              const tone = change > 0 ? "text-positive" : change < 0 ? "text-negative" : "text-foreground/70";
              return (
                <tr key={m.ticker} className="border-t border-border" data-testid={`mover-${m.ticker}`}>
                  <td className="py-2">
                    <Link
                      to={`/stocks/${encodeURIComponent(m.ticker)}`}
                      className="font-medium text-accent hover:underline"
                    >
                      {m.ticker}
                    </Link>
                  </td>
                  <td className="py-2 text-foreground/80">{m.name}</td>
                  <td className="py-2 hidden md:table-cell text-foreground/60">{m.exchange}</td>
                  <td className="py-2 text-right font-mono">
                    {formatCurrency(m.price, m.currency)}
                  </td>
                  <td className={cn("py-2 text-right font-mono", tone)}>
                    {m.change_pct != null ? formatSignedPercent(m.change_pct) : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}
