import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { api } from "@/api/client";
import { Card } from "@/components/Card";
import { formatCurrency, formatPercent, formatSignedPercent } from "@/lib/format";

export default function Portfolio() {
  const { t } = useTranslation("common");
  const valuation = useQuery({
    queryKey: ["valuation"],
    queryFn: () => api.valuation(),
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">{t("nav.portfolio")}</h1>
      </header>

      {valuation.isLoading && <p className="text-sm text-foreground/60">Loading…</p>}
      {valuation.isError && (
        <Card className="border-negative/30">
          <p className="text-sm text-negative">Could not load portfolio.</p>
        </Card>
      )}

      {valuation.data && valuation.data.positions.length === 0 && (
        <Card>
          <p className="text-sm">
            No holdings yet. Search a ticker on the dashboard and use "{t("actions.log_trade")}" to
            record your first position.
          </p>
        </Card>
      )}

      {valuation.data && valuation.data.positions.length > 0 && (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <Card title="Total value">
              <p className="text-2xl font-mono">
                {formatCurrency(valuation.data.total_value, valuation.data.base_currency)}
              </p>
            </Card>
            <Card title="Unrealised P&L">
              <p
                className={`text-2xl font-mono ${valuation.data.total_unrealized_pl >= 0 ? "text-positive" : "text-negative"}`}
              >
                {formatCurrency(valuation.data.total_unrealized_pl, valuation.data.base_currency)}
                <span className="ml-2 text-sm">
                  {formatSignedPercent(valuation.data.total_unrealized_pl_pct)}
                </span>
              </p>
            </Card>
            <Card title="Concentration (HHI)">
              <p className="text-2xl font-mono">{valuation.data.concentration_hhi.toFixed(2)}</p>
              <p className="mt-1 text-xs text-foreground/60">
                {valuation.data.concentration_hhi >= 0.5
                  ? "Very concentrated"
                  : valuation.data.concentration_hhi >= 0.25
                  ? "Moderate"
                  : "Diversified"}
              </p>
            </Card>
          </div>

          <Card title="Positions">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-foreground/60">
                    <th className="py-1">Ticker</th>
                    <th className="py-1 text-right">Qty</th>
                    <th className="py-1 text-right">Avg cost</th>
                    <th className="py-1 text-right">Price</th>
                    <th className="py-1 text-right">Market value</th>
                    <th className="py-1 text-right">P&L</th>
                    <th className="py-1 text-right">Weight</th>
                  </tr>
                </thead>
                <tbody>
                  {valuation.data.positions.map((p) => (
                    <tr key={p.ticker} className="border-t border-border">
                      <td className="py-2">
                        <Link
                          to={`/stocks/${encodeURIComponent(p.ticker)}`}
                          className="font-medium text-accent hover:underline"
                        >
                          {p.ticker}
                        </Link>
                      </td>
                      <td className="py-2 text-right font-mono">{p.quantity}</td>
                      <td className="py-2 text-right font-mono">
                        {formatCurrency(p.avg_cost, p.currency)}
                      </td>
                      <td className="py-2 text-right font-mono">
                        {formatCurrency(p.current_price, p.currency)}
                      </td>
                      <td className="py-2 text-right font-mono">
                        {formatCurrency(p.market_value, valuation.data.base_currency)}
                      </td>
                      <td
                        className={`py-2 text-right font-mono ${p.unrealized_pl >= 0 ? "text-positive" : "text-negative"}`}
                      >
                        {formatSignedPercent(p.unrealized_pl_pct)}
                      </td>
                      <td className="py-2 text-right font-mono">{formatPercent(p.weight, 1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <Card title="Currency exposure">
            <ul className="space-y-1 text-sm">
              {Object.entries(valuation.data.currency_exposure)
                .sort((a, b) => b[1] - a[1])
                .map(([ccy, share]) => (
                  <li key={ccy} className="flex items-center justify-between">
                    <span className="font-medium">{ccy}</span>
                    <span className="font-mono">{formatPercent(share, 1)}</span>
                  </li>
                ))}
            </ul>
          </Card>
        </>
      )}
    </div>
  );
}
