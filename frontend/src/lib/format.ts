/** Locale-aware formatters. The active i18n language drives the locale. */

import i18n from "@/i18n";

function locale(): string {
  // i18next "de" → Intl "de-DE", "en" → "en-US".
  const lng = i18n.resolvedLanguage ?? "en";
  switch (lng) {
    case "de":
      return "de-DE";
    case "en":
      return "en-US";
    default:
      return lng;
  }
}

export function formatCurrency(amount: number, currency: string): string {
  return new Intl.NumberFormat(locale(), {
    style: "currency",
    currency,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatPercent(value: number, fractionDigits = 2): string {
  return new Intl.NumberFormat(locale(), {
    style: "percent",
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value);
}

/** Format a signed percent: prepends + / -, two decimals. */
export function formatSignedPercent(value: number, fractionDigits = 2): string {
  const sign = value > 0 ? "+" : value < 0 ? "" : "";
  return `${sign}${formatPercent(value, fractionDigits)}`;
}

export function formatNumber(value: number, fractionDigits = 2): string {
  return new Intl.NumberFormat(locale(), {
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value);
}

export function formatDate(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return new Intl.DateTimeFormat(locale(), {
    year: "numeric",
    month: "short",
    day: "2-digit",
  }).format(d);
}
