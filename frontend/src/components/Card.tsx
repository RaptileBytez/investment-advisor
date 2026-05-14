import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "@/lib/utils";

interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, "title"> {
  title?: ReactNode;
  trailing?: ReactNode;
}

export function Card({ title, trailing, className, children, ...rest }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-background shadow-sm",
        className,
      )}
      {...rest}
    >
      {(title || trailing) && (
        <div className="flex items-center justify-between border-b border-border px-4 py-2">
          <h3 className="text-sm font-medium tracking-tight">{title}</h3>
          {trailing && <div className="text-sm text-foreground/60">{trailing}</div>}
        </div>
      )}
      <div className="p-4">{children}</div>
    </div>
  );
}
