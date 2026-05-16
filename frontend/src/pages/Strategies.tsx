import { type FormEvent, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { api, ApiError } from "@/api/client";
import { Card } from "@/components/Card";
import { RiskCard } from "@/components/RiskCard";
import { VerdictBadge } from "@/components/VerdictBadge";
import { formatPercent } from "@/lib/format";

type RiskTolerance = "conservative" | "balanced" | "aggressive";

export default function StrategiesPage() {
  const { t, i18n } = useTranslation(["common", "strategies"]);
  const lang = i18n.resolvedLanguage ?? "en";
  const strategies = useQuery({ queryKey: ["strategies"], queryFn: () => api.listStrategies() });

  const [ticker, setTicker] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const [tolerance, setTolerance] = useState<RiskTolerance | "">("");

  const evaluate = useMutation({
    mutationFn: () =>
      api.evaluate({
        ticker: ticker.trim().toUpperCase(),
        strategies: selected.length > 0 ? selected : undefined,
        risk_tolerance: tolerance || undefined,
        lang,
      }),
  });

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (ticker.trim()) evaluate.mutate();
  }

  function toggle(name: string) {
    setSelected((prev) =>
      prev.includes(name) ? prev.filter((s) => s !== name) : [...prev, name],
    );
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">{t("common:nav.strategies")}</h1>
        <p className="mt-1 text-sm text-foreground/60">
          {t("common:strategies_page.tagline")}
        </p>
      </header>

      <Card>
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <label className="block">
              <span className="mb-1 block text-xs text-foreground/60">{t("common:cols.ticker")}</span>
              <input
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder={t("common:strategies_page.ticker_placeholder")}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
              />
            </label>
            <label className="block">
              <span className="mb-1 block text-xs text-foreground/60">{t("common:tolerance.label")}</span>
              <select
                value={tolerance}
                onChange={(e) => setTolerance(e.target.value as RiskTolerance | "")}
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
              >
                <option value="">{t("common:strategies_page.use_my_profile")}</option>
                <option value="conservative">{t("common:tolerance.conservative")}</option>
                <option value="balanced">{t("common:tolerance.balanced")}</option>
                <option value="aggressive">{t("common:tolerance.aggressive")}</option>
              </select>
            </label>
            <div className="block">
              <span className="mb-1 block text-xs text-foreground/60">{t("common:strategies_page.strategies_label")}</span>
              <div className="flex flex-wrap gap-2 pt-1">
                {strategies.data?.map((name) => (
                  <button
                    key={name}
                    type="button"
                    onClick={() => toggle(name)}
                    className={`rounded-full border px-3 py-1 text-xs ${
                      selected.includes(name)
                        ? "border-accent bg-accent/10 text-accent"
                        : "border-border text-foreground/70 hover:bg-muted"
                    }`}
                  >
                    {t(`strategies:names.${name}` as const, { defaultValue: name })}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <div className="flex justify-end">
            <button
              type="submit"
              disabled={!ticker.trim() || evaluate.isPending}
              className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-50"
            >
              {evaluate.isPending
                ? t("common:actions.evaluating")
                : t("common:actions.evaluate")}
            </button>
          </div>
        </form>
      </Card>

      {evaluate.isError && (
        <Card className="border-negative/30">
          <p className="text-sm text-negative">
            {evaluate.error instanceof ApiError
              ? t("common:strategies_page.error_evaluate", {
                  ticker: ticker || t("common:strategies_page.ticker_placeholder"),
                  message: evaluate.error.message,
                })
              : t("common:strategies_page.error_evaluate_generic")}
          </p>
        </Card>
      )}

      {evaluate.data && (
        <>
          <Card
            title={
              <Link to={`/stocks/${encodeURIComponent(evaluate.data.ticker)}`} className="hover:underline">
                {evaluate.data.ticker}
              </Link>
            }
          >
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

          {evaluate.data.risk_summary && <RiskCard risk={evaluate.data.risk_summary} />}
        </>
      )}
    </div>
  );
}
