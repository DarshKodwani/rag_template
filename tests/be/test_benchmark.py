"""Tests for the benchmark scoring, runner, and dashboard modules."""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.benchmark.scorer import llm_judge, retrieval_precision, retrieval_recall
from app.benchmark.dashboard import generate_html, save_dashboard, _score_color, _pct_color, _fmt, _esc
from app.benchmark.runner import (
    _avg,
    _retrieve_pages,
    load_ground_truth,
    print_summary,
    run_benchmark,
    run_single,
    save_report,
)
from app.core.models import ChatResponse, Citation


def _sample_report():
    return {
        "summary": {
            "total_questions": 2, "factual_count": 1, "reasoning_count": 1,
            "elapsed_seconds": 5.0,
            "avg_retrieval_recall": 0.9, "avg_retrieval_precision": 0.7,
            "avg_correctness": 4.0, "avg_completeness": 3.5,
            "avg_correctness_factual": 5.0, "avg_correctness_reasoning": 3.0,
            "avg_completeness_factual": 4.0, "avg_completeness_reasoning": 3.0,
        },
        "results": [
            {
                "id": "f-001", "question": "What is X?", "type": "factual",
                "expected_answer": "X is Y.", "generated_answer": "X is Y indeed.",
                "retrieval_recall": 1.0, "retrieval_precision": 0.5,
                "retrieved_pages": [1, 3], "expected_pages": [1],
                "correctness": 5, "completeness": 5,
                "judge_explanation": "Perfect answer.", "num_citations": 2,
            },
            {
                "id": "r-001", "question": "Why does Z happen?", "type": "reasoning",
                "expected_answer": "Because of W.", "generated_answer": "Due to W.",
                "retrieval_recall": 0.5, "retrieval_precision": 1.0,
                "retrieved_pages": [2], "expected_pages": [2, 4],
                "correctness": 3, "completeness": 3,
                "judge_explanation": "Partial.", "num_citations": 1,
            },
        ],
    }


# ===================================================================
# Retrieval recall
# ===================================================================


class TestRetrievalRecall:
    def test_perfect_recall(self):
        assert retrieval_recall([1, 2, 3], [1, 2, 3]) == 1.0

    def test_partial_recall(self):
        assert retrieval_recall([1, 5], [1, 2]) == 0.5

    def test_zero_recall(self):
        assert retrieval_recall([10, 20], [1, 2]) == 0.0

    def test_empty_expected_returns_one(self):
        assert retrieval_recall([1, 2], []) == 1.0

    def test_empty_retrieved(self):
        assert retrieval_recall([], [1, 2]) == 0.0

    def test_none_values_ignored(self):
        assert retrieval_recall([None, 1, None, 2], [1, 2]) == 1.0

    def test_duplicates_in_retrieved(self):
        assert retrieval_recall([1, 1, 2], [1, 2]) == 1.0

    def test_both_empty(self):
        assert retrieval_recall([], []) == 1.0


# ===================================================================
# Retrieval precision
# ===================================================================


class TestRetrievalPrecision:
    def test_perfect_precision(self):
        assert retrieval_precision([1, 2], [1, 2]) == 1.0

    def test_partial_precision(self):
        assert retrieval_precision([1, 2, 3, 4], [1, 2]) == 0.5

    def test_zero_precision(self):
        assert retrieval_precision([10, 20], [1, 2]) == 0.0

    def test_empty_retrieved_returns_zero(self):
        assert retrieval_precision([], [1, 2]) == 0.0

    def test_empty_expected(self):
        assert retrieval_precision([1, 2], []) == 0.0

    def test_none_values_ignored_precision(self):
        # Only non-None pages count: {1} from retrieved, expected {1} → 1.0
        assert retrieval_precision([None, 1, None], [1]) == 1.0

    def test_all_none_returns_zero(self):
        assert retrieval_precision([None, None], [1, 2]) == 0.0


# ===================================================================
# LLM Judge
# ===================================================================


class TestLLMJudge:
    @patch("app.rag.search._get_client")
    def test_happy_path(self, mock_get):
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content='{"correctness": 4, "completeness": 3, "explanation": "mostly correct"}'))
        ]

        settings = MagicMock()
        settings.azure_keys_present = False
        settings.openai_chat_model = "gpt-4o"

        result = llm_judge("q?", "expected", "generated", settings)
        assert result["correctness"] == 4
        assert result["completeness"] == 3
        assert "mostly correct" in result["explanation"]

    @patch("app.rag.search._get_client")
    def test_invalid_json_returns_zeros(self, mock_get):
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="NOT JSON"))
        ]

        settings = MagicMock()
        settings.azure_keys_present = False
        settings.openai_chat_model = "gpt-4o"

        result = llm_judge("q?", "expected", "generated", settings)
        assert result["correctness"] == 0
        assert result["completeness"] == 0
        assert "Parse error" in result["explanation"]

    @patch("app.rag.search._get_client")
    def test_empty_response(self, mock_get):
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content=None))
        ]

        settings = MagicMock()
        settings.azure_keys_present = False
        settings.openai_chat_model = "gpt-4o"

        result = llm_judge("q?", "expected", "generated", settings)
        assert result["correctness"] == 0
        assert result["completeness"] == 0

    @patch("app.rag.search._get_client")
    def test_uses_azure_deployment_when_present(self, mock_get):
        mock_client = MagicMock()
        mock_get.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content='{"correctness": 5, "completeness": 5, "explanation": "ok"}'))
        ]

        settings = MagicMock()
        settings.azure_keys_present = True
        settings.azure_openai_chat_deployment = "my-deployment"

        llm_judge("q?", "expected", "generated", settings)
        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["model"] == "my-deployment"


# ===================================================================
# Load ground truth
# ===================================================================


class TestLoadGroundTruth:
    def test_loads_from_custom_path(self, tmp_path: Path):
        data = [{"id": "test-001", "question": "q", "expected_answer": "a"}]
        path = tmp_path / "gt.json"
        path.write_text(json.dumps(data))
        loaded = load_ground_truth(path)
        assert len(loaded) == 1
        assert loaded[0]["id"] == "test-001"

    def test_invalid_json_raises(self, tmp_path: Path):
        path = tmp_path / "bad.json"
        path.write_text("not json!!")
        with pytest.raises(json.JSONDecodeError):
            load_ground_truth(path)


# ===================================================================
# Helper: _avg
# ===================================================================


class TestAvg:
    def test_avg_normal(self):
        items = [{"x": 1}, {"x": 3}]
        assert _avg(items, "x") == 2.0

    def test_avg_ignores_negative(self):
        items = [{"x": 3}, {"x": -1}]
        assert _avg(items, "x") == 3.0

    def test_avg_all_negative(self):
        items = [{"x": -1}, {"x": -1}]
        assert _avg(items, "x") is None

    def test_avg_empty_list(self):
        assert _avg([], "x") is None

    def test_avg_missing_key(self):
        items = [{"y": 1}]
        assert _avg(items, "x") is None


# ===================================================================
# _retrieve_pages
# ===================================================================


class TestRetrievePages:
    @patch("app.benchmark.runner._embed_query")
    @patch("app.benchmark.runner.QdrantStore")
    def test_returns_page_list(self, MockStore, mock_embed):
        mock_embed.return_value = [0.1] * 1536
        store_inst = MockStore.return_value
        store_inst.search.return_value = [
            ({"page": 5, "text": "chunk1"}, "c1"),
            ({"page": 10, "text": "chunk2"}, "c2"),
        ]

        settings = MagicMock()
        settings.top_k = 5
        pages = _retrieve_pages("test question", settings, 5)
        assert pages == [5, 10]
        store_inst.search.assert_called_once()


# ===================================================================
# run_single
# ===================================================================


class TestRunSingle:
    @patch("app.benchmark.runner.llm_judge")
    @patch("app.benchmark.runner.answer_query")
    @patch("app.benchmark.runner._retrieve_pages")
    def test_full_run(self, mock_retriev, mock_answer, mock_judge):
        mock_retriev.return_value = [5, 10]
        mock_answer.return_value = ChatResponse(
            answer="Generated answer",
            citations=[
                Citation(doc_name="doc.pdf", doc_path="documents/doc.pdf", page=5, snippet="snip", chunk_id="c1"),
            ],
        )
        mock_judge.return_value = {"correctness": 4, "completeness": 3, "explanation": "good"}

        settings = MagicMock()
        settings.top_k = 5
        item = {
            "id": "f-001",
            "question": "What is X?",
            "expected_answer": "X is Y.",
            "type": "factual",
            "source_pages": [5, 10],
        }

        result = run_single(item, settings, use_judge=True)

        assert result["id"] == "f-001"
        assert result["retrieval_recall"] == 1.0
        assert result["retrieval_precision"] == 1.0
        assert result["correctness"] == 4
        assert result["completeness"] == 3
        assert result["num_citations"] == 1
        assert result["generated_answer"] == "Generated answer"

    @patch("app.benchmark.runner.answer_query")
    @patch("app.benchmark.runner._retrieve_pages")
    def test_skip_judge(self, mock_retriev, mock_answer):
        mock_retriev.return_value = [5]
        mock_answer.return_value = ChatResponse(answer="ans", citations=[])

        settings = MagicMock()
        settings.top_k = 5
        item = {
            "id": "f-002",
            "question": "Q?",
            "expected_answer": "A.",
            "type": "factual",
            "source_pages": [5],
        }

        result = run_single(item, settings, use_judge=False)
        assert result["correctness"] == -1
        assert result["judge_explanation"] == "skipped"


# ===================================================================
# run_benchmark
# ===================================================================


class TestRunBenchmark:
    @patch("app.benchmark.runner.run_single")
    @patch("app.benchmark.runner.load_ground_truth")
    @patch("app.benchmark.runner.get_settings")
    def test_aggregation(self, mock_settings, mock_gt, mock_single):
        mock_settings.return_value = MagicMock()
        mock_gt.return_value = [
            {"id": "f-001", "question": "q1", "expected_answer": "a1", "type": "factual", "source_pages": [1]},
            {"id": "r-001", "question": "q2", "expected_answer": "a2", "type": "reasoning", "source_pages": [2]},
        ]
        mock_single.side_effect = [
            {
                "id": "f-001", "question": "q1", "type": "factual",
                "expected_answer": "a1", "generated_answer": "ga1",
                "retrieval_recall": 1.0, "retrieval_precision": 0.5,
                "retrieved_pages": [1, 3], "expected_pages": [1],
                "correctness": 5, "completeness": 5,
                "judge_explanation": "perfect", "num_citations": 2,
            },
            {
                "id": "r-001", "question": "q2", "type": "reasoning",
                "expected_answer": "a2", "generated_answer": "ga2",
                "retrieval_recall": 0.5, "retrieval_precision": 1.0,
                "retrieved_pages": [2], "expected_pages": [2, 4],
                "correctness": 3, "completeness": 3,
                "judge_explanation": "partial", "num_citations": 1,
            },
        ]

        report = run_benchmark(use_judge=True)
        s = report["summary"]
        assert s["total_questions"] == 2
        assert s["factual_count"] == 1
        assert s["reasoning_count"] == 1
        assert s["avg_retrieval_recall"] == 0.75
        assert s["avg_correctness"] == 4.0
        assert s["avg_correctness_factual"] == 5.0
        assert s["avg_correctness_reasoning"] == 3.0
        assert len(report["results"]) == 2

    @patch("app.benchmark.runner.run_single")
    @patch("app.benchmark.runner.load_ground_truth")
    @patch("app.benchmark.runner.get_settings")
    def test_limit_parameter(self, mock_settings, mock_gt, mock_single):
        mock_settings.return_value = MagicMock()
        mock_gt.return_value = [
            {"id": f"f-{i:03d}", "question": f"q{i}", "expected_answer": f"a{i}", "type": "factual", "source_pages": []}
            for i in range(10)
        ]
        mock_single.return_value = {
            "id": "f-000", "question": "q", "type": "factual",
            "expected_answer": "a", "generated_answer": "g",
            "retrieval_recall": 1.0, "retrieval_precision": 1.0,
            "retrieved_pages": [], "expected_pages": [],
            "correctness": 5, "completeness": 5,
            "judge_explanation": "ok", "num_citations": 0,
        }

        report = run_benchmark(limit=3)
        assert report["summary"]["total_questions"] == 3
        assert mock_single.call_count == 3

    @patch("app.benchmark.runner.run_single")
    @patch("app.benchmark.runner.load_ground_truth")
    @patch("app.benchmark.runner.get_settings")
    def test_no_judge(self, mock_settings, mock_gt, mock_single):
        mock_settings.return_value = MagicMock()
        mock_gt.return_value = [
            {"id": "f-001", "question": "q1", "expected_answer": "a1", "type": "factual", "source_pages": []},
        ]
        mock_single.return_value = {
            "id": "f-001", "question": "q", "type": "factual",
            "expected_answer": "a", "generated_answer": "g",
            "retrieval_recall": 1.0, "retrieval_precision": 1.0,
            "retrieved_pages": [], "expected_pages": [],
            "correctness": -1, "completeness": -1,
            "judge_explanation": "skipped", "num_citations": 0,
        }

        report = run_benchmark(use_judge=False)
        assert report["summary"]["avg_correctness"] is None


# ===================================================================
# save_report
# ===================================================================


class TestSaveReport:
    def test_saves_json_and_dashboard(self, tmp_path: Path):
        report = _sample_report()
        out = save_report(report, tmp_path / "report.json")
        assert out.exists()
        loaded = json.loads(out.read_text())
        assert loaded["summary"]["total_questions"] == 2
        # Dashboard auto-generated alongside
        assert (tmp_path / "report.html").exists()

    def test_creates_parent_dirs(self, tmp_path: Path):
        path = tmp_path / "sub" / "report.json"
        save_report(_sample_report(), path)
        assert path.exists()
        assert (tmp_path / "sub" / "report.html").exists()


# ===================================================================
# print_summary (smoke test – just make sure it doesn't crash)
# ===================================================================


class TestPrintSummary:
    def test_with_judge(self, capsys):
        report = {
            "summary": {
                "total_questions": 2, "factual_count": 1, "reasoning_count": 1,
                "elapsed_seconds": 10.5,
                "avg_retrieval_recall": 0.8, "avg_retrieval_precision": 0.7,
                "avg_correctness": 4.0, "avg_completeness": 3.5,
                "avg_correctness_factual": 5.0, "avg_correctness_reasoning": 3.0,
                "avg_completeness_factual": 4.0, "avg_completeness_reasoning": 3.0,
            },
            "results": [],
        }
        print_summary(report)
        out = capsys.readouterr().out
        assert "BENCHMARK REPORT" in out
        assert "4.0 / 5" in out

    def test_without_judge(self, capsys):
        report = {
            "summary": {
                "total_questions": 1, "factual_count": 1, "reasoning_count": 0,
                "elapsed_seconds": 2.0,
                "avg_retrieval_recall": 1.0, "avg_retrieval_precision": 1.0,
                "avg_correctness": None, "avg_completeness": None,
                "avg_correctness_factual": None, "avg_correctness_reasoning": None,
                "avg_completeness_factual": None, "avg_completeness_reasoning": None,
            },
            "results": [],
        }
        print_summary(report)
        out = capsys.readouterr().out
        assert "BENCHMARK REPORT" in out
        assert "/ 5" not in out


# ===================================================================
# Dashboard helpers
# ===================================================================


class TestEsc:
    def test_escapes_html(self):
        assert _esc("<b>hi</b>") == "&lt;b&gt;hi&lt;/b&gt;"

    def test_none_returns_empty(self):
        assert _esc(None) == ""

    def test_number(self):
        assert _esc(42) == "42"


class TestScoreColor:
    def test_high_score_green(self):
        assert _score_color(4.5, 5.0) == "#c6efce"

    def test_mid_score_amber(self):
        assert _score_color(3.0, 5.0) == "#ffeb9c"

    def test_low_score_red(self):
        assert _score_color(1.0, 5.0) == "#ffc7ce"

    def test_none_returns_grey(self):
        assert _score_color(None) == "#f0f0f0"

    def test_negative_returns_grey(self):
        assert _score_color(-1) == "#f0f0f0"


class TestPctColor:
    def test_high_green(self):
        assert _pct_color(0.9) == "#c6efce"

    def test_none_grey(self):
        assert _pct_color(None) == "#f0f0f0"


class TestFmt:
    def test_float(self):
        assert _fmt(3.456) == "3.46"

    def test_int(self):
        assert _fmt(5) == "5"

    def test_none(self):
        assert _fmt(None) == "\u2014"

    def test_custom_decimals(self):
        assert _fmt(1.2345, 1) == "1.2"


# ===================================================================
# Dashboard generation
# ===================================================================


class TestGenerateHTML:
    def test_returns_valid_html(self):
        html = generate_html(_sample_report())
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_contains_title(self):
        html = generate_html(_sample_report(), title="My Run")
        assert "My Run" in html

    def test_contains_summary_values(self):
        html = generate_html(_sample_report())
        assert "0.90" in html  # recall
        assert "4.0" in html  # correctness

    def test_contains_result_rows(self):
        html = generate_html(_sample_report())
        assert "What is X?" in html
        assert "Why does Z happen?" in html

    def test_type_badges(self):
        html = generate_html(_sample_report())
        assert "factual" in html
        assert "reasoning" in html

    def test_no_judge_scores_still_works(self):
        report = _sample_report()
        report["summary"]["avg_correctness"] = None
        report["summary"]["avg_completeness"] = None
        html = generate_html(report)
        assert "<!DOCTYPE html>" in html

    def test_escapes_html_in_answers(self):
        report = _sample_report()
        report["results"][0]["generated_answer"] = "<script>alert('xss')</script>"
        html = generate_html(report)
        assert "<script>alert" not in html
        assert "&lt;script&gt;" in html


class TestSaveDashboard:
    def test_writes_file(self, tmp_path: Path):
        out = save_dashboard(_sample_report(), tmp_path / "dash.html")
        assert out.exists()
        content = out.read_text()
        assert "<!DOCTYPE html>" in content

    def test_creates_dirs(self, tmp_path: Path):
        out = save_dashboard(_sample_report(), tmp_path / "nested" / "dash.html")
        assert out.exists()
