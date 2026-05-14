import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { api } from "@/api/client";
import { Card } from "@/components/Card";
import { SearchBox } from "@/components/SearchBox";
import { useUser } from "@/hooks/useUser";
import { formatCurrency, formatSignedPercent } from "@/lib/format";

export default function Dashboard() {
  const { t } = useTranslation("common");
  const user = useUser();
  const valuation = useQuery({
    queryKey: ["valuation"],
    queryFn: () => api.valuation(),
    enabled: !user.isLoading && !user.isError,
  });

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <h1 className="text-2xl font-semibold tracking-tight">{t("nav.dashboard")}</h1>
        <p className="text-sm text-foreground/60">{t("app.tagline")}</p>
      </header>

      <SearchBox />

      {user.isError && (
        <Card className="border-negative/30">
          <p className="text-sm text-negative">
            Could not reach the backend. Run <code>uvicorn app.main:app --reload</code> in the
            <code> backend/</code> directory.
          </p>
        </Card>
      )}

      {valuation.data && (
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
          <Card title="Positions">
            <p className="text-2xl font-mono">{valuation.data.positions.length}</p>
            <p className="mt-1 text-xs text-foreground/60">
              Concentration HHI: {valuation.data.concentration_hhi.toFixed(2)}
            </p>
          </Card>
        </div>
      )}

      {valuation.data && valuation.data.positions.length > 0 && (
        <Card title="Top holdings">
          <ul className="divide-y divide-border">
            {valuation.data.positions
              .slice()
              .sort((a, b) => b.market_value - a.market_value)
              .slice(0, 5)
              .map((p) => (
                <li key={p.ticker} className="flex items-center justify-between py-2 text-sm">
                  <span className="font-medium">{p.ticker}</span>
                  <span className="font-mono">
                    {formatCurrency(p.market_value, valuation.data.base_currency)}
                  </span>
                  <span
                    className={`font-mono ${p.unrealized_pl >= 0 ? "text-positive" : "text-negative"}`}
                  >
                    {formatSignedPercent(p.unrealized_pl_pct)}
                  </span>
                </li>
              ))}
          </ul>
        </Card>
      )}

      {valuation.data && valuation.data.positions.length === 0 && (
        <Card>
          <p className="text-sm text-foreground/70">
            Your portfolio is empty. Search a ticker above, open its detail page, and use
            "{t("actions.log_trade")}" to start tracking trades.
          </p>
        </Card>
      )}
    </div>
  );
}
