import { useTranslation } from "react-i18next";

import type { RiskSummaryOut } from "@/api/client";
import { Card } from "./Card";
import { ExplainTooltip } from "./ExplainTooltip";
import { formatNumber, formatPercent } from "@/lib/format";

interface RiskCardProps {
  risk: RiskSummaryOut;
  className?: string;
}

export function RiskCard({ risk, className }: RiskCardProps) {
  const { t } = useTranslation("risk");

  return (
    <Card
      title={t("card_title")}
      trailing={t("benchmark_against", { name: risk.benchmark })}
      className={className}
    >
      <dl className="grid grid-cols-1 gap-x-6 gap-y-3 text-sm sm:grid-cols-2">
        <Row
          label={
            <ExplainTooltip termKey="volatility">{t("metrics.volatility")}</ExplainTooltip>
          }
          value={formatPercent(risk.volatility, 1)}
        />
        <Row
          label={<ExplainTooltip termKey="sharpe-ratio">{t("metrics.sharpe")}</ExplainTooltip>}
          value={formatNumber(risk.sharpe, 2)}
        />
        <Row
          label={<ExplainTooltip termKey="beta">{t("metrics.beta")}</ExplainTooltip>}
          value={formatNumber(risk.beta, 2)}
        />
        <Row
          label={
            <ExplainTooltip termKey="max-drawdown">{t("metrics.max_drawdown")}</ExplainTooltip>
          }
          value={formatPercent(risk.max_drawdown, 1)}
          tone={risk.max_drawdown < 0 ? "negative" : "neutral"}
        />
        <Row
          label={
            <ExplainTooltip termKey="value-at-risk">
              {t("metrics.value_at_risk_95")}
            </ExplainTooltip>
          }
          value={formatPercent(risk.value_at_risk_95, 1)}
        />
        <Row
          label={
            <ExplainTooltip termKey="risk-free-rate">{t("risk_free_rate_label")}</ExplainTooltip>
          }
          value={formatPercent(risk.risk_free_rate, 2)}
        />
      </dl>
    </Card>
  );
}

function Row({
  label,
  value,
  tone = "neutral",
}: {
  label: React.ReactNode;
  value: string;
  tone?: "neutral" | "negative" | "positive";
}) {
  const colour =
    tone === "negative" ? "text-negative" : tone === "positive" ? "text-positive" : "";
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt className="text-foreground/70">{label}</dt>
      <dd className={`font-mono ${colour}`}>{value}</dd>
    </div>
  );
}
