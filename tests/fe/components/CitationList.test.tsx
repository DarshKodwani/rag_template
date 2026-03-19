import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { CitationList } from "@/components/CitationList";
import type { Citation } from "@/types";

vi.mock("@/api/client", () => ({
  docUrl: vi.fn((path: string) => `http://localhost:8000${path}`),
}));

const baseCitation: Citation = {
  doc_name: "doc.pdf",
  doc_path: "/documents/doc.pdf",
  snippet: "Some text",
  chunk_id: "c1",
};

describe("CitationList", () => {
  it("returns null when citations are empty", () => {
    const { container } = render(
      <CitationList citations={[]} activeIdx={null} onSelect={vi.fn()} />,
    );
    expect(container.innerHTML).toBe("");
  });

  it("renders citations header", () => {
    render(
      <CitationList citations={[baseCitation]} activeIdx={null} onSelect={vi.fn()} />,
    );
    expect(screen.getByText("Sources")).toBeInTheDocument();
  });

  it("renders citation chips with numbers and names", () => {
    const citations: Citation[] = [
      baseCitation,
      { ...baseCitation, doc_name: "other.pdf", chunk_id: "c2" },
    ];
    render(
      <CitationList citations={citations} activeIdx={null} onSelect={vi.fn()} />,
    );
    expect(screen.getByText("1")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("doc.pdf")).toBeInTheDocument();
    expect(screen.getByText("other.pdf")).toBeInTheDocument();
  });

  it("calls onSelect when a chip is clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <CitationList citations={[baseCitation]} activeIdx={null} onSelect={onSelect} />,
    );
    await user.click(screen.getByTitle("doc.pdf"));
    expect(onSelect).toHaveBeenCalledWith(0);
  });

  it("shows popover when activeIdx is set", () => {
    const citation: Citation = {
      doc_name: "report.pdf",
      doc_path: "/documents/report.pdf",
      page: 5,
      section: "Introduction",
      snippet: "Important finding here.",
      chunk_id: "c1",
    };
    render(
      <CitationList citations={[citation]} activeIdx={0} onSelect={vi.fn()} />,
    );
    // Popover shows doc link, page, section, snippet
    expect(screen.getByText("📄 report.pdf")).toBeInTheDocument();
    expect(screen.getByText("Page 5")).toBeInTheDocument();
    expect(screen.getByText("§ Introduction")).toBeInTheDocument();
    expect(screen.getByText("Important finding here.")).toBeInTheDocument();
  });

  it("popover has a working document link", () => {
    render(
      <CitationList citations={[baseCitation]} activeIdx={0} onSelect={vi.fn()} />,
    );
    const link = screen.getByRole("link", { name: /doc\.pdf/ });
    expect(link).toHaveAttribute(
      "href",
      "http://localhost:8000/documents/doc.pdf",
    );
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("calls onSelect when close button is clicked", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <CitationList citations={[baseCitation]} activeIdx={0} onSelect={onSelect} />,
    );
    await user.click(screen.getByLabelText("Close"));
    expect(onSelect).toHaveBeenCalledWith(0);
  });

  it("does not show popover when activeIdx is null", () => {
    render(
      <CitationList citations={[baseCitation]} activeIdx={null} onSelect={vi.fn()} />,
    );
    expect(screen.queryByText("📄 doc.pdf")).not.toBeInTheDocument();
  });

  it("renders multiple chips", () => {
    const citations: Citation[] = [
      { ...baseCitation, doc_name: "a.pdf", chunk_id: "c1" },
      { ...baseCitation, doc_name: "b.pdf", chunk_id: "c2" },
    ];
    render(
      <CitationList citations={citations} activeIdx={null} onSelect={vi.fn()} />,
    );
    expect(screen.getByText("a.pdf")).toBeInTheDocument();
    expect(screen.getByText("b.pdf")).toBeInTheDocument();
  });

  it("calls onSelect when clicking outside the popover", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const { container } = render(
      <div>
        <span data-testid="outside">outside</span>
        <CitationList citations={[baseCitation]} activeIdx={0} onSelect={onSelect} />
      </div>,
    );
    // Click outside the popover
    await user.click(screen.getByTestId("outside"));
    expect(onSelect).toHaveBeenCalledWith(0);
  });
});
