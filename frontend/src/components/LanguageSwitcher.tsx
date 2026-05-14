import { useTranslation } from "react-i18next";

import { SUPPORTED_LANGUAGES, type SupportedLanguage } from "@/i18n";

export function LanguageSwitcher() {
  const { t, i18n } = useTranslation("common");

  const active = (i18n.resolvedLanguage ?? "en") as SupportedLanguage;

  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="text-muted-foreground">{t("language.label")}:</span>
      <select
        aria-label={t("language.label")}
        value={active}
        onChange={(e) => {
          void i18n.changeLanguage(e.target.value);
        }}
        className="rounded-md border border-border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
      >
        {SUPPORTED_LANGUAGES.map((lng) => (
          <option key={lng} value={lng}>
            {t(`language.${lng}` as const)}
          </option>
        ))}
      </select>
    </label>
  );
}
