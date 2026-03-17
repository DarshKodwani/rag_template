import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "@/App";

describe("App", () => {
  it("renders the header", () => {
    render(<App />);
    expect(screen.getByText("📄 RAG Demo")).toBeInTheDocument();
  });

  it("renders the subtitle", () => {
    render(<App />);
    expect(screen.getByText("RAG · Qdrant · FastAPI")).toBeInTheDocument();
  });

  it("renders ChatPanel and UploadPanel", () => {
    render(<App />);
    expect(screen.getByText("Chat")).toBeInTheDocument();
    expect(screen.getByText("Documents")).toBeInTheDocument();
  });
});
