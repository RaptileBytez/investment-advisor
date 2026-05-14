import i18n from "i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import { initReactI18next } from "react-i18next";

import enCommon from "./locales/en/common.json";
import enErrors from "./locales/en/errors.json";
import enGlossary from "./locales/en/glossary.json";
import enRisk from "./locales/en/risk.json";
import enStrategies from "./locales/en/strategies.json";

import deCommon from "./locales/de/common.json";
import deErrors from "./locales/de/errors.json";
import deGlossary from "./locales/de/glossary.json";
import deRisk from "./locales/de/risk.json";
import deStrategies from "./locales/de/strategies.json";

export const SUPPORTED_LANGUAGES = ["en", "de"] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

export const DEFAULT_NAMESPACE = "common";
export const NAMESPACES = ["common", "errors", "glossary", "risk", "strategies"] as const;

void i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: "en",
    supportedLngs: SUPPORTED_LANGUAGES as unknown as string[],
    defaultNS: DEFAULT_NAMESPACE,
    ns: NAMESPACES as unknown as string[],
    interpolation: {
      escapeValue: false,
    },
    detection: {
      order: ["localStorage", "navigator"],
      caches: ["localStorage"],
      lookupLocalStorage: "investment-advisor.language",
    },
    resources: {
      en: {
        common: enCommon,
        errors: enErrors,
        glossary: enGlossary,
        risk: enRisk,
        strategies: enStrategies,
      },
      de: {
        common: deCommon,
        errors: deErrors,
        glossary: deGlossary,
        risk: deRisk,
        strategies: deStrategies,
      },
    },
  });

export default i18n;
