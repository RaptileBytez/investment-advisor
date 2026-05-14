/** Typed fetch wrapper for the backend REST API. */

export interface UserOut {
  id: number;
  email: string;
  base_currency: string;
  locale: string;
  risk_tolerance: "conservative" | "balanced" | "aggressive";
}

export interface QuoteOut {
  ticker: string;
  price: number;
  currency: string;
  timestamp: string;
  previous_close: number | null;
  change: number | null;
  change_pct: number | null;
}

export interface HistoryBar {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface HistoryOut {
  ticker: string;
  period: string;
  interval: string;
  bars: HistoryBar[];
}

export interface RiskSummaryOut {
  volatility: number;
  sharpe: number;
  beta: number;
  max_drawdown: number;
  value_at_risk_95: number;
  benchmark: string;
  risk_free_rate: number;
}

export interface StrategyResultOut {
  strategy: string;
  ticker: string;
  verdict: "buy" | "hold" | "sell" | "watch";
  score: number;
  rationale: string;
  key_inputs: Record<string, number | string | null>;
}

export interface VerdictOut {
  ticker: string;
  action: "buy" | "hold" | "sell" | "watch";
  confidence: number;
  rationale: string;
  risk_summary: RiskSummaryOut | null;
  strategy_results: StrategyResultOut[];
}

export interface HoldingOut {
  ticker: string;
  quantity: number;
  avg_cost: number;
  currency: string;
}

export interface PositionValuationOut {
  ticker: string;
  quantity: number;
  avg_cost: number;
  currency: string;
  current_price: number;
  market_value: number;
  cost_basis: number;
  unrealized_pl: number;
  unrealized_pl_pct: number;
  weight: number;
}

export interface PortfolioValuationOut {
  base_currency: string;
  total_value: number;
  total_cost_basis: number;
  total_unrealized_pl: number;
  total_unrealized_pl_pct: number;
  concentration_hhi: number;
  currency_exposure: Record<string, number>;
  positions: PositionValuationOut[];
}

export interface GlossarySummary {
  key: string;
  title: string;
  short: string;
  language: string;
  language_fallback: boolean;
}

export interface GlossaryEntry extends GlossarySummary {
  body_html: string;
  related: string[];
}

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, text || response.statusText);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export const api = {
  // ── user / preferences ──
  me: () => request<UserOut>("/api/portfolio/me"),
  updatePreferences: (body: Partial<Pick<UserOut, "base_currency" | "locale" | "risk_tolerance">>) =>
    request<UserOut>("/api/portfolio/me", { method: "PUT", body: JSON.stringify(body) }),

  // ── stocks ──
  searchTickers: (q: string, region?: string) =>
    request<Array<{ ticker: string; name: string; exchange: string; region: string; currency: string }>>(
      `/api/stocks/search?q=${encodeURIComponent(q)}${region ? `&region=${region}` : ""}`,
    ),
  quote: (ticker: string) => request<QuoteOut>(`/api/stocks/quote/${encodeURIComponent(ticker)}`),
  history: (ticker: string, period = "1y", interval = "1d") =>
    request<HistoryOut>(
      `/api/stocks/history/${encodeURIComponent(ticker)}?period=${period}&interval=${interval}`,
    ),

  // ── portfolio ──
  holdings: () => request<HoldingOut[]>("/api/portfolio/holdings"),
  valuation: () => request<PortfolioValuationOut>("/api/portfolio/valuation"),
  recordTrade: (body: {
    ticker: string;
    side: "buy" | "sell";
    quantity: number;
    price: number;
    executed_at: string;
    fees?: number;
    note?: string;
  }) => request("/api/portfolio/trades", { method: "POST", body: JSON.stringify(body) }),

  // ── strategies ──
  listStrategies: () => request<string[]>("/api/strategies"),
  evaluate: (body: {
    ticker: string;
    strategies?: string[];
    strategy_weights?: Record<string, number>;
    risk_tolerance?: "conservative" | "balanced" | "aggressive";
    history_period?: string;
  }) => request<VerdictOut>("/api/strategies/evaluate", { method: "POST", body: JSON.stringify(body) }),

  // ── risk ──
  risk: (ticker: string, period = "5y") =>
    request<RiskSummaryOut>(`/api/risk/${encodeURIComponent(ticker)}?period=${period}`),

  // ── glossary ──
  glossaryList: (lang: string) =>
    request<GlossarySummary[]>(`/api/glossary?lang=${encodeURIComponent(lang)}`),
  glossaryEntry: (key: string, lang: string) =>
    request<GlossaryEntry>(`/api/glossary/${encodeURIComponent(key)}?lang=${encodeURIComponent(lang)}`),
};
