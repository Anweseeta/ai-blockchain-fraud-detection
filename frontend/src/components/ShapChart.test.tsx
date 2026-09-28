import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import type { ShapFactor } from "../types";
import { ShapChart } from "./ShapChart";

const FACTORS: ShapFactor[] = [
  { feature: "Unique Received From Addresses", value: "26", shap_value: 3.65, direction: "increases_risk", explanation_type: "model_contribution" },
  { feature: "Time Diff between first and last (Mins)", value: "100", shap_value: -1.2, direction: "decreases_risk", explanation_type: "model_contribution" },
];

describe("ShapChart", () => {
  it("separates increasing and decreasing factors and uses real values", () => {
    render(<ShapChart factors={FACTORS} />);
    expect(screen.getByText(/factors increasing/i)).toBeInTheDocument();
    expect(screen.getByText(/factors decreasing/i)).toBeInTheDocument();
    expect(screen.getByText("Unique Received From Addresses")).toBeInTheDocument();
    expect(screen.getByText("+3.650")).toBeInTheDocument();
  });

  it("labels output as model contribution, not causation", () => {
    render(<ShapChart factors={FACTORS} />);
    expect(screen.getByText(/model contribution, not causation/i)).toBeInTheDocument();
    expect(screen.queryByText(/proves fraud/i)).not.toBeInTheDocument();
  });

  it("tooltip shows feature, value, contribution and direction", async () => {
    const user = userEvent.setup();
    render(<ShapChart factors={FACTORS} />);
    await user.hover(screen.getByText("Unique Received From Addresses"));
    expect(screen.getByText("Input value")).toBeInTheDocument();
    expect(screen.getByText("SHAP contribution")).toBeInTheDocument();
    expect(screen.getByText(/Increased the model's fraud prediction/)).toBeInTheDocument();
  });

  it("handles an empty factor list without crashing", () => {
    render(<ShapChart factors={[]} />);
    expect(screen.getAllByText(/no factors pushed/i)).toHaveLength(2);
  });
});
