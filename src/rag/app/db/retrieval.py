from typing import Annotated

import litellm
from fastapi import Depends

from rag.app.core.config import get_settings
from rag.app.core.llm import trace_metadata


async def semantic_search(
    queries: list[str],
    interaction_id: str,
    conversation_id: str,
    settings: Annotated[dict, Depends(get_settings)],
    limit: int = 5,
) -> list[list[dict]]:

    queries = queries[:4]

    if not queries:
        return []

    # Must match the model used to embed stored document chunks.
    embedding_response = await litellm.aembedding(
        model=settings.openai_embedding_model,
        input=queries,
        timeout=20,
        metadata=trace_metadata(
            interaction_id,
            conversation_id,
            "rag-query-embedding",
        ),
    )

    vectors = [item["embedding"] for item in embedding_response.data]

    results = []

    for vector in vectors:
        chunks = await vector_search(
            vector=vector,
            limit=limit,
        )
        results.append(chunks)

    return results
