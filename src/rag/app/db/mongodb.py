import asyncio
from typing import Annotated, Any

from fastapi import Depends
from pymongo import AsyncMongoClient

from rag.app.core.config import Settings, get_settings


class MongoDB:
    def __init__(self, settings: Annotated[dict, Depends(get_settings)]) -> None:
        self.settings = settings
        self.client = AsyncMongoClient(settings.require_mongodb())
        self.db = self.client[settings.mongodb_db]
        self.chunks = self.db[settings.mongodb_chunks_collection]

    async def ping(self) -> dict:
        result = await self.client.admin.command("ping")
        return result

    async def close(self) -> None:
        await self.client.close()

    async def keyword_search(
        self,
        keys: list[str],
        *,
        candidate_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Search chunk text using MongoDB Atlas Search."""

        if not 1 <= candidate_k <= 100:
            raise ValueError("candidate_k must be between 1 and 100")

        cleaned_keys = list(
            dict.fromkeys(
                key.strip() for key in keys if isinstance(key, str) and key.strip()
            )
        )[:8]

        if not cleaned_keys:
            return []

        pipeline = [
            {
                "$search": {
                    "index": self.settings.mongodb_text_index,
                    "text": {
                        "query": cleaned_keys,
                        "path": "text",
                        "matchCriteria": "any",
                    },
                }
            },
            {"$limit": candidate_k},
            {
                "$project": {
                    "_id": 1,
                    "document_id": 1,
                    "chunk_id": 1,
                    "chunk_index": 1,
                    "text": 1,
                    "token_count": 1,
                    "metadata": 1,
                    "keyword_score": {"$meta": "searchScore"},
                }
            },
        ]

        cursor = await self.chunks.aggregate(pipeline)

        return await cursor.to_list(length=candidate_k)

    async def semantic_search(
        self,
        query_vector: list[float],
        *,
        candidate_k: int = 20,
    ) -> list[dict[str, Any]]:
        """Retrieve chunks using MongoDB Vector Search."""

        if not 1 <= candidate_k <= 100:
            raise ValueError("candidate_k must be between 1 and 100")

        expected_dimensions = self.settings.mongodb_vector_dimensions

        if len(query_vector) != expected_dimensions:
            raise ValueError(
                f"Expected {expected_dimensions} embedding dimensions; "
                f"received {len(query_vector)}"
                f"model {self.settings.openai_embedding_model}"
            )

        pipeline = [
            {
                "$vectorSearch": {
                    "index": self.settings.mongodb_vector_index,
                    "path": "embedding",
                    "queryVector": query_vector,
                    "numCandidates": max(candidate_k * 20, 100),
                    "limit": candidate_k,
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "document_id": 1,
                    "chunk_id": 1,
                    "chunk_index": 1,
                    "text": 1,
                    "token_count": 1,
                    "metadata": 1,
                    "vector_score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        cursor = await self.chunks.aggregate(pipeline)

        return await cursor.to_list(length=candidate_k)

    async def hybrid_search(
        self,
        *,
        keys: list[str],
        query_vectors: list[list[float]],
        candidate_k: int = 20,
        top_k: int = 5,
    ) -> list[dict]:

        if not 1 <= candidate_k <= 100:
            raise ValueError("candidate_k must be between 1 and 100")

        if not 1 <= top_k <= 20:
            raise ValueError("top_k must be between 1 and 20")

        vectors = query_vectors[:4]

        ranked_lists = []

        # 1. Keyword search
        if keys:
            keyword_results = await self.keyword_search(
                keys=keys,
                candidate_k=candidate_k,
            )

            ranked_lists.append(("keyword", keyword_results, 1.0))

        # 2. Semantic vector searches
        if vectors:
            semantic_weight = 1.0 / len(vectors)

            for index, vector in enumerate(vectors, start=1):
                semantic_results = await self.semantic_search(
                    query_vector=vector,
                    candidate_k=candidate_k,
                )

                ranked_lists.append(
                    (
                        f"semantic_{index}",
                        semantic_results,
                        semantic_weight,
                    )
                )

        # 3. Return empty results if no searches were performed.
        if not ranked_lists:
            return []

        # 4. Merge, deduplicate and rerank using RRF.
        return reciprocal_rank_fusion(
            ranked_lists,
            top_k=top_k,
        )


db = MongoDB(Settings())


async def ensure_vector_index():

    # Make sure collection exists first
    collection_names = await db.db.list_collection_names()

    if db.settings.mongodb_chunks_collection not in collection_names:
        await db.db.create_collection(db.settings.mongodb_chunks_collection)

    # Check existing search/vector indexes
    cursor = await db.chunks.list_search_indexes()
    existing_indexes = await cursor.to_list()

    if any(
        index["name"] == db.settings.mongodb_vector_index for index in existing_indexes
    ):
        print("Indexes exists")
        return

    print("indexes does not exists")
    # Create vector index
    await db.chunks.create_search_index(
        {
            "name": db.settings.mongodb_vector_index,
            "type": "vectorSearch",
            "definition": {
                "fields": [
                    {
                        "type": "vector",
                        "path": "embedding",
                        "numDimensions": db.settings.mongodb_vector_dimensions,
                        "similarity": "cosine",
                    }
                ]
            },
        }
    )


async def store_embeddings(documents):
    await ensure_vector_index()
    if not documents:
        return
    await db.chunks.insert_many(documents)


def reciprocal_rank_fusion(
    ranked_lists: list[tuple[str, list[dict], float]],
    *,
    top_k: int = 5,
    rank_constant: int = 60,
) -> list[dict]:
    """Merge ranked lists using weighted Reciprocal Rank Fusion."""

    fused: dict[str, dict] = {}

    for source, documents, weight in ranked_lists:
        for rank, document in enumerate(documents, start=1):
            identity = str(document.get("chunk_id") or document.get("_id"))

            if identity not in fused:
                fused[identity] = {
                    **document,
                    "rrf_score": 0.0,
                    "retrieval_methods": [],
                    "retrieval_ranks": {},
                }

            result = fused[identity]

            result["rrf_score"] += weight / (rank_constant + rank)

            if source not in result["retrieval_methods"]:
                result["retrieval_methods"].append(source)

            result["retrieval_ranks"][source] = rank

    ranked = sorted(
        fused.values(),
        key=lambda item: item["rrf_score"],
        reverse=True,
    )

    return ranked[:top_k]
