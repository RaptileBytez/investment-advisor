import { useEffect, useRef } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import renderMathInElement from "katex/contrib/auto-render";

import { api, ApiError } from "@/api/client";
import { Card } from "@/components/Card";

export default function LearnEntry() {
  const { t, i18n } = useTranslation("glossary");
  const { term = "" } = useParams<{ term: string }>();
  const lang = i18n.resolvedLanguage ?? "en";
  const articleRef = useRef<HTMLDivElement>(null);

  const entry = useQuery({
    queryKey: ["glossary", term, lang],
    queryFn: () => api.glossaryEntry(term, lang),
    retry: (count, err) => {
      if (err instanceof ApiError && err.status === 404) return false;
      return count < 1;
    },
  });

  // Run KaTeX auto-render whenever the article HTML lands.
  useEffect(() => {
    if (!articleRef.current || !entry.data?.body_html) return;
    renderMathInElement(articleRef.current, {
      delimiters: [
        { left: "$$", right: "$$", display: true },
        { left: "$", right: "$", display: false },
        { left: "\\(", right: "\\)", display: false },
        { left: "\\[", right: "\\]", display: true },
      ],
      throwOnError: false,
    });
  }, [entry.data?.body_html]);

  return (
    <div className="space-y-4">
      <Link to="/learn" className="text-sm text-accent hover:underline">
        ← {t("page_title")}
      </Link>

      {entry.isLoading && <p className="text-sm text-foreground/60">Loading…</p>}
      {entry.isError && (
        <p className="text-sm text-negative">
          {entry.error instanceof ApiError && entry.error.status === 404
            ? t("no_results")
            : "—"}
        </p>
      )}

      {entry.data && (
        <Card>
          {entry.data.language_fallback && (
            <p className="mb-3 rounded-md border border-accent/30 bg-accent/10 px-3 py-2 text-xs text-accent">
              {t("translated_soon")}
            </p>
          )}
          <h1 className="text-2xl font-semibold tracking-tight">{entry.data.title}</h1>
          <p className="mt-2 text-foreground/70">{entry.data.short}</p>
          <article
            ref={articleRef}
            className="prose prose-sm mt-6 max-w-none text-foreground/90 [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_h3]:mt-6 [&_h3]:mb-2 [&_h3]:text-base [&_h3]:font-semibold [&_p]:my-3 [&_table]:my-4 [&_table]:w-full [&_table]:border-collapse [&_th]:text-left [&_th]:py-1 [&_th]:px-2 [&_th]:font-medium [&_th]:border-b [&_th]:border-border [&_td]:py-1 [&_td]:px-2 [&_td]:border-t [&_td]:border-border"
            dangerouslySetInnerHTML={{ __html: entry.data.body_html }}
          />
          {entry.data.related.length > 0 && (
            <div className="mt-6 border-t border-border pt-4">
              <p className="mb-2 text-xs text-foreground/60">Related</p>
              <ul className="flex flex-wrap gap-2">
                {entry.data.related.map((key) => (
                  <li key={key}>
                    <Link
                      to={`/learn/${key}`}
                      className="rounded-full border border-border bg-muted/30 px-3 py-1 text-xs hover:bg-muted"
                    >
                      {key}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
