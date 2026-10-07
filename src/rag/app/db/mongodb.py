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


def ensure_vector_index():
    existing_indexes = db.chunks.list_search_indexes()

    if any(
        index["name"] == db.settings.mongodb_vector_index for index in existing_indexes
    ):
        return

    db.chunks.create_search_index(
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
def store_embeddings(documents):
    ensure_vector_index()
    if not documents:
        return
    db.insert_many(documents)