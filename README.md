# Investment Advisor

A personal, web-based investment-advisor app. Monitors stock markets, tracks
your portfolio, computes risk metrics, and suggests **Buy more / Hold / Sell**
actions across multiple strategies. International-market aware (US + Europe)
with English and German UI.

> **Disclaimer.** This software is for educational and informational purposes
> only. It does not constitute financial advice. Past performance is not
> indicative of future results. You alone are responsible for your investment
> decisions.

## Status

🚧 **Pre-MVP.** Currently scaffolding the project structure. See
[docs/plan.md](docs/plan.md) for the full implementation plan.

## Features (MVP)

- 📈 Interactive price charts for any supported stock (US + European markets)
- 🧮 Risk metrics (volatility, Sharpe, beta, max drawdown, VaR) with
  region-appropriate benchmarks
- 🧠 Four investment strategies out of the box:
  - Buy & Hold
  - Dollar-Cost Averaging (DCA)
  - Value investing
  - Momentum / trend following
- 💼 Portfolio tracking with **Buy more / Hold / Sell** verdicts per position
- 📝 Paper-trading trade log (broker API integration planned)
- 🌍 Multi-currency, multi-locale (EUR/USD/GBP and beyond)
- 🇬🇧🇩🇪 English & German UI; new languages drop in as a folder
- 📚 Inline explanations for every metric, term, and strategy

## Tech stack

| Layer    | Tools                                                              |
| -------- | ------------------------------------------------------------------ |
| Backend  | Python 3.11+, FastAPI, SQLAlchemy, Pydantic                        |
| Quant    | `pandas`, `numpy`, `scipy`, `yfinance`, `pandas-ta`                |
| DB       | SQLite (file-local), Alembic migrations                            |
| Frontend | React + TypeScript + Vite                                          |
| UI       | Tailwind CSS + shadcn/ui                                           |
| Charts   | TradingView `lightweight-charts`                                   |
| i18n     | `react-i18next` + browser `Intl`                                   |
| Tests    | `pytest` (backend), `vitest` + React Testing Library (frontend)    |

## Quickstart

### Backend

```bash
cd backend
python -m venv .venv
# Windows:   .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Then open <http://localhost:5173>.

## Project structure

```
investment-advisor/
├── backend/     # FastAPI app, strategies, risk math, data providers
├── frontend/    # React + TypeScript SPA
├── docs/        # Plans and design notes
└── .github/     # CI workflows, issue & PR templates
```

See [docs/plan.md](docs/plan.md) for the full architecture.

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md) for branch and commit conventions,
test commands, and the development workflow.

## License

Apache License 2.0 — see [LICENSE](LICENSE).
