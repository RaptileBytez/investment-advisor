# Contributing

Thanks for your interest. This document covers the workflow, conventions,
and quality bars for contributing to the Investment Advisor.

## Workflow

1. Open (or pick up) an issue describing the change. Confirm scope before
   writing code for anything non-trivial.
2. Branch from `main`:
   - `feat/<scope>` — new feature
   - `fix/<scope>` — bug fix
   - `chore/<scope>` — tooling, deps, CI
   - `docs/<scope>` — docs only
   - `refactor/<scope>` — no behavior change
3. Keep branches short-lived. Rebase, don't merge `main` in.
4. Open a Pull Request. CI must be green before merge.
5. Use **squash merge** to keep `main` history linear and readable.

## Commits — Conventional Commits

Format: `type(optional-scope): short imperative description`

Types: `feat`, `fix`, `chore`, `docs`, `test`, `refactor`, `perf`, `ci`,
`build`, `style`.

Examples:

```
feat(strategies): add momentum strategy with RSI signal
fix(risk): correct annualization factor for volatility
docs(readme): add quickstart for backend
ci(i18n): fail PR when DE locale missing keys from EN
```

If a change is breaking, append `!`: `feat(api)!: rename /holdings to /positions`.

## Running tests

### Backend

```bash
cd backend
pytest                  # all tests
pytest --cov=app        # with coverage
ruff check .            # lint
ruff format .           # auto-format
```

### Frontend

```bash
cd frontend
npm run test            # vitest
npm run lint            # eslint
npm run typecheck       # tsc --noEmit
npm run build           # vite build (must succeed)
```

### Before opening a PR

- [ ] Tests pass locally for the area you touched.
- [ ] New behavior covered by a test.
- [ ] If you added user-facing text: every string goes through `t("…")` and
      both `en/` and `de/` locale files are updated.
- [ ] If you added a financial metric / signal: a glossary entry exists in
      both `en/` and `de/`.
- [ ] No secrets or `.env` files committed.
- [ ] Updated relevant docs (`README.md`, `docs/`).

## Internationalization rules

- **No hardcoded strings** in `frontend/src/**` — use `t("namespace:key")`.
- Long-form content (glossary, strategy explainers) lives in
  `backend/app/glossary/entries/<lang>/<term>.md`.
- When adding a key to `en/`, you **must** add it to `de/` in the same PR
  (CI enforces this).

## Reporting bugs / requesting features

Use the issue templates in [`.github/ISSUE_TEMPLATE/`](.github/ISSUE_TEMPLATE/).
For security issues, see [SECURITY.md](SECURITY.md) — do not open a public
issue.

## Code style

- Python: `ruff` (lint + format), type hints required on public APIs.
- TypeScript: `eslint` + `prettier`, no `any` without a justifying comment.
- Keep functions small and named. Comments only when the *why* is non-obvious.
