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
    expect(screen.getByLabelText(/Verdict:\s*Buy/i)).toBeInTheDocument();
  });

  it("shows the rationale and confidence when given", () => {
    render(<VerdictBadge verdict="hold" confidence={0.72} rationale="Mixed signals." />);
    expect(screen.getByText("Mixed signals.")).toBeInTheDocument();
    expect(screen.getByText("72 / 100")).toBeInTheDocument();
  });

  it("applies the negative-tone classes for SELL", () => {
    render(<VerdictBadge verdict="sell" />);
    const badge = screen.getByLabelText(/Verdict:\s*Sell/i);
    expect(badge.className).toMatch(/text-negative/);
  });

  it("localises to German when the language changes", async () => {
    await i18n.changeLanguage("de");
    render(<VerdictBadge verdict="buy" />);
    // Both the visible label *and* the aria-label prefix now localise.
    expect(screen.getByText("Kaufen")).toBeInTheDocument();
    expect(screen.getByLabelText(/Empfehlung:\s*Kaufen/i)).toBeInTheDocument();
  });
});
