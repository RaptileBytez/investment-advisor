/**
 * Markets discovery — surfaces market state and Buy candidates so a user
 * who doesn't know any tickers has somewhere to start.
 *
 * Layout: indices ribbon, region filter + tab strip, then either the
 * Top Picks list or the Top Movers gainers/losers split.
 */

import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { IndexRibbon } from "@/components/IndexRibbon";
import { MoverList } from "@/components/MoverList";
import { TopPicksList } from "@/components/TopPicksList";
import { cn } from "@/lib/utils";
import { useUser } from "@/hooks/useUser";

type Tab = "picks" | "movers";
type MoverKind = "gainers" | "losers";

const REGIONS = ["all", "us", "de", "gb", "fr", "jp"] as const;
type RegionKey = (typeof REGIONS)[number];

function defaultRegionFor(locale: string | undefined): RegionKey {
  const lng = (locale ?? "").toLowerCase().split("-")[0];
  if (lng === "de") return "de";
  if (lng === "fr") return "fr";
  if (lng === "ja") return "jp";
  if (lng === "en") return "us";
  return "all";
}

export default function Markets() {
  const { t } = useTranslation("common");
  const user = useUser();

  const initialRegion = useMemo<RegionKey>(
    () => defaultRegionFor(user.data?.locale),
    [user.data?.locale],
  );
  const [region, setRegion] = useState<RegionKey>(initialRegion);
  const [tab, setTab] = useState<Tab>("picks");
  const [moverKind, setMoverKind] = useState<MoverKind>("gainers");

  const apiRegion = region === "all" ? undefined : region.toUpperCase();

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{t("markets.title")}</h1>
        <p className="text-sm text-foreground/70">{t("markets.subtitle")}</p>
      </header>

      <IndexRibbon />

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        {/* Region filter */}
        <div className="flex items-center gap-2">
          <label htmlFor="market-region" className="text-xs text-foreground/60">
            {t("markets.region.label")}
          </label>
          <select
            id="market-region"
            className="rounded-md border border-border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-accent"
            value={region}
            onChange={(e) => setRegion(e.target.value as RegionKey)}
            data-testid="market-region-filter"
          >
            {REGIONS.map((r) => (
              <option key={r} value={r}>
                {t(`markets.region.${r}` as const)}
              </option>
            ))}
          </select>
        </div>

        {/* Top tabs */}
        <div className="inline-flex rounded-md border border-border bg-background p-0.5" role="tablist">
          {(["picks", "movers"] as Tab[]).map((key) => (
            <button
              key={key}
              type="button"
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              data-testid={`tab-${key}`}
              className={cn(
                "rounded-md px-3 py-1 text-sm transition-colors",
                tab === key
                  ? "bg-accent/10 text-accent"
                  : "text-foreground/70 hover:bg-muted",
              )}
            >
              {t(`markets.tab.${key}` as const)}
            </button>
          ))}
        </div>
      </div>

      {tab === "picks" && <TopPicksList region={apiRegion} />}

      {tab === "movers" && (
        <div className="space-y-3">
          <div className="inline-flex rounded-md border border-border bg-background p-0.5" role="tablist">
            {(["gainers", "losers"] as MoverKind[]).map((key) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={moverKind === key}
                onClick={() => setMoverKind(key)}
                data-testid={`movers-${key}`}
                className={cn(
                  "rounded-md px-3 py-1 text-sm transition-colors",
                  moverKind === key
                    ? key === "gainers"
                      ? "bg-positive/10 text-positive"
                      : "bg-negative/10 text-negative"
                    : "text-foreground/70 hover:bg-muted",
                )}
              >
                {t(`markets.movers_sub.${key}` as const)}
              </button>
            ))}
          </div>
          <MoverList region={apiRegion} kind={moverKind} />
        </div>
      )}
    </div>
  );
}
