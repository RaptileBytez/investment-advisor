import { useTranslation } from "react-i18next";

import { cn } from "@/lib/utils";

export type VerdictAction = "buy" | "hold" | "sell" | "watch";

interface VerdictBadgeProps {
  verdict: VerdictAction;
  confidence?: number;        // 0..1
  rationale?: string;
  className?: string;
}

const COLOR: Record<VerdictAction, string> = {
  buy:   "bg-positive/10  text-positive  border-positive/30",
  hold:  "bg-muted        text-foreground/80 border-border",
  sell:  "bg-negative/10  text-negative  border-negative/30",
  watch: "bg-accent/10    text-accent    border-accent/30",
};

export function VerdictBadge({ verdict, confidence, rationale, className }: VerdictBadgeProps) {
  const { t } = useTranslation("common");
  const label = t(`verdict.${verdict}` as const);

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-center gap-3">
        <span
          aria-label={t("verdict.aria", { action: label })}
          className={cn(
            "inline-flex items-center gap-2 rounded-full border px-3 py-1 text-sm font-medium",
            COLOR[verdict],
          )}
        >
          <span aria-hidden className="inline-block h-2 w-2 rounded-full bg-current" />
          {label}
        </span>
        {typeof confidence === "number" && (
          <span className="text-xs text-foreground/60">
            {(confidence * 100).toFixed(0)} / 100
          </span>
        )}
      </div>
      {rationale && <p className="text-sm leading-relaxed text-foreground/80">{rationale}</p>}
    </div>
  );
}
