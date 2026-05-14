import { NavLink, Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { LanguageSwitcher } from "./LanguageSwitcher";
import { cn } from "@/lib/utils";

const NAV_KEYS = [
  { to: "/", key: "dashboard" },
  { to: "/portfolio", key: "portfolio" },
  { to: "/strategies", key: "strategies" },
  { to: "/trades", key: "trade_log" },
  { to: "/learn", key: "learn" },
] as const;

export default function Layout() {
  const { t } = useTranslation("common");

  return (
    <div className="min-h-screen bg-background text-foreground">
      <header className="border-b border-border bg-muted/30 backdrop-blur sticky top-0 z-10">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-4 py-3">
          <div className="flex items-center gap-2 font-semibold tracking-tight">
            <span className="text-accent">●</span>
            <span>{t("app.name")}</span>
          </div>
          <nav className="hidden gap-1 md:flex">
            {NAV_KEYS.map(({ to, key }) => (
              <NavLink
                key={to}
                to={to}
                end={to === "/"}
                className={({ isActive }) =>
                  cn(
                    "rounded-md px-3 py-1.5 text-sm transition-colors",
                    isActive
                      ? "bg-accent/10 text-accent"
                      : "text-foreground/70 hover:bg-muted hover:text-foreground",
                  )
                }
              >
                {t(`nav.${key}` as const)}
              </NavLink>
            ))}
          </nav>
          <LanguageSwitcher />
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">
        <Outlet />
      </main>

      <footer className="border-t border-border bg-muted/20">
        <div className="mx-auto max-w-7xl px-4 py-4 text-xs text-foreground/60">
          {t("disclaimer")}
        </div>
      </footer>
    </div>
  );
}
