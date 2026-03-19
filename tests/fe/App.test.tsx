import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "@/App";

describe("App", () => {
  it("renders the header", () => {
    render(<App />);
    expect(screen.getByText("AnaGuide")).toBeInTheDocument();
    expect(screen.getByAltText("BIL")).toBeInTheDocument();
  });

  it("renders the subtitle", () => {
    render(<App />);
    expect(screen.getByText("Your AnaCredit regulation assistant")).toBeInTheDocument();
  });

  it("renders the landing page by default", () => {
    render(<App />);
    expect(
      screen.getByText("What would you like to do?"),
    ).toBeInTheDocument();
    expect(screen.getByText("Ask AnaGuide")).toBeInTheDocument();
    expect(screen.getByText("Manage Documents")).toBeInTheDocument();
  });
});
