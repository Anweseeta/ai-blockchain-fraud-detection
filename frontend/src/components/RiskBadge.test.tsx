import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PredictionBadge, RiskBadge } from "./RiskBadge";

describe("RiskBadge", () => {
  it.each(["HIGH", "MEDIUM", "LOW"] as const)("renders %s with text and icon, not color alone", (level) => {
    render(<RiskBadge level={level} />);
    const el = screen.getByRole("status");
    expect(el).toHaveTextContent(level);
    expect(el).toHaveAttribute("aria-label", expect.stringContaining("risk"));
  });
});

describe("PredictionBadge", () => {
  it("labels fraud vs legitimate in words", () => {
    const { rerender } = render(<PredictionBadge value="FRAUD" />);
    expect(screen.getByRole("status")).toHaveTextContent("FRAUD");
    rerender(<PredictionBadge value="LEGITIMATE" />);
    expect(screen.getByRole("status")).toHaveTextContent("LEGITIMATE");
  });
});
