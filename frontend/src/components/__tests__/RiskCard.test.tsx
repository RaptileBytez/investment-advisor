import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, beforeEach } from "vitest";

import { RiskCard } from "../RiskCard";
import i18n from "@/i18n";

const sample = {
  volatility: 0.225,
  sharpe: 1.42,
  beta: 1.05,
  max_drawdown: -0.32,
  value_at_risk_95: 0.034,
  benchmark: "S&P 500",
  risk_free_rate: 0.045,
};

function renderWithProviders(ui: React.ReactNode) {
  const client = new QueryClient();
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RiskCard", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("renders every metric row with localised labels", () => {
    renderWithProviders(<RiskCard risk={sample} />);
    expect(screen.getByText("Volatility")).toBeInTheDocument();
    expect(screen.getByText("Sharpe ratio")).toBeInTheDocument();
    expect(screen.getByText("Beta (β)")).toBeInTheDocument();
    expect(screen.getByText("Max drawdown")).toBeInTheDocument();
    expect(screen.getByText("Value at Risk (95%)")).toBeInTheDocument();
    expect(screen.getByText("Risk-free rate")).toBeInTheDocument();
  });

  it("formats values via Intl (English locale uses period as decimal)", () => {
    renderWithProviders(<RiskCard risk={sample} />);
    // 0.225 → "22.5%", 1.42 → "1.42", etc.
    expect(screen.getByText("22.5%")).toBeInTheDocument();
    expect(screen.getByText("1.42")).toBeInTheDocument();
  });

  it("shows the benchmark in the card header", () => {
    renderWithProviders(<RiskCard risk={sample} />);
    expect(screen.getByText(/S&P 500/)).toBeInTheDocument();
  });
});
