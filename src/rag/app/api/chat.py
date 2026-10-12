import logging
from typing import Annotated
from uuid import uuid4

import litellm
from fastapi import APIRouter, Depends, HTTPException

from rag.app.core.config import Settings, get_settings
from rag.app.core.llm import (
    generate_grounded_answer,
    route_query,
)
from rag.app.db.mongodb import db
from rag.app.schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

chat = APIRouter(prefix="/chat", tags=["chat"])


@chat.post("", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatResponse:
    interaction_id = uuid4().hex
    conversation_id = request.conversation_id or uuid4().hex

    try:
        # Stage 1: Route the query.
        decision = await route_query(
            query=request.query,
            interaction_id=interaction_id,
            conversation_id=conversation_id,
            settings=settings,
        )

        # Direct response: no retrieval needed.
        if not decision.search:
            return ChatResponse(
                interaction_id=interaction_id,
                conversation_id=conversation_id,
                response=decision.response or "",
                confidence=None,
            )

        # Stage 2: Embed semantic queries.
        semantic_queries = decision.semantic[:4]
        query_vectors = []

        if semantic_queries:
            embedding_response = await litellm.aembedding(
                model="openai/" + settings.openai_embedding_model,
                input=semantic_queries,
                timeout=20,
                metadata={
                    "trace_id": interaction_id,
                    "session_id": conversation_id,
                    "generation_name": "rag-query-embedding",
                },
                api_base=settings.litellm_proxy_api_base,
                api_key=settings.litellm_proxy_api_key,
            )

            query_vectors = [item["embedding"] for item in embedding_response.data]

        # Stage 3: Keyword + vector search + RRF reranking.
        chunks = await db.hybrid_search(
            keys=decision.keys,
            query_vectors=query_vectors,
            candidate_k=20,
            top_k=5,
        )

        # Stage 4: Generate the grounded answer.
        answer = await generate_grounded_answer(
            query=request.query,
            chunks=chunks,
            interaction_id=interaction_id,
            conversation_id=conversation_id,
            settings=settings,
        )

        return ChatResponse(
            interaction_id=interaction_id,
            conversation_id=conversation_id,
            response=answer.response,
            confidence=answer.confidence,
        )

    except Exception as exc:
        logger.exception(
            "Chat pipeline failed: interaction_id=%s",
            interaction_id,
        )

        raise HTTPException(
            status_code=502,
            detail={
                "error": "Chat pipeline failed",
                "interaction_id": interaction_id,
            },
        ) from exc
