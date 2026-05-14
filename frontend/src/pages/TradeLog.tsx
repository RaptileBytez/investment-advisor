import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { ApiError } from "@/api/client";
import { Card } from "@/components/Card";
import { TradeForm } from "@/components/TradeForm";
import { formatCurrency, formatDate } from "@/lib/format";

interface TransactionRow {
  id: number;
  ticker: string;
  side: string;
  quantity: number;
  price: number;
  fees: number;
  currency: string;
  executed_at: string;
  note: string | null;
}

export default function TradeLog() {
  const { t } = useTranslation("common");

  const txs = useQuery<TransactionRow[]>({
    queryKey: ["transactions"],
    queryFn: async () => {
      const res = await fetch("/api/portfolio/transactions");
      if (!res.ok) throw new ApiError(res.status, await res.text());
      return (await res.json()) as TransactionRow[];
    },
  });

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">{t("nav.trade_log")}</h1>
      </header>

      <Card title={t("actions.log_trade")}>
        <TradeForm onSuccess={() => txs.refetch()} />
      </Card>

      <Card title="History">
        {txs.isLoading && <p className="text-sm text-foreground/60">Loading…</p>}
        {txs.isError && <p className="text-sm text-negative">Could not load transactions.</p>}
        {txs.data && txs.data.length === 0 && (
          <p className="text-sm text-foreground/70">No trades yet.</p>
        )}
        {txs.data && txs.data.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-foreground/60">
                  <th className="py-1">Date</th>
                  <th className="py-1">Ticker</th>
                  <th className="py-1">Side</th>
                  <th className="py-1 text-right">Qty</th>
                  <th className="py-1 text-right">Price</th>
                  <th className="py-1 text-right">Fees</th>
                  <th className="py-1">Note</th>
                </tr>
              </thead>
              <tbody>
                {txs.data.map((tx) => (
                  <tr key={tx.id} className="border-t border-border">
                    <td className="py-2">{formatDate(tx.executed_at)}</td>
                    <td className="py-2">
                      <Link
                        to={`/stocks/${encodeURIComponent(tx.ticker)}`}
                        className="font-medium text-accent hover:underline"
                      >
                        {tx.ticker}
                      </Link>
                    </td>
                    <td
                      className={`py-2 ${tx.side === "buy" ? "text-positive" : "text-negative"}`}
                    >
                      {t(`actions.${tx.side as "buy" | "sell"}`)}
                    </td>
                    <td className="py-2 text-right font-mono">{tx.quantity}</td>
                    <td className="py-2 text-right font-mono">
                      {formatCurrency(tx.price, tx.currency)}
                    </td>
                    <td className="py-2 text-right font-mono">
                      {formatCurrency(tx.fees, tx.currency)}
                    </td>
                    <td className="py-2 text-foreground/70">{tx.note ?? ""}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
