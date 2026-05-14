import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { api } from "@/api/client";

export default function Dashboard() {
  const { t } = useTranslation("common");

  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: () => api.me(),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{t("nav.dashboard")}</h1>
        <p className="text-sm text-foreground/60">{t("app.tagline")}</p>
      </div>

      <div className="rounded-lg border border-border bg-muted/30 p-4">
        {meQuery.isLoading && <p className="text-sm">Loading…</p>}
        {meQuery.isError && (
          <p className="text-sm text-negative">
            Could not reach the backend at <code>/api/portfolio/me</code>.
            Start it with <code>uvicorn app.main:app --reload</code>.
          </p>
        )}
        {meQuery.data && (
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-foreground/60">Email</dt>
            <dd>{meQuery.data.email}</dd>
            <dt className="text-foreground/60">{t("tolerance.label")}</dt>
            <dd>{t(`tolerance.${meQuery.data.risk_tolerance}` as const)}</dd>
            <dt className="text-foreground/60">Base currency</dt>
            <dd>{meQuery.data.base_currency}</dd>
            <dt className="text-foreground/60">Locale</dt>
            <dd>{meQuery.data.locale}</dd>
          </dl>
        )}
      </div>
    </div>
  );
}
