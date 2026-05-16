import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

import i18n from "@/i18n";

vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>("@/api/client");
  return {
    ...actual,
    api: {
      ...actual.api,
      valuation: vi.fn().mockResolvedValue({
        base_currency: "EUR",
        total_value: 1234.56,
        total_cost_basis: 1000,
        total_unrealized_pl: 234.56,
        total_unrealized_pl_pct: 0.23,
        concentration_hhi: 0.3,
        currency_exposure: { EUR: 1.0 },
        positions: [
          {
            ticker: "SAP.DE",
            quantity: 10,
            avg_cost: 100,
            currency: "EUR",
            current_price: 120,
            market_value: 1200,
            cost_basis: 1000,
            unrealized_pl: 200,
            unrealized_pl_pct: 0.2,
            weight: 1.0,
          },
        ],
      }),
    },
  };
});

import Portfolio from "../Portfolio";

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Portfolio />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Portfolio table i18n (regression: issue #3)", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("renders English table headers in English mode", async () => {
    renderPage();
    await waitFor(() => expect(screen.getByText("SAP.DE")).toBeInTheDocument());
    expect(screen.getByRole("columnheader", { name: "Ticker" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Qty" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Avg cost" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Market value" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Weight" })).toBeInTheDocument();
  });

  it("renders German table headers in German mode", async () => {
    await i18n.changeLanguage("de");
    renderPage();
    await waitFor(() => expect(screen.getByText("SAP.DE")).toBeInTheDocument());
    // Each was hardcoded English before this fix — the failure modes the
    // issue reported.
    expect(screen.getByRole("columnheader", { name: "Stück" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Ø-Kosten" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Marktwert" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Gewicht" })).toBeInTheDocument();
    // Card titles must also relocalise.
    expect(screen.getByText("Gesamtwert")).toBeInTheDocument();
    expect(screen.getByText("Positionen")).toBeInTheDocument();
    expect(screen.getByText("Währungsexposure")).toBeInTheDocument();
  });
});
