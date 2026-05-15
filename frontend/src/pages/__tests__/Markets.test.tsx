import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
      me: vi.fn().mockResolvedValue({
        id: 1, email: "x@y", base_currency: "USD", locale: "en", risk_tolerance: "balanced",
      }),
      indices: vi.fn().mockResolvedValue([
        {
          ticker: "^GSPC", name: "S&P 500", region: "US", price: 5200,
          previous_close: 5100, change: 100, change_pct: 0.0196, currency: "USD",
        },
      ]),
      topPicks: vi.fn().mockResolvedValue([
        {
          ticker: "AAPL", name: "Apple Inc.", exchange: "NYSE/Nasdaq", region: "US",
          currency: "USD", price: 200, change_pct: 0.01, action: "buy",
          confidence: 0.87, rationale: "Strong momentum and trend.", score: 0.8,
        },
      ]),
      movers: vi.fn().mockResolvedValue([
        {
          ticker: "NVDA", name: "NVIDIA Corporation", exchange: "NYSE/Nasdaq", region: "US",
          currency: "USD", price: 1000, previous_close: 900, change: 100, change_pct: 0.111,
        },
      ]),
    },
  };
});

import Markets from "../Markets";

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <Markets />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Markets page", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("renders indices ribbon and Top Picks by default", async () => {
    renderPage();
    expect(await screen.findByText("S&P 500")).toBeInTheDocument();
    expect(await screen.findByText("AAPL")).toBeInTheDocument();
    expect(screen.getByText("Strong momentum and trend.")).toBeInTheDocument();
  });

  it("switches to the Top Movers tab", async () => {
    const user = userEvent.setup();
    renderPage();
    await user.click(screen.getByTestId("tab-movers"));
    expect(await screen.findByText("NVDA")).toBeInTheDocument();
  });

  it("region filter updates the API call", async () => {
    const user = userEvent.setup();
    const { api: mockedApi } = await import("@/api/client");
    renderPage();
    await waitFor(() => expect(screen.getByTestId("market-region-filter")).toBeInTheDocument());
    await user.selectOptions(screen.getByTestId("market-region-filter"), "de");
    // After selecting DE, the next topPicks call should have region "DE".
    await waitFor(() => {
      const calls = (mockedApi.topPicks as unknown as ReturnType<typeof vi.fn>).mock.calls;
      const lastArgs = calls[calls.length - 1]?.[0];
      expect(lastArgs?.region).toBe("DE");
    });
  });

  it("relocalises to German when the language switches", async () => {
    await i18n.changeLanguage("de");
    renderPage();
    expect(await screen.findByText("Märkte")).toBeInTheDocument();
    expect(screen.getByText("Top-Empfehlungen")).toBeInTheDocument();
  });
});
