# Backend — Investment Advisor

FastAPI service powering the Investment Advisor: data ingestion, risk math,
strategies, portfolio tracking, and the glossary API.

## Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Optional — only if pandas-ta has a wheel for your Python version:
pip install -e ".[indicators]"
```

On Linux/macOS substitute `source .venv/bin/activate`.

## Configuration

Copy `.env.example` to `.env` and edit:

```powershell
Copy-Item .env.example .env
```

| Variable        | Default                     | Purpose                            |
| --------------- | --------------------------- | ---------------------------------- |
| `DATABASE_URL`  | `sqlite:///./data/app.db`   | SQLAlchemy connection string       |
| `DATA_PROVIDER` | `yfinance`                  | Market-data provider key           |
| `BASE_CURRENCY` | `EUR`                       | Default base currency for users    |
| `LOCALE`        | `en`                        | Default UI language code           |
| `CACHE_DIR`     | `./data/cache`              | On-disk cache for history requests |
| `LOG_LEVEL`     | `INFO`                      | Standard Python log level          |

## Running

```powershell
# First-time DB setup
alembic upgrade head

# Dev server
uvicorn app.main:app --reload
```

API docs: <http://127.0.0.1:8000/docs>.

## Testing

```powershell
pytest                  # all tests
pytest -m "not integration"   # skip tests that hit yfinance
pytest --cov=app        # with coverage report
ruff check .            # lint
ruff format .           # auto-format
```

## Layout

See [docs/plan.md](../docs/plan.md) in the repo root for the full
architecture. High-level:

```
app/
├── api/            # FastAPI routers (one file per resource)
├── core/           # config, logging, cache
├── data/           # provider interface + concrete providers (yfinance, …)
├── db/             # SQLAlchemy models + session
├── glossary/       # markdown content for financial terms (en/, de/, …)
├── portfolio/      # holdings, transactions, valuation
├── recommendation/ # strategy + risk → final verdict
├── risk/           # metrics, region benchmarks & risk-free rates
└── strategies/     # buy_hold, dca, value, momentum
```
