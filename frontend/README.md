# Frontend — Investment Advisor

React + TypeScript + Vite single-page app that talks to the FastAPI
backend over `/api/*`. Tailwind for styling, `react-i18next` for
English + German UI, TradingView `lightweight-charts` for stock charts
(wired in phase 2).

## Setup

```powershell
cd frontend
npm install
npm run dev
```

Then open <http://localhost:5173>. The dev server proxies `/api/*` to
`http://127.0.0.1:8000`, so the backend must be running.

## Scripts

| Command            | Purpose                            |
| ------------------ | ---------------------------------- |
| `npm run dev`      | Vite dev server with HMR.          |
| `npm run build`    | Type-check then production build.  |
| `npm run preview`  | Serve the production build.        |
| `npm run lint`     | ESLint on `src/`.                  |
| `npm run typecheck`| `tsc --noEmit`.                    |
| `npm run test`     | Vitest (jsdom + RTL).              |

## Project layout

```
src/
├── api/         # typed fetch client mirroring backend schemas
├── components/  # shared UI (LanguageSwitcher, Layout, charts …)
├── i18n/        # i18next config + locale JSON files
│   └── locales/
│       ├── en/
│       └── de/
├── lib/         # utilities (cn, formatters …)
├── pages/       # one component per route
└── test/        # vitest setup
```

## Internationalisation

Every user-facing string flows through `useTranslation("…")`. Locale
files are split into namespaces (`common`, `errors`, `glossary`, `risk`,
`strategies`) so the bundle can lazy-load namespaces later.

To add a language:

1. Drop a `src/i18n/locales/<code>/` folder mirroring `en/`'s files.
2. Add `<code>` to `SUPPORTED_LANGUAGES` in `src/i18n/index.ts`.
3. The backend already serves glossary content per language — drop
   matching markdown files into `backend/app/glossary/entries/<code>/`.
