/**
 * Settings page — change base currency, UI language, and risk tolerance.
 *
 * Each change is persisted to /api/portfolio/me (PUT) and reflected
 * immediately: changing the locale also flips the i18n language so the
 * whole UI relocalises without a reload.
 */

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { api, ApiError } from "@/api/client";
import { Card } from "@/components/Card";
import { useUser } from "@/hooks/useUser";

const CURRENCIES = ["EUR", "USD", "GBP", "CHF", "JPY", "CAD", "AUD", "SEK", "NOK", "DKK"] as const;
const LOCALES = [
  { code: "en", labelKey: "language.en" as const },
  { code: "de", labelKey: "language.de" as const },
];
const TOLERANCES = ["conservative", "balanced", "aggressive"] as const;

export default function Settings() {
  const { t, i18n } = useTranslation("common");
  const queryClient = useQueryClient();
  const user = useUser();
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const update = useMutation({
    mutationFn: api.updatePreferences,
    onSuccess: (next) => {
      queryClient.setQueryData(["me"], next);
      void queryClient.invalidateQueries({ queryKey: ["valuation"] });
      if (next.locale && next.locale !== i18n.resolvedLanguage) {
        void i18n.changeLanguage(next.locale);
      }
      setSavedAt(Date.now());
      setError(null);
    },
    onError: (err) => {
      setError(err instanceof ApiError ? err.message : String(err));
      setSavedAt(null);
    },
  });

  const current = user.data;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">{t("settings.title")}</h1>
      </header>

      {user.isLoading && <p className="text-sm text-foreground/60">{t("common.loading")}</p>}

      {current && (
        <Card>
          <dl className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <div>
              <dt className="mb-1 text-xs text-foreground/60">{t("settings.base_currency")}</dt>
              <select
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                value={current.base_currency}
                onChange={(e) => update.mutate({ base_currency: e.target.value })}
                data-testid="settings-currency"
              >
                {CURRENCIES.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <dt className="mb-1 text-xs text-foreground/60">{t("settings.locale")}</dt>
              <select
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                value={current.locale}
                onChange={(e) => update.mutate({ locale: e.target.value })}
                data-testid="settings-locale"
              >
                {LOCALES.map(({ code, labelKey }) => (
                  <option key={code} value={code}>
                    {t(labelKey)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <dt className="mb-1 text-xs text-foreground/60">{t("settings.risk_tolerance")}</dt>
              <select
                className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
                value={current.risk_tolerance}
                onChange={(e) =>
                  update.mutate({
                    risk_tolerance: e.target.value as typeof TOLERANCES[number],
                  })
                }
                data-testid="settings-tolerance"
              >
                {TOLERANCES.map((v) => (
                  <option key={v} value={v}>
                    {t(`tolerance.${v}` as const)}
                  </option>
                ))}
              </select>
            </div>
          </dl>

          <div className="mt-4 text-xs">
            {update.isPending && <span className="text-foreground/60">…</span>}
            {!update.isPending && savedAt && (
              <span className="text-positive">{t("settings.saved")}</span>
            )}
            {error && <span className="text-negative">{error}</span>}
          </div>
        </Card>
      )}
    </div>
  );
}
