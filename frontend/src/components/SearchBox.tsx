/**
 * SearchBox — type a ticker, hit Enter or click a hit, jump to /stocks/:ticker.
 * Hits /api/stocks/search with debounced queries.
 */

import { type FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { api } from "@/api/client";
import { cn } from "@/lib/utils";

interface SearchBoxProps {
  className?: string;
}

export function SearchBox({ className }: SearchBoxProps) {
  const { t } = useTranslation("common");
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [debounced, setDebounced] = useState("");

  useEffect(() => {
    const id = setTimeout(() => setDebounced(q.trim()), 250);
    return () => clearTimeout(id);
  }, [q]);

  const results = useQuery({
    queryKey: ["search", debounced],
    queryFn: () => api.searchTickers(debounced),
    enabled: debounced.length >= 2,
    staleTime: 30_000,
  });

  function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const target = (results.data && results.data[0]?.ticker) ?? q.trim().toUpperCase();
    if (target) navigate(`/stocks/${encodeURIComponent(target)}`);
  }

  return (
    <form onSubmit={onSubmit} className={cn("relative w-full max-w-xl", className)} role="search">
      <input
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={`${t("actions.search")}…  e.g. AAPL, SAP.DE`}
        className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
        aria-label={t("actions.search")}
      />
      {debounced.length >= 2 && results.data && results.data.length > 0 && (
        <ul className="absolute left-0 right-0 z-20 mt-1 max-h-64 overflow-auto rounded-md border border-border bg-background shadow-lg">
          {results.data.slice(0, 10).map((hit) => (
            <li key={hit.ticker}>
              <Link
                to={`/stocks/${encodeURIComponent(hit.ticker)}`}
                onClick={() => setQ("")}
                className="flex items-center justify-between px-3 py-2 text-sm hover:bg-muted"
              >
                <span className="font-medium">{hit.ticker}</span>
                <span className="truncate text-foreground/60">{hit.name}</span>
                <span className="ml-2 text-xs text-foreground/50">{hit.exchange}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </form>
  );
}
