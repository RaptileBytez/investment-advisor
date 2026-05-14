import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { describe, expect, it, vi, beforeEach } from "vitest";

import { TradeForm } from "../TradeForm";
import i18n from "@/i18n";

vi.mock("@/api/client", async () => {
  const actual = await vi.importActual<typeof import("@/api/client")>("@/api/client");
  return {
    ...actual,
    api: {
      ...actual.api,
      recordTrade: vi.fn().mockResolvedValue(undefined),
    },
  };
});

import { api, ApiError } from "@/api/client";

function renderForm(props = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <TradeForm {...props} />
    </QueryClientProvider>,
  );
}

describe("TradeForm", () => {
  beforeEach(async () => {
    vi.clearAllMocks();
    await i18n.changeLanguage("en");
  });

  it("rejects zero quantity locally", async () => {
    const user = userEvent.setup();
    renderForm();
    await user.type(screen.getByTestId("trade-ticker"), "AAPL");
    await user.type(screen.getByTestId("trade-quantity"), "0");
    await user.type(screen.getByTestId("trade-price"), "100");
    await user.click(screen.getByRole("button", { name: /save/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/quantity/i);
    expect(api.recordTrade).not.toHaveBeenCalled();
  });

  it("submits a valid trade and clears the inputs", async () => {
    const user = userEvent.setup();
    const onSuccess = vi.fn();
    renderForm({ onSuccess });
    await user.type(screen.getByTestId("trade-ticker"), "AAPL");
    await user.type(screen.getByTestId("trade-quantity"), "10");
    await user.type(screen.getByTestId("trade-price"), "150.25");
    await user.click(screen.getByRole("button", { name: /save/i }));
    await waitFor(() => expect(api.recordTrade).toHaveBeenCalledTimes(1));
    const args = (api.recordTrade as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0];
    expect(args.ticker).toBe("AAPL");
    expect(args.quantity).toBe(10);
    expect(args.price).toBe(150.25);
    expect(onSuccess).toHaveBeenCalled();
  });

  it("surfaces an oversell error from the backend", async () => {
    (api.recordTrade as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new ApiError(409, "cannot sell"),
    );
    const user = userEvent.setup();
    renderForm();
    await user.type(screen.getByTestId("trade-ticker"), "AAPL");
    await user.selectOptions(screen.getByTestId("trade-side"), "sell");
    await user.type(screen.getByTestId("trade-quantity"), "10");
    await user.type(screen.getByTestId("trade-price"), "100");
    await user.click(screen.getByRole("button", { name: /save/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/sell more shares/i);
  });
});
