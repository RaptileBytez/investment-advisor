/**
 * ExplainTooltip — universal inline-explanation widget.
 *
 * Wrap any label that names a financial term:
 *   <ExplainTooltip termKey="sharpe-ratio">Sharpe ratio</ExplainTooltip>
 *
 * Fetches the short summary from /api/glossary/{key}?lang=<active> via
 * react-query (so multiple tooltips for the same term hit the cache),
 * and shows it in a hover/focus popover with a "Learn more" link to the
 * Learn page. Fallback to English content is flagged.
 */

import { type ReactNode, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { api, ApiError } from "@/api/client";
import { cn } from "@/lib/utils";

interface ExplainTooltipProps {
  termKey: string;
  children: ReactNode;
  className?: string;
}

export function ExplainTooltip({ termKey, children, className }: ExplainTooltipProps) {
  const { i18n, t } = useTranslation("glossary");
  const lang = i18n.resolvedLanguage ?? "en";
  const [open, setOpen] = useState(false);

  const query = useQuery({
    queryKey: ["glossary", termKey, lang],
    queryFn: () => api.glossaryEntry(termKey, lang),
    enabled: open,
    staleTime: 60 * 60 * 1000,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) return false;
      return failureCount < 1;
    },
  });

  return (
    <span
      className={cn("relative inline-flex items-center gap-1", className)}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={() => setOpen(false)}
    >
      <span className="underline decoration-dotted decoration-foreground/40 underline-offset-4">
        {children}
      </span>
      <button
        type="button"
        aria-label={`What is ${termKey}?`}
        className="inline-flex h-4 w-4 items-center justify-center rounded-full border border-foreground/30 text-[10px] text-foreground/60 hover:bg-muted focus:outline-none focus:ring-2 focus:ring-accent"
      >
        i
      </button>

      {open && (
        <span
          role="tooltip"
          className="absolute left-0 top-full z-20 mt-1 w-72 rounded-md border border-border bg-background p-3 text-left text-xs shadow-lg"
        >
          {query.isLoading && <span className="text-foreground/60">Loading…</span>}
          {query.isError && (
            <span className="text-foreground/60">
              {query.error instanceof ApiError && query.error.status === 404
                ? t("no_results")
                : "—"}
            </span>
          )}
          {query.data && (
            <>
              {query.data.language_fallback && (
                <p className="mb-1 text-[10px] text-foreground/50">{t("translated_soon")}</p>
              )}
              <p className="font-medium">{query.data.title}</p>
              <p className="mt-1 text-foreground/80">{query.data.short}</p>
              <Link
                to={`/learn/${termKey}`}
                className="mt-2 inline-block text-accent hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                {t("page_title")} →
              </Link>
            </>
          )}
        </span>
      )}
    </span>
  );
}
