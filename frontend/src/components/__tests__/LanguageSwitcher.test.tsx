import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, beforeEach } from "vitest";

import { LanguageSwitcher } from "../LanguageSwitcher";
import i18n from "@/i18n";

describe("LanguageSwitcher", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
  });

  it("renders English option labels by default", () => {
    render(<LanguageSwitcher />);
    expect(screen.getByLabelText(/language/i)).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /english/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /german/i })).toBeInTheDocument();
  });

  it("switches the active language on select change", async () => {
    const user = userEvent.setup();
    render(<LanguageSwitcher />);
    const combo = screen.getByLabelText(/language/i) as HTMLSelectElement;
    await user.selectOptions(combo, "de");
    expect(i18n.resolvedLanguage).toBe("de");
  });
});
