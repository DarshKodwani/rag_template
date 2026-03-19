import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { LandingPage } from "@/components/LandingPage";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

describe("LandingPage", () => {
  it("renders the title", () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );
    expect(screen.getByText("What would you like to do?")).toBeInTheDocument();
  });

  it("renders chat and documents cards", () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );
    expect(screen.getByText("Ask AnaGuide")).toBeInTheDocument();
    expect(screen.getByText("Manage Documents")).toBeInTheDocument();
  });

  it("navigates to /chat when chat card is clicked", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );
    await user.click(screen.getByText("Ask AnaGuide"));
    expect(mockNavigate).toHaveBeenCalledWith("/chat");
  });

  it("navigates to /documents when documents card is clicked", async () => {
    const user = userEvent.setup();
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>,
    );
    await user.click(screen.getByText("Manage Documents"));
    expect(mockNavigate).toHaveBeenCalledWith("/documents");
  });
});
