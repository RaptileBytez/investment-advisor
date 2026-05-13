# Investment Advisor — Implementation Plan

## Context

This is a greenfield build of a personal investment-advisor web app. The user
wants a tool that:

- Monitors the stock market and tracks a user's portfolio.
- Suggests investments optimizing return vs. risk, supporting multiple
  strategies (Buy & Hold, DCA, Value, Momentum).
- For existing holdings, recommends **Buy more / Hold / Sell** with reasoning.
- Visualizes price history for any selected stock.
- Provides a UI to log buys/sells (paper trading first).
- Is **user-friendly**: every financial term, strategy, and risk metric is
  explained inline.
- Supports **international markets** — a user in Europe/Germany must be able
  to research and hold European stocks (e.g. `SAP.DE`), with currency and
  benchmark handled locally.

Approach: ship a **lean MVP** with a pluggable architecture so we can layer
on broker-API execution, more strategies, and alerts without rewrites.

---

## Tech stack (locked)

| Layer        | Choice                                                      |
| ------------ | ----------------------------------------------------------- |
| Backend      | Python 3.11+, FastAPI, SQLAlchemy, Pydantic                 |
| Quant libs   | `pandas`, `numpy`, `scipy`, `yfinance`, `pandas-ta`         |
| DB           | SQLite (file-local) via SQLAlchemy — easy upgrade to Postgres |
| Frontend     | React + TypeScript + Vite                                   |
| UI kit       | Tailwind CSS + shadcn/ui                                    |
| Charts       | TradingView `lightweight-charts` (best free stock charting) |
| i18n/locale  | `react-i18next` + browser `Intl` (UI strings **and** content) |
| Tests        | `pytest` (backend), `vitest` + React Testing Library (front) |

---

## Repository layout

```
investment-advisor/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entrypoint
│   │   ├── api/                    # REST routers
│   │   │   ├── stocks.py           # search, quote, history, fundamentals
│   │   │   ├── portfolio.py        # holdings, transactions, valuation
│   │   │   ├── strategies.py       # run a strategy, get suggestions
│   │   │   ├── risk.py             # risk metrics for ticker / portfolio
│   │   │   └── glossary.py         # terms, explanations
│   │   ├── data/
│   │   │   ├── provider.py         # DataProvider abstract interface
│   │   │   └── providers/
│   │   │       ├── yfinance_provider.py   # MVP default
│   │   │       └── broker_provider.py     # stub for later (Alpaca/IBKR)
│   │   ├── strategies/
│   │   │   ├── base.py             # Strategy ABC, common scoring
│   │   │   ├── buy_hold.py
│   │   │   ├── dca.py
│   │   │   ├── value.py
│   │   │   └── momentum.py
│   │   ├── risk/
│   │   │   ├── metrics.py          # volatility, Sharpe, beta, drawdown, VaR
│   │   │   └── benchmarks.py       # region → benchmark/risk-free rate map
│   │   ├── portfolio/
│   │   │   ├── service.py          # add/remove holdings, record trades
│   │   │   └── valuation.py        # current value, P&L, time series
│   │   ├── recommendation/
│   │   │   └── engine.py           # combines strategy + risk → verdict
│   │   ├── glossary/
│   │   │   └── entries/
│   │   │       ├── en/*.md         # English glossary content
│   │   │       └── de/*.md         # German glossary content (parallel files)
│   │   ├── db/
│   │   │   ├── models.py           # SQLAlchemy models
│   │   │   └── session.py
│   │   └── core/
│   │       ├── config.py           # env, settings (locale, currency)
│   │       └── cache.py            # in-memory + SQLite price cache
│   ├── tests/
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx
│   │   │   ├── StockDetail.tsx
│   │   │   ├── Portfolio.tsx
│   │   │   ├── Strategies.tsx
│   │   │   ├── TradeLog.tsx
│   │   │   └── Learn.tsx           # glossary / strategy explainers
│   │   ├── components/
│   │   │   ├── ChartView.tsx       # lightweight-charts wrapper
│   │   │   ├── RiskCard.tsx
│   │   │   ├── StrategyCard.tsx
│   │   │   ├── ExplainTooltip.tsx  # hover any metric → glossary entry
│   │   │   ├── TradeForm.tsx       # log buy/sell
│   │   │   └── VerdictBadge.tsx    # Buy / Hold / Sell + rationale
│   │   ├── api/                    # typed fetch client
│   │   ├── i18n/
│   │   │   ├── index.ts            # i18next config, language detection, fallback
│   │   │   └── locales/
│   │   │       ├── en/             # one JSON per namespace
│   │   │       │   ├── common.json
│   │   │       │   ├── glossary.json
│   │   │       │   ├── strategies.json
│   │   │       │   ├── risk.json
│   │   │       │   └── errors.json
│   │   │       └── de/             # same namespaces, German
│   │   └── lib/
│   ├── index.html
│   └── package.json
└── README.md
```

---

## Data layer (pluggable)

`DataProvider` interface defines the integration seam:

```python
class DataProvider(ABC):
    def search(self, q: str, market: str | None = None) -> list[TickerInfo]: ...
    def get_quote(self, ticker: str) -> Quote: ...
    def get_history(self, ticker: str, period: str, interval: str) -> pd.DataFrame: ...
    def get_fundamentals(self, ticker: str) -> Fundamentals: ...
```

- **MVP impl**: `YFinanceProvider`. Free, no key, supports US + European
  tickers via suffixes (`.DE` Xetra, `.PA` Euronext Paris, `.L` London,
  `.AS` Amsterdam, `.MI` Milan, etc.). Will document rate-limit caveats.
- **Caching**: in-memory LRU for quotes (60s TTL); SQLite-backed cache for
  daily history (24 h TTL). Keeps the app responsive and reduces 429s.
- **Future providers**: `AlpacaProvider`, `IBKRProvider` implement the same
  interface — switching only changes a config flag. Broker providers will
  extend with `place_order()`, `get_account()` when we add live trading.

---

## Database schema (SQLite, single-user MVP, multi-user-ready)

| Table          | Key columns                                                            |
| -------------- | ---------------------------------------------------------------------- |
| `users`        | id, email, base_currency, locale, risk_tolerance                       |
| `holdings`     | id, user_id, ticker, quantity, avg_cost, currency, opened_at           |
| `transactions` | id, user_id, ticker, side (buy/sell), qty, price, fees, executed_at, note |
| `watchlist`    | id, user_id, ticker, added_at                                          |
| `snapshots`    | id, user_id, taken_at, total_value, by_position_json (daily portfolio history) |
| `cache_prices` | ticker, date, ohlcv (price-history cache)                              |

Migrations via Alembic from day 1 so schema evolves cleanly.

---

## Strategies (MVP — all four)

Each strategy implements `score(ticker, history, fundamentals) -> StrategyResult`
returning `{score, verdict, rationale, key_inputs}`. Verdict ∈ `BUY / HOLD / SELL / WATCH`.

1. **Buy & Hold** — favors large-cap, low-volatility names with positive
   long-term CAGR and stable earnings. Good "default" for conservative users.
2. **Dollar-Cost Averaging (DCA)** — input: ticker(s), amount, cadence. Output:
   simulated outcome over the last 5/10 yrs vs. lump-sum, plus an action
   schedule. Reduces timing risk.
3. **Value investing** — screen on P/E, P/B, debt/equity, dividend yield,
   free-cash-flow yield. Compare against sector medians. Flags "undervalued
   vs. peers" candidates.
4. **Momentum / trend following** — 12-1 momentum, RSI(14), SMA50/SMA200
   crossover (golden/death cross). Flags trend-up / trend-down signals.

The `RecommendationEngine` combines per-strategy outputs into a single verdict
per holding/candidate using the user's selected strategy weights and risk
tolerance. Each verdict carries a **plain-language rationale** for the UI.

---

## Risk metrics (region-aware)

All metrics in `app/risk/metrics.py`:

- **Volatility** — annualized std of daily log returns.
- **Sharpe ratio** — uses a region-appropriate risk-free rate (US Treasury
  3M for USD, ECB €STR for EUR, BoE base for GBP). Configurable in
  `risk/benchmarks.py`.
- **Beta** — vs region-appropriate benchmark: S&P 500 (US), STOXX 600 (EU),
  DAX (DE), FTSE 100 (UK). Mapped automatically from the ticker suffix.
- **Max drawdown** — peak-to-trough on cumulative returns.
- **Value at Risk (VaR 95 %)** — historical method on daily returns.
- **Portfolio concentration** — Herfindahl-Hirschman Index on position weights.
- **Currency exposure** — % of portfolio per currency.

Every metric is paired with a glossary entry so the UI explains it in plain
language on hover.

---

## Internationalization (UI language)

Frontend ships with **English and German** at MVP, designed so adding a new
language is purely additive (drop in a `locales/<code>/` folder, register
the code, done — no code changes elsewhere).

**Approach**

- `react-i18next` for translation lookups; `i18next-browser-languagedetector`
  to seed initial language from `navigator.language` (falls back to English).
- Translations split by **namespace** (`common`, `glossary`, `strategies`,
  `risk`, `errors`) so lazy-loading is possible later if files grow.
- **No hardcoded strings** in components — every visible label, button,
  tooltip, error, and chart legend uses `t("namespace:key")`. Lint rule
  (`eslint-plugin-i18next` `no-literal-string`) enforces this in CI.
- A `LanguageSwitcher` component lives in the top nav; selected language is
  persisted to the user preferences API (so it survives reloads and can be
  set from onboarding).
- **Pluralization & interpolation** via i18next ICU-style placeholders
  (`{{count}}`, `{{price, currency}}`).
- **Locale-bound formatting** for dates, numbers, percentages, and currency
  via `Intl.NumberFormat` / `Intl.DateTimeFormat` — the active i18next
  language drives the `Intl` locale tag.

**Glossary & strategy content (long-form text)**

Long-form explanations live as **markdown files keyed by language** in the
backend (`app/glossary/entries/<lang>/<term>.md`). The `/glossary` API
accepts an `?lang=` parameter (defaults to the user's preference) and
returns the matching content, falling back to English if a translation is
missing. This keeps long content out of JSON locale files and authorable
in plain markdown.

**Adding a new language later**

1. Create `frontend/src/i18n/locales/<code>/*.json` (copy English as a
   starting point).
2. Create `backend/app/glossary/entries/<code>/*.md` (any missing file
   falls back to English automatically).
3. Register `<code>` in `frontend/src/i18n/index.ts` `supportedLngs`.
4. Add the entry to `LanguageSwitcher`.

No core code changes required — that is the success criterion for the
i18n design.

---

## International / multi-currency support

- User sets **base currency** (EUR, USD, GBP, …) in preferences during onboarding.
- All portfolio totals are normalized to base currency using daily FX rates
  (fetched via `yfinance` FX pairs e.g. `EURUSD=X`).
- Stock search supports ticker suffixes and exchange filters (`Xetra`,
  `Euronext`, `LSE`, `NYSE`, `Nasdaq`).
- Benchmarks and risk-free rates auto-pick by region — explained in the UI
  ("Beta computed vs. DAX because SAP.DE is listed in Germany").
- Market-hours indicator per exchange on stock detail pages.
- Number/date/currency formatting via `Intl` driven by the user's locale.

---

## Frontend pages (MVP)

1. **Dashboard** — portfolio value, today's P&L, top movers in your holdings,
   3 top suggestions from your active strategy, recent alerts/signals.
2. **Stock Detail** — interactive `ChartView` (1D / 1W / 1M / 1Y / 5Y / Max),
   key stats, fundamentals card, **RiskCard** (all metrics, each with hover
   explanations), **VerdictBadge** with rationale, "Log a trade" button.
3. **Portfolio** — table of holdings with qty, avg cost, current price,
   unrealized P&L, % of portfolio, per-position verdict (Buy more / Hold /
   Sell). Concentration & currency-exposure charts.
4. **Strategies** — pick a strategy, set investable amount, optional
   constraints (sector, region, max risk), get a ranked list of candidates
   with rationale and visualized risk/return.
5. **Trade Log** — chronological list of paper trades; `TradeForm` to add a
   buy or sell (auto-fills price from the executed date).
6. **Learn** — full glossary (search + categorized) and "How this strategy
   works" deep-dives. Every metric, every chart, every signal links here.

### Explanation layer (cross-cutting)

- `ExplainTooltip` is the single component used everywhere a financial term
  appears. It loads short text from the glossary API and a "Learn more" link.
- Strategy pages embed a collapsible "How this works" panel with examples.
- Every recommendation includes a `rationale` field rendered as a 1-3 line
  human-readable sentence (e.g., *"Momentum is positive (12-1 return +18 %),
  trading above its 200-day SMA, with volatility 22 % p.a. — moderate risk,
  consistent with your balanced profile."*).
- Persistent risk disclaimer banner — "Past performance is not indicative of
  future results. This tool provides educational guidance, not financial advice."

---

## Recommendation engine

`app/recommendation/engine.py`:

1. Pull strategy results for each candidate / holding.
2. Compute risk metrics relative to the user's portfolio (does adding this
   position raise or lower portfolio risk? does it improve diversification?).
3. Combine into a final verdict using user-set strategy weights + risk
   tolerance bucket (`conservative` / `balanced` / `aggressive`).
4. Emit `Verdict { action, confidence, rationale, key_signals }`.

This is the single place where "Buy / Hold / Sell" decisions are produced;
strategies stay narrowly focused on their own signal.

---

## Extension hooks (designed in, not built yet)

- `BrokerProvider` interface alongside `DataProvider` — wiring is already in
  the config layer; switching from paper to real trading is a provider swap +
  an "Execute trade" confirmation flow.
- `Alerts` table + websocket channel — schema slot reserved.
- Multi-user: all queries are already scoped by `user_id` even though MVP
  ships single-user. Adding JWT auth later is additive.
- Backtesting sandbox — strategies already operate on historical dataframes;
  reusing them for backtests is straightforward.

---

## Critical files to create (build order)

1. `backend/app/db/models.py`, `backend/app/db/session.py` — schema first.
2. `backend/app/data/provider.py` + `providers/yfinance_provider.py` — data seam.
3. `backend/app/risk/metrics.py` + `risk/benchmarks.py` — math foundation.
4. `backend/app/strategies/{base,buy_hold,dca,value,momentum}.py`.
5. `backend/app/recommendation/engine.py`.
6. `backend/app/portfolio/{service,valuation}.py`.
7. `backend/app/api/*.py` + `backend/app/main.py`.
8. Glossary content seeded as `backend/app/glossary/entries/*.md`.
9. Frontend scaffold (Vite + React + TS + Tailwind + shadcn).
10. `frontend/src/components/{ChartView,RiskCard,ExplainTooltip,TradeForm,VerdictBadge}.tsx`.
11. Pages in order: StockDetail → Portfolio → Strategies → Dashboard → TradeLog → Learn.

---

## Verification

**Backend unit tests (`pytest`)**

- Risk metrics: assert against textbook values on a synthetic series
  (volatility, Sharpe with known inputs, max drawdown, VaR 95 % via percentile).
- Each strategy: snapshot rationale + verdict on a fixed historical slice
  (e.g., `AAPL` 2018-2020) using a mocked provider — pure-function so stable.
- Recommendation engine: combine known strategy outputs, assert final verdict
  for each risk-tolerance bucket.
- `YFinanceProvider`: smoke test fetching `AAPL` and `SAP.DE`; verify currency,
  exchange, and history shape.

**Frontend tests (`vitest`)**

- `ExplainTooltip` renders glossary content on hover.
- `RiskCard` renders all metrics with their explanations.
- `TradeForm` validates qty/price and posts to the API.

**End-to-end manual walkthrough (must pass before "MVP done")**

1. Start backend: `uvicorn app.main:app --reload`.
2. Start frontend: `npm run dev`.
3. Onboarding: set base currency = EUR, locale = de-DE, risk = balanced.
4. Search `SAP.DE` → open Stock Detail → chart renders, RiskCard shows beta
   vs. DAX, all metrics have working hover explanations.
5. Log a paper buy (10 shares at historical close) → appears in Portfolio
   with correct EUR P&L.
6. Open Strategies → run Value with €5 000 budget → ranked list with
   rationales and per-candidate verdicts.
7. Open Portfolio → SAP.DE row shows Buy more / Hold / Sell verdict with a
   1-3 line rationale and links into the explanation.
8. Open Learn → search "Sharpe ratio" → entry loads with example.
9. Switch base currency to USD → all portfolio values reconverted; benchmark
   for `AAPL` becomes S&P 500.
10. Switch UI language to German via `LanguageSwitcher` → every label,
    tooltip, glossary entry, and verdict rationale renders in German;
    numbers and dates format per `de-DE`; reload preserves the choice.
11. Delete one German locale key → CI's `i18n-check.yml` fails the PR,
    proving the safety net works.

---

## Repository & version control (GitHub)

Set up a GitHub repository **before any code is written**, so every change
is tracked from commit 1 and issues can be filed against early decisions.

**Initial setup**

1. `git init` in `d:/Coding/Projects/investment-advisor`.
2. Create a `.gitignore` covering both stacks: Python (`__pycache__`,
   `.venv/`, `*.pyc`, `.pytest_cache/`, `*.db`, `*.sqlite`, `.env`) and
   Node (`node_modules/`, `dist/`, `.vite/`, `coverage/`).
3. Create a GitHub repo via `gh repo create investment-advisor --private`
   (will confirm public vs. private with user before running).
4. Initial commit on `main` with the scaffold + this plan committed under
   `docs/plan.md`.
5. Push `main` and set it as the default branch with branch protection
   (require PR, require CI green) once the first CI run lands.

**Branching & commits**

- `main` is always deployable.
- Feature work on short-lived branches: `feat/<scope>`, `fix/<scope>`,
  `chore/<scope>`. PR-only merges, no direct pushes to `main`.
- **Conventional Commits** (`feat:`, `fix:`, `chore:`, `docs:`, `test:`,
  `refactor:`) — makes changelog generation trivial later.

**Repo hygiene files**

- `README.md` — what the project is, quickstart for both backend and
  frontend, link to the plan.
- `CONTRIBUTING.md` — branch naming, commit style, how to run tests.
- `.github/ISSUE_TEMPLATE/bug_report.md` and `feature_request.md`.
- `.github/PULL_REQUEST_TEMPLATE.md` — summary, screenshots, test plan,
  checklist (tests added, docs updated, glossary updated if a new metric).
- `LICENSE` (suggest MIT — will confirm with user).
- `SECURITY.md` — how to report vulnerabilities (relevant once we touch
  broker APIs).

**Continuous integration — `.github/workflows/`**

- `backend.yml`: matrix on Python 3.11/3.12 → install deps, `ruff check`,
  `pytest` with coverage upload.
- `frontend.yml`: install deps, `tsc --noEmit`, `eslint`, `vitest run`,
  `vite build`.
- `i18n-check.yml`: custom step that diffs locale JSON keys across
  languages — fails the PR if `de` is missing a key that exists in `en`
  (prevents silent untranslated strings).
- All workflows run on PR + on push to `main`.

**Issue tracking**

- File issues for every non-trivial scope decision in this plan (one per
  major feature: "Risk metrics module", "Value strategy", "i18n
  infrastructure", "Broker provider stub", etc.) so progress is visible
  on the repo's project board.
- Label scheme: `area/backend`, `area/frontend`, `area/data`, `type/bug`,
  `type/feat`, `good-first-issue`, `blocked`.

**Secrets & safety**

- No API keys committed — use `.env` (gitignored) for local dev and
  GitHub Actions secrets for CI.
- Dependabot enabled for both `pip` and `npm` ecosystems.

---

## Out of scope for MVP (named so we don't drift)

- Real-money execution (deferred to broker-integration milestone).
- Multi-user auth / cloud deploy (single local user only).
- Push/email alerts.
- Options, crypto, forex trading (equities + ETFs only).
- Tax-lot accounting (FIFO/LIFO/HIFO) — straight average cost only for now.
