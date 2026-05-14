import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { api, ApiError } from "@/api/client";
import { Card } from "@/components/Card";
import { ChartView } from "@/components/ChartView";
import { RiskCard } from "@/components/RiskCard";
import { TradeForm } from "@/components/TradeForm";
import { VerdictBadge } from "@/components/VerdictBadge";
import { formatCurrency, formatPercent, formatSignedPercent } from "@/lib/format";

const PERIODS = ["1mo", "6mo", "1y", "5y", "max"] as const;
type Period = (typeof PERIODS)[number];

export default function StockDetail() {
  const { t } = useTranslation(["common", "strategies"]);
  const { ticker = "" } = useParams<{ ticker: string }>();
  const [period, setPeriod] = useState<Period>("1y");
  const [showTradeForm, setShowTradeForm] = useState(false);

  const quote = useQuery({ queryKey: ["quote", ticker], queryFn: () => api.quote(ticker) });
  const history = useQuery({
    queryKey: ["history", ticker, period],
    queryFn: () => api.history(ticker, period, "1d"),
  });

  const evaluate = useMutation({
    mutationFn: () => api.evaluate({ ticker }),
  });

  // Auto-evaluate on first mount and whenever the ticker changes — that's
  // the "rationale" the user expects to see immediately.
  useEffect(() => {
    if (ticker) evaluate.mutate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ticker]);

  const change = quote.data?.change_pct;
  const changeColor = change == null ? "" : change >= 0 ? "text-positive" : "text-negative";

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{ticker}</h1>
          {quote.data && (
            <p className="mt-1 font-mono text-lg">
              {formatCurrency(quote.data.price, quote.data.currency)}
              {change != null && (
                <span className={`ml-3 text-sm ${changeColor}`}>
                  {formatSignedPercent(change)}
                </span>
              )}
            </p>
          )}
          {quote.isError && (
            <p className="text-sm text-negative">
              {quote.error instanceof ApiError ? quote.error.message : t("common:disclaimer")}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => evaluate.mutate()}
            disabled={evaluate.isPending}
            className="rounded-md border border-border bg-muted px-3 py-1.5 text-sm hover:bg-border disabled:cursor-not-allowed disabled:opacity-50"
            data-testid="evaluate-button"
          >
            {evaluate.isPending ? t("common:actions.evaluating") : t("common:actions.evaluate")}
          </button>
          <button
            onClick={() => setShowTradeForm((v) => !v)}
            className="rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-white"
          >
            {t("common:actions.log_trade")}
          </button>
        </div>
      </header>

      <Card
        trailing={
          <div className="flex gap-1">
            {PERIODS.map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`rounded px-2 py-0.5 text-xs ${
                  p === period
                    ? "bg-accent/10 text-accent"
                    : "text-foreground/60 hover:bg-muted"
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        }
      >
        {history.isLoading && <p className="text-sm text-foreground/60">Loading chart…</p>}
        {history.isError && (
          <p className="text-sm text-negative">
            {history.error instanceof ApiError ? history.error.message : "Could not load history."}
          </p>
        )}
        {history.data && <ChartView bars={history.data.bars} type="candlestick" />}
      </Card>

      {evaluate.isError && (
        <Card className="border-negative/30">
          <p className="text-sm text-negative">
            {evaluate.error instanceof ApiError
              ? `Could not evaluate ${ticker}: ${evaluate.error.message}`
              : `Could not evaluate ${ticker}.`}
          </p>
        </Card>
      )}

      {evaluate.data && (
        <Card title={t("strategies:rationale")}>
          <VerdictBadge
            verdict={evaluate.data.action}
            confidence={evaluate.data.confidence}
            rationale={evaluate.data.rationale}
          />
          {evaluate.data.strategy_results.length > 0 && (
            <ul className="mt-4 space-y-2 text-sm">
              {evaluate.data.strategy_results.map((r) => (
                <li key={r.strategy} className="rounded-md border border-border bg-muted/30 p-2">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">
                      {t(`strategies:names.${r.strategy}` as const, { defaultValue: r.strategy })}
                    </span>
                    <span className="text-xs text-foreground/60">
                      {t(`common:verdict.${r.verdict}` as const)} · {formatPercent(r.score, 0)}
                    </span>
                  </div>
                  <p className="mt-1 text-foreground/80">{r.rationale}</p>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}

      {evaluate.data?.risk_summary && <RiskCard risk={evaluate.data.risk_summary} />}

      {showTradeForm && (
        <Card title={t("common:actions.log_trade")}>
          <TradeForm defaultTicker={ticker} onSuccess={() => setShowTradeForm(false)} />
        </Card>
      )}
    </div>
  );
}
