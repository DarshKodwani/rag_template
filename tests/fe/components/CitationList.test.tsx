import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { CitationList } from "@/components/CitationList";
import type { Citation } from "@/types";

vi.mock("@/api/client", () => ({
  docUrl: vi.fn((path: string) => `http://localhost:8000${path}`),
}));

describe("CitationList", () => {
  it("returns null when citations are empty", () => {
    const { container } = render(<CitationList citations={[]} />);
    expect(container.innerHTML).toBe("");
  });

  it("renders citations header", () => {
    const citations: Citation[] = [
      {
        doc_name: "doc.pdf",
        doc_path: "/documents/doc.pdf",
        snippet: "Some text",
        chunk_id: "c1",
      },
    ];
    render(<CitationList citations={citations} />);
    expect(screen.getByText("📎 Sources")).toBeInTheDocument();
  });

  it("renders document name as a link", () => {
    const citations: Citation[] = [
      {
        doc_name: "report.pdf",
        doc_path: "/documents/report.pdf",
        snippet: "Text here",
        chunk_id: "c1",
      },
    ];
    render(<CitationList citations={citations} />);
    const link = screen.getByRole("link", { name: "report.pdf" });
    expect(link).toHaveAttribute(
      "href",
      "http://localhost:8000/documents/report.pdf"
    );
    expect(link).toHaveAttribute("target", "_blank");
  });

  it("renders page number when present", () => {
    const citations: Citation[] = [
      {
        doc_name: "doc.pdf",
        doc_path: "/documents/doc.pdf",
        page: 5,
        snippet: "Text",
        chunk_id: "c1",
      },
    ];
    render(<CitationList citations={citations} />);
    expect(screen.getByText("· p.5")).toBeInTheDocument();
  });

  it("renders section when present", () => {
    const citations: Citation[] = [
      {
        doc_name: "doc.pdf",
        doc_path: "/documents/doc.pdf",
        section: "Introduction",
        snippet: "Text",
        chunk_id: "c1",
      },
    ];
    render(<CitationList citations={citations} />);
    expect(screen.getByText("· §Introduction")).toBeInTheDocument();
  });

  it("renders snippet in blockquote", () => {
    const citations: Citation[] = [
      {
        doc_name: "doc.pdf",
        doc_path: "/documents/doc.pdf",
        snippet: "Important finding here.",
        chunk_id: "c1",
      },
    ];
    render(<CitationList citations={citations} />);
    expect(screen.getByText("Important finding here.")).toBeInTheDocument();
  });

  it("renders multiple citations", () => {
    const citations: Citation[] = [
      {
        doc_name: "a.pdf",
        doc_path: "/documents/a.pdf",
        snippet: "Text A",
        chunk_id: "c1",
      },
      {
        doc_name: "b.pdf",
        doc_path: "/documents/b.pdf",
        snippet: "Text B",
        chunk_id: "c2",
      },
    ];
    render(<CitationList citations={citations} />);
    expect(screen.getByText("a.pdf")).toBeInTheDocument();
    expect(screen.getByText("b.pdf")).toBeInTheDocument();
  });
});
