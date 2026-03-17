"""Tests for rag/search.py."""
from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest

from app.core.models import ChatRequest, ChatResponse, ChatMessage


def _make_settings(azure: bool = False):
    s = MagicMock()
    s.azure_openai_endpoint = "https://foo.openai.azure.com/"
    s.azure_openai_api_key = "az-key"
    s.azure_openai_api_version = "2024-02-01"
    s.azure_openai_chat_deployment = "gpt-4o"
    s.azure_openai_embedding_deployment = "emb-deploy"

    s.openai_api_key = "sk-test"
    s.openai_base_url = "https://api.openai.com/v1"
    s.openai_chat_model = "gpt-4o"
    s.openai_embedding_model = "text-embedding-3-small"

    s.qdrant_url = "http://localhost:6333"
    s.qdrant_collection = "documents"
    s.top_k = 3

    s.azure_keys_present = azure
    s.openai_keys_present = not azure
    return s


class TestGetClient:
    def test_returns_azure_client_when_azure_keys(self):
        from app.rag.search import _get_client

        settings = _make_settings(azure=True)
        with patch("openai.AzureOpenAI") as mock_azure:
            client = _get_client(settings)
            mock_azure.assert_called_once()

    def test_returns_openai_client_when_no_azure(self):
        from app.rag.search import _get_client

        settings = _make_settings(azure=False)
        with patch("openai.OpenAI") as mock_openai:
            client = _get_client(settings)
            mock_openai.assert_called_once()


class TestEmbedQuery:
    def test_embeds_with_openai(self):
        from app.rag.search import _embed_query

        settings = _make_settings(azure=False)
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.1, 0.2, 0.3]
        mock_response = MagicMock()
        mock_response.data = [mock_embedding]

        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response

        with patch("app.rag.search._get_client", return_value=mock_client):
            result = _embed_query("test query", settings)

        assert result == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once_with(
            input=["test query"], model="text-embedding-3-small"
        )

    def test_embeds_with_azure(self):
        from app.rag.search import _embed_query

        settings = _make_settings(azure=True)
        mock_embedding = MagicMock()
        mock_embedding.embedding = [0.4, 0.5]
        mock_response = MagicMock()
        mock_response.data = [mock_embedding]

        mock_client = MagicMock()
        mock_client.embeddings.create.return_value = mock_response

        with patch("app.rag.search._get_client", return_value=mock_client):
            result = _embed_query("test", settings)

        mock_client.embeddings.create.assert_called_once_with(
            input=["test"], model="emb-deploy"
        )


class TestChatCompletion:
    def test_returns_content(self):
        from app.rag.search import _chat_completion

        settings = _make_settings(azure=False)
        mock_choice = MagicMock()
        mock_choice.message.content = "Generated answer"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("app.rag.search._get_client", return_value=mock_client):
            result = _chat_completion([{"role": "user", "content": "hi"}], settings)

        assert result == "Generated answer"

    def test_returns_empty_string_on_none_content(self):
        from app.rag.search import _chat_completion

        settings = _make_settings(azure=False)
        mock_choice = MagicMock()
        mock_choice.message.content = None
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("app.rag.search._get_client", return_value=mock_client):
            result = _chat_completion([], settings)

        assert result == ""

    def test_uses_azure_deployment(self):
        from app.rag.search import _chat_completion

        settings = _make_settings(azure=True)
        mock_choice = MagicMock()
        mock_choice.message.content = "ok"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response

        with patch("app.rag.search._get_client", return_value=mock_client):
            _chat_completion([], settings)

        call_kwargs = mock_client.chat.completions.create.call_args[1]
        assert call_kwargs["model"] == "gpt-4o"


class TestAnswerQuery:
    def test_no_results_returns_no_info(self):
        from app.rag.search import answer_query

        settings = _make_settings()
        request = ChatRequest(message="What is X?")

        mock_store = MagicMock()
        mock_store.search.return_value = []

        with (
            patch("app.vectordb.qdrant_store.QdrantStore", return_value=mock_store),
            patch("app.rag.search._embed_query", return_value=[0.1] * 3),
        ):
            result = answer_query(request, settings)

        assert "don't have enough information" in result.answer
        assert result.citations == []

    def test_with_results_calls_chat(self):
        from app.rag.search import answer_query

        settings = _make_settings()
        request = ChatRequest(message="What is X?")

        payload = {
            "text": "X is a variable.",
            "doc_name": "doc.pdf",
            "doc_rel_path": "documents/doc.pdf",
            "page": 1,
            "section": None,
        }
        mock_store = MagicMock()
        mock_store.search.return_value = [(payload, "chunk1")]

        with (
            patch("app.vectordb.qdrant_store.QdrantStore", return_value=mock_store),
            patch("app.rag.search._embed_query", return_value=[0.1] * 3),
            patch("app.rag.search._chat_completion", return_value="X is a variable."),
        ):
            result = answer_query(request, settings)

        assert result.answer == "X is a variable."
        assert len(result.citations) == 1

    def test_with_chat_history(self):
        from app.rag.search import answer_query

        settings = _make_settings()
        history = [
            ChatMessage(role="user", content="Hi"),
            ChatMessage(role="assistant", content="Hello!"),
        ]
        request = ChatRequest(message="Follow up?", chat_history=history)

        payload = {"text": "context", "doc_name": "a.pdf", "doc_rel_path": "a.pdf"}
        mock_store = MagicMock()
        mock_store.search.return_value = [(payload, "c1")]

        with (
            patch("app.vectordb.qdrant_store.QdrantStore", return_value=mock_store),
            patch("app.rag.search._embed_query", return_value=[0.1]),
            patch("app.rag.search._chat_completion", return_value="Answer") as mock_chat,
        ):
            result = answer_query(request, settings)

        # Verify chat_history messages are included
        messages = mock_chat.call_args[0][0]
        roles = [m["role"] for m in messages]
        assert "system" in roles
        assert roles.count("user") == 2  # history user + current user
        assert "assistant" in roles
