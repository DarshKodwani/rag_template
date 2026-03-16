"""System and user prompt templates for the RAG chat flow."""
from __future__ import annotations

SYSTEM_PROMPT = """\
You are a helpful assistant that answers questions strictly based on the provided context.

Rules:
1. Answer ONLY using the information in the context blocks below.
2. If the context does not contain enough information to answer, say:
   "I don't have enough information in the provided documents to answer that question."
3. Always cite the source(s) you used by referencing [Source N] markers in your answer.
4. Be concise and factual.
"""


def build_user_prompt(question: str, context_blocks: list[str]) -> str:
    """Build the user turn that includes the context and the question."""
    numbered = "\n\n".join(
        f"[Source {i + 1}]\n{block}" for i, block in enumerate(context_blocks)
    )
    return f"Context:\n{numbered}\n\nQuestion: {question}"
