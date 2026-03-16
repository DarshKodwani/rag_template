"""RAG search: embed query → retrieve from Qdrant → generate answer."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.core.models import ChatRequest, ChatResponse
from app.rag.citations import payloads_to_citations
from app.rag.prompts import SYSTEM_PROMPT, build_user_prompt

if TYPE_CHECKING:
    from app.core.config import Settings

log = logging.getLogger(__name__)


def _embed_query(query: str, settings: "Settings") -> list[float]:
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )
    response = client.embeddings.create(
        input=[query],
        model=settings.azure_openai_embedding_deployment,
    )
    return response.data[0].embedding


def _chat_completion(
    messages: list[dict],
    settings: "Settings",
) -> str:
    from openai import AzureOpenAI

    client = AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )
    response = client.chat.completions.create(
        model=settings.azure_openai_chat_deployment,
        messages=messages,
        temperature=0.0,
    )
    return response.choices[0].message.content or ""


def answer_query(request: ChatRequest, settings: "Settings") -> ChatResponse:
    from app.vectordb.qdrant_store import QdrantStore

    store = QdrantStore(settings)

    # 1. Embed the user's question
    query_vector = _embed_query(request.message, settings)

    # 2. Retrieve top-k chunks from Qdrant
    raw_results = store.search(query_vector, top_k=settings.top_k, filter=None)
    # raw_results: list of (payload: dict, chunk_id: str)

    if not raw_results:
        return ChatResponse(
            answer="I don't have enough information in the provided documents to answer that question.",
            citations=[],
        )

    # 3. Build context blocks (text of each chunk)
    context_blocks = [payload.get("text", "") for payload, _ in raw_results]

    # 4. Compose messages for chat model
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Include prior conversation history
    for msg in request.chat_history:
        messages.append({"role": msg.role, "content": msg.content})

    # Add current turn
    messages.append(
        {"role": "user", "content": build_user_prompt(request.message, context_blocks)}
    )

    # 5. Generate answer
    answer = _chat_completion(messages, settings)

    # 6. Build structured citations
    citations = payloads_to_citations(raw_results)

    log.info(
        "Answered query '%s…' with %d citations",
        request.message[:60],
        len(citations),
    )
    return ChatResponse(answer=answer, citations=citations)
