import { render, screen } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";

import { VerdictBadge } from "../VerdictBadge";
import i18n from "@/i18n";

describe("VerdictBadge", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("renders the localized BUY label", () => {
    render(<VerdictBadge verdict="buy" />);
    expect(screen.getByLabelText(/Verdict Buy/i)).toBeInTheDocument();
  });

  it("shows the rationale and confidence when given", () => {
    render(<VerdictBadge verdict="hold" confidence={0.72} rationale="Mixed signals." />);
    expect(screen.getByText("Mixed signals.")).toBeInTheDocument();
    expect(screen.getByText("72 / 100")).toBeInTheDocument();
  });

  it("applies the negative-tone classes for SELL", () => {
    render(<VerdictBadge verdict="sell" />);
    const badge = screen.getByLabelText(/Verdict Sell/i);
    expect(badge.className).toMatch(/text-negative/);
  });

  it("localises to German when the language changes", async () => {
    await i18n.changeLanguage("de");
    render(<VerdictBadge verdict="buy" />);
    // The aria-label uses the English fixed prefix; the visible label is German.
    expect(screen.getByText("Kaufen")).toBeInTheDocument();
  });
});
