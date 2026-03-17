"""Tests for rag/prompts.py."""
from __future__ import annotations

from app.rag.prompts import SYSTEM_PROMPT, build_user_prompt


class TestSystemPrompt:
    def test_is_non_empty_string(self):
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 0

    def test_contains_key_instructions(self):
        assert "context" in SYSTEM_PROMPT.lower()
        assert "Source" in SYSTEM_PROMPT


class TestBuildUserPrompt:
    def test_with_single_block(self):
        result = build_user_prompt("What is X?", ["X is a variable."])
        assert "[Source 1]" in result
        assert "X is a variable." in result
        assert "Question: What is X?" in result

    def test_with_multiple_blocks(self):
        blocks = ["Block A", "Block B", "Block C"]
        result = build_user_prompt("Question?", blocks)
        assert "[Source 1]" in result
        assert "[Source 2]" in result
        assert "[Source 3]" in result
        assert "Block A" in result
        assert "Block C" in result

    def test_with_empty_blocks(self):
        result = build_user_prompt("Q?", [])
        assert "Question: Q?" in result
        assert "Context:" in result
