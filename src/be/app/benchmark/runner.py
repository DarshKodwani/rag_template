"""Benchmark runner — evaluates RAG pipeline against ground truth."""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from app.benchmark.scorer import (
    llm_judge,
    retrieval_precision,
    retrieval_recall,
)
from app.core.config import Settings, get_settings, PROJECT_ROOT
from app.core.models import ChatRequest
from app.rag.search import answer_query
from app.vectordb.qdrant_store import QdrantStore
from app.rag.search import _embed_query

log = logging.getLogger(__name__)

GROUND_TRUTH_PATH = PROJECT_ROOT / "benchmarks" / "ground_truth.json"


def load_ground_truth(path: Path | None = None) -> list[dict]:
    """Load the Q&A ground truth dataset."""
    p = path or GROUND_TRUTH_PATH
    with open(p) as f:
        return json.load(f)


def _retrieve_pages(question: str, settings: Settings, top_k: int) -> list[int | None]:
    """Run embedding + retrieval only, return pages of retrieved chunks."""
    store = QdrantStore(settings)
    vector = _embed_query(question, settings)
    results = store.search(vector, top_k=top_k, filter=None)
    return [payload.get("page") for payload, _ in results]


def run_single(
    item: dict,
    settings: Settings,
    *,
    use_judge: bool = True,
) -> dict[str, Any]:
    """Evaluate a single ground truth item. Returns a result dict."""
    question = item["question"]
    expected = item["expected_answer"]
    q_type = item.get("type", "factual")
    expected_pages = item.get("source_pages", [])

    # 1. Retrieval scoring
    retrieved_pages = _retrieve_pages(question, settings, settings.top_k)
    recall = retrieval_recall(retrieved_pages, expected_pages)
    precision = retrieval_precision(retrieved_pages, expected_pages)

    # 2. Generation
    request = ChatRequest(message=question, chat_history=[])
    response = answer_query(request, settings)
    generated = response.answer

    # 3. LLM judge scoring
    judge = {"correctness": -1, "completeness": -1, "explanation": "skipped"}
    if use_judge:
        judge = llm_judge(question, expected, generated, settings)

    return {
        "id": item.get("id"),
        "question": question,
        "type": q_type,
        "expected_answer": expected,
        "generated_answer": generated,
        "retrieval_recall": round(recall, 3),
        "retrieval_precision": round(precision, 3),
        "retrieved_pages": retrieved_pages,
        "expected_pages": expected_pages,
        "correctness": judge["correctness"],
        "completeness": judge["completeness"],
        "judge_explanation": judge["explanation"],
        "num_citations": len(response.citations),
    }


def run_benchmark(
    *,
    ground_truth_path: Path | None = None,
    use_judge: bool = True,
    limit: int | None = None,
) -> dict[str, Any]:
    """Run the full benchmark suite. Returns summary + per-item results."""
    settings = get_settings()
    items = load_ground_truth(ground_truth_path)
    if limit:
        items = items[:limit]

    results: list[dict] = []
    start = time.time()

    for i, item in enumerate(items):
        log.info("Benchmark [%d/%d] %s", i + 1, len(items), item["question"][:60])
        result = run_single(item, settings, use_judge=use_judge)
        results.append(result)

    elapsed = time.time() - start

    # Compute aggregate metrics
    factual = [r for r in results if r["type"] == "factual"]
    reasoning = [r for r in results if r["type"] == "reasoning"]

    summary = {
        "total_questions": len(results),
        "factual_count": len(factual),
        "reasoning_count": len(reasoning),
        "elapsed_seconds": round(elapsed, 1),
        "avg_retrieval_recall": _avg(results, "retrieval_recall"),
        "avg_retrieval_precision": _avg(results, "retrieval_precision"),
        "avg_correctness": _avg(results, "correctness") if use_judge else None,
        "avg_completeness": _avg(results, "completeness") if use_judge else None,
        "avg_correctness_factual": _avg(factual, "correctness") if use_judge else None,
        "avg_correctness_reasoning": _avg(reasoning, "correctness") if use_judge else None,
        "avg_completeness_factual": _avg(factual, "completeness") if use_judge else None,
        "avg_completeness_reasoning": _avg(reasoning, "completeness") if use_judge else None,
    }

    return {"summary": summary, "results": results}


def _avg(items: list[dict], key: str) -> float | None:
    vals = [r[key] for r in items if isinstance(r.get(key), (int, float)) and r[key] >= 0]
    if not vals:
        return None
    return round(sum(vals) / len(vals), 3)


def save_report(report: dict, path: Path | None = None) -> Path:
    """Write the benchmark report JSON and HTML dashboard."""
    from app.benchmark.dashboard import save_dashboard

    p = path or (PROJECT_ROOT / "benchmarks" / "latest_report.json")
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(report, f, indent=2)

    # Auto-generate HTML dashboard alongside the JSON
    dashboard_path = p.with_suffix(".html")
    save_dashboard(report, dashboard_path)
    log.info("Dashboard saved to %s", dashboard_path)
    return p


def print_summary(report: dict) -> None:
    """Print a human-readable summary to stdout."""
    s = report["summary"]
    print("\n" + "=" * 60)
    print("  RAG BENCHMARK REPORT")
    print("=" * 60)
    print(f"  Questions evaluated:  {s['total_questions']}")
    print(f"    Factual:            {s['factual_count']}")
    print(f"    Reasoning:          {s['reasoning_count']}")
    print(f"  Time elapsed:         {s['elapsed_seconds']}s")
    print("-" * 60)
    print(f"  Retrieval recall:     {s['avg_retrieval_recall']}")
    print(f"  Retrieval precision:  {s['avg_retrieval_precision']}")
    if s.get("avg_correctness") is not None:
        print("-" * 60)
        print(f"  Correctness (all):    {s['avg_correctness']} / 5")
        print(f"  Completeness (all):   {s['avg_completeness']} / 5")
        print(f"  Correctness (fact):   {s['avg_correctness_factual']} / 5")
        print(f"  Correctness (reas):   {s['avg_correctness_reasoning']} / 5")
        print(f"  Completeness (fact):  {s['avg_completeness_factual']} / 5")
        print(f"  Completeness (reas):  {s['avg_completeness_reasoning']} / 5")
    print("=" * 60 + "\n")
