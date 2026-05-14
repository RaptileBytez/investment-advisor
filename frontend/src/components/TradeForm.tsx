/**
 * TradeForm — record a paper-trading buy/sell.
 *
 * Pure controlled form. On submit, posts to /api/portfolio/trades via the
 * api client. Surfaces validation errors locally (quantity > 0, price ≥ 0)
 * and any backend error inline (oversell, 5xx, …).
 *
 * Convenience: Price is auto-filled from the historical close of the chosen
 * execution date (yfinance via /api/stocks/history), and Fees is computed
 * as a small percentage of the trade value. Both fields remain user-
 * editable — the moment you type into either, auto-population stops for
 * that field for the rest of the form's life.
 */

import { type FormEvent, useEffect, useRef, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";

import { api, ApiError } from "@/api/client";
import { cn } from "@/lib/utils";

interface TradeFormProps {
  defaultTicker?: string;
  onSuccess?: () => void;
  className?: string;
}

// Conservative default for European discount brokers (≈0.25 %). Users can
// override — fee structures are broker-specific and we don't want to
// pretend we know what they pay.
const DEFAULT_FEE_RATE = 0.0025;

export function TradeForm({ defaultTicker = "", onSuccess, className }: TradeFormProps) {
  const { t } = useTranslation(["common", "errors"]);
  const queryClient = useQueryClient();

  const [ticker, setTicker] = useState(defaultTicker);
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [quantity, setQuantity] = useState<string>("");
  const [price, setPrice] = useState<string>("");
  const [executedAt, setExecutedAt] = useState<string>(
    new Date().toISOString().slice(0, 10),
  );
  const [fees, setFees] = useState<string>("");
  const [note, setNote] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const priceTouched = useRef(false);
  const feesTouched = useRef(false);

  const mutation = useMutation({
    mutationFn: () =>
      api.recordTrade({
        ticker: ticker.trim(),
        side,
        quantity: Number(quantity),
        price: Number(price),
        executed_at: new Date(`${executedAt}T00:00:00Z`).toISOString(),
        fees: Number(fees) || 0,
        note: note.trim() || undefined,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["holdings"] });
      void queryClient.invalidateQueries({ queryKey: ["valuation"] });
      void queryClient.invalidateQueries({ queryKey: ["transactions"] });
      setQuantity("");
      setPrice("");
      setFees("");
      setNote("");
      priceTouched.current = false;
      feesTouched.current = false;
      onSuccess?.();
    },
    onError: (err) => {
      if (err instanceof ApiError && err.status === 409) {
        setError(t("errors:trade_validation.oversell"));
      } else if (err instanceof ApiError) {
        setError(err.message || t("errors:generic"));
      } else {
        setError(t("errors:generic"));
      }
    },
  });

  // ── Auto-fill Price from historical close for the executed_at date ──
  useEffect(() => {
    if (priceTouched.current) return;
    const symbol = ticker.trim();
    if (!symbol || !executedAt) return;
    const timer = setTimeout(async () => {
      try {
        const hist = await api.history(symbol, "5y", "1d");
        const matched = [...hist.bars].filter((b) => b.date <= executedAt).pop();
        if (matched && !priceTouched.current) {
          setPrice(matched.close.toFixed(2));
        }
      } catch {
        // silent — user can fill in manually
      }
    }, 300); // debounce so we don't fire on every keystroke when typing the ticker
    return () => clearTimeout(timer);
  }, [ticker, executedAt]);

  // ── Auto-compute Fees from quantity × price × default rate ──
  useEffect(() => {
    if (feesTouched.current) return;
    const q = Number(quantity);
    const p = Number(price);
    if (!Number.isFinite(q) || q <= 0 || !Number.isFinite(p) || p <= 0) return;
    setFees((q * p * DEFAULT_FEE_RATE).toFixed(2));
  }, [quantity, price]);

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const q = Number(quantity);
    const p = Number(price);
    if (!Number.isFinite(q) || q <= 0) {
      setError(t("errors:trade_validation.quantity_required"));
      return;
    }
    if (!Number.isFinite(p) || p < 0) {
      setError(t("errors:trade_validation.price_required"));
      return;
    }
    if (!ticker.trim()) return;
    mutation.mutate();
  }

  return (
    <form onSubmit={handleSubmit} className={cn("space-y-3", className)} aria-label="Trade form">
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="Ticker">
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value.toUpperCase())}
            required
            placeholder="AAPL"
            className={inputCls}
            data-testid="trade-ticker"
          />
        </Field>
        <Field label={t("common:actions.buy") + " / " + t("common:actions.sell")}>
          <select
            value={side}
            onChange={(e) => setSide(e.target.value as "buy" | "sell")}
            className={inputCls}
            data-testid="trade-side"
          >
            <option value="buy">{t("common:actions.buy")}</option>
            <option value="sell">{t("common:actions.sell")}</option>
          </select>
        </Field>
        <Field label="Quantity">
          <input
            type="number"
            step="any"
            min="0"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            required
            className={inputCls}
            data-testid="trade-quantity"
          />
        </Field>
        <Field
          label="Price"
          hint={priceTouched.current ? undefined : "auto-filled from history; edit to override"}
        >
          <input
            type="number"
            step="any"
            min="0"
            value={price}
            onChange={(e) => {
              priceTouched.current = true;
              setPrice(e.target.value);
            }}
            required
            className={inputCls}
            data-testid="trade-price"
          />
        </Field>
        <Field label="Executed">
          <input
            type="date"
            value={executedAt}
            onChange={(e) => setExecutedAt(e.target.value)}
            required
            className={inputCls}
          />
        </Field>
        <Field
          label="Fees"
          hint={
            feesTouched.current
              ? undefined
              : `auto: ${(DEFAULT_FEE_RATE * 100).toFixed(2)}% of trade value`
          }
        >
          <input
            type="number"
            step="any"
            min="0"
            value={fees}
            onChange={(e) => {
              feesTouched.current = true;
              setFees(e.target.value);
            }}
            className={inputCls}
            data-testid="trade-fees"
          />
        </Field>
      </div>
      <Field label="Note">
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          maxLength={500}
          className={inputCls}
          placeholder="Optional"
        />
      </Field>

      {error && (
        <p
          role="alert"
          className="rounded-md border border-negative/30 bg-negative/10 px-3 py-2 text-sm text-negative"
        >
          {error}
        </p>
      )}

      <div className="flex justify-end gap-2">
        <button
          type="submit"
          disabled={mutation.isPending}
          className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {mutation.isPending ? "…" : t("common:actions.save")}
        </button>
      </div>
    </form>
  );
}

const inputCls =
  "w-full rounded-md border border-border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent";

function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs text-foreground/60">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-[10px] text-foreground/50">{hint}</span>}
    </label>
  );
}
