import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Combine and de-duplicate Tailwind class names. */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
