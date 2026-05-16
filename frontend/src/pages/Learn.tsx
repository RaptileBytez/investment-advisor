import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { api } from "@/api/client";
import { Card } from "@/components/Card";

export default function Learn() {
  const { t, i18n } = useTranslation(["glossary", "common"]);
  const lang = i18n.resolvedLanguage ?? "en";
  const [q, setQ] = useState("");

  const list = useQuery({
    queryKey: ["glossary-list", lang],
    queryFn: () => api.glossaryList(lang),
    staleTime: 60 * 60_000,
  });

  const filter = q.trim().toLowerCase();
  const visible = list.data?.filter(
    (e) =>
      !filter ||
      e.title.toLowerCase().includes(filter) ||
      e.short.toLowerCase().includes(filter) ||
      e.key.includes(filter),
  );

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{t("page_title")}</h1>
        <p className="text-sm text-foreground/60">{t("page_subtitle")}</p>
      </header>

      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={t("search_placeholder")}
        className="w-full max-w-md rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
      />

      {list.isLoading && <p className="text-sm text-foreground/60">{t("common:common.loading")}</p>}

      {visible && visible.length === 0 && (
        <p className="text-sm text-foreground/70">{t("no_results")}</p>
      )}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {visible?.map((entry) => (
          <Link key={entry.key} to={`/learn/${entry.key}`} className="block">
            <Card className="h-full transition-colors hover:border-accent">
              <h2 className="text-base font-medium">{entry.title}</h2>
              {entry.language_fallback && (
                <p className="mt-1 text-[10px] text-foreground/50">{t("translated_soon")}</p>
              )}
              <p className="mt-2 text-sm text-foreground/70">{entry.short}</p>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  );
}
