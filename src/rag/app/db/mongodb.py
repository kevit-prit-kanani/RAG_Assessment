from pymongo import AsyncMongoClient

from rag.app.core.config import Settings


class MongoDB:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncMongoClient(settings.require_mongodb())
        self.db = self.client[settings.mongodb_db]
        self.chunks = self.db[settings.mongodb_chunks_collection]

    async def ping(self) -> dict:
        result = await self.client.admin.command("ping")
        return result

    async def close(self) -> None:
        await self.client.close()


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
        return

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
