import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { ExplainTooltip } from "../ExplainTooltip";
import i18n from "@/i18n";

vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>("@/api/client");
  return {
    ...actual,
    api: {
      ...actual.api,
      glossaryEntry: vi.fn().mockResolvedValue({
        key: "sharpe-ratio",
        title: "Sharpe Ratio",
        short: "Risk-adjusted return per unit of volatility.",
        body_html: "<p>…</p>",
        related: [],
        language: "en",
        language_fallback: false,
      }),
    },
  };
});

import { api } from "@/api/client";

function renderTip() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ExplainTooltip termKey="sharpe-ratio">Sharpe ratio</ExplainTooltip>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ExplainTooltip", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage("en");
  });

  it("renders the label and the info button", () => {
    renderTip();
    expect(screen.getByText("Sharpe ratio")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /what is sharpe-ratio/i })).toBeInTheDocument();
  });

  it("fetches and shows the glossary short on hover", async () => {
    const user = userEvent.setup();
    renderTip();
    await user.hover(screen.getByRole("button"));
    await waitFor(() =>
      expect(screen.getByText(/Risk-adjusted return per unit of volatility/i)).toBeInTheDocument(),
    );
    expect(api.glossaryEntry).toHaveBeenCalledWith("sharpe-ratio", "en");
  });
});
