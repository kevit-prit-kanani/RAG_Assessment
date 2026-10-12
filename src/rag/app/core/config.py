from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_embedding_model: str = Field(
        default="text-embedding-3-large", alias="OPENAI_EMBEDDING_MODEL"
    )
    openai_embedding_dimensions: int = Field(
        default=3072, ge=1, le=8192, alias="OPENAI_EMBEDDING_DIMENSIONS"
    )
    openai_chat_model: str = Field(default="gpt-6.1-sol", alias="OPENAI_CHAT_MODEL")

    mongodb_uri: str | None = Field(default=None, alias="MONGODB_URI")
    mongodb_db: str = Field(default="RAG_assessment", alias="MONGODB_DB")
    mongodb_chunks_collection: str = Field(
        default="chunks", alias="MONGODB_CHUNKS_COLLECTION"
    )
    mongodb_vector_index: str = Field(
        default="chunk_vector_index", alias="MONGODB_VECTOR_INDEX"
    )
    mongodb_vector_dimensions: int = Field(
        default=3072, alias="MONGODB_VECTOR_DIMENSIONS"
    )
    mongodb_text_index: str = Field(
        default="chunk_text_index", alias="MONGODB_SEARCH_INDEX"
    )
    langfuse_secrete_key: str = Field(
        default="langfuse_secrete_key", alias="LANGFUSE_SECRET_KEY"
    )
    langfuse_public_key: str = Field(
        default="langfuse_public_key", alias="LANGFUSE_PUBLIC_KEY"
    )
    langfuse_base_url: str = Field(
        default="langfuse_base_url", alias="LANGFUSE_BASE_URL"
    )

    def require_openai(self) -> str:
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        return self.openai_api_key

    def require_mongodb(self) -> str:
        if not self.mongodb_uri:
            raise RuntimeError("MONGODB_URI is not configured")
        return self.mongodb_uri

    def require_langfuse(self) -> str:
        if not (
            self.langfuse_base_url
            and self.langfuse_public_key
            and self.langfuse_secrete_key
        ):
            raise RuntimeError("Langfuse Keys not configured properly")
        return self.langfuse_base_url


def get_settings() -> Settings:
    settings = Settings()
    return settings
