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
      movers: vi.fn(),
    },
  };
});

import { api } from "@/api/client";
import { MoverList } from "../MoverList";

function renderList(props: { region?: string; kind: "gainers" | "losers" }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <MoverList {...props} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("MoverList", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage("en");
  });

  it("renders gainers with positive-tone styling", async () => {
    (api.movers as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        ticker: "SAP.DE",
        name: "SAP SE",
        exchange: "Xetra",
        region: "DE",
        currency: "EUR",
        price: 200,
        previous_close: 180,
        change: 20,
        change_pct: 0.111,
      },
    ]);
    renderList({ region: "DE", kind: "gainers" });
    await waitFor(() => expect(screen.getByText("SAP.DE")).toBeInTheDocument());
    // Find the change cell and confirm positive tone.
    const cells = screen.getAllByRole("cell");
    const changeCell = cells[cells.length - 1];
    expect(changeCell.className).toMatch(/text-positive/);
  });

  it("renders losers with negative-tone styling", async () => {
    (api.movers as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([
      {
        ticker: "BMW.DE",
        name: "BMW AG",
        exchange: "Xetra",
        region: "DE",
        currency: "EUR",
        price: 90,
        previous_close: 100,
        change: -10,
        change_pct: -0.1,
      },
    ]);
    renderList({ region: "DE", kind: "losers" });
    await waitFor(() => expect(screen.getByText("BMW.DE")).toBeInTheDocument());
    const cells = screen.getAllByRole("cell");
    const changeCell = cells[cells.length - 1];
    expect(changeCell.className).toMatch(/text-negative/);
  });

  it("shows an empty state when no movers come back", async () => {
    (api.movers as unknown as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    renderList({ kind: "gainers" });
    expect(await screen.findByText(/No movers available/i)).toBeInTheDocument();
  });
});
