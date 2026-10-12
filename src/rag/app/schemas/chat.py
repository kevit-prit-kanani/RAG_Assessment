from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    query: str = Field(min_length=1, max_length=4000)

    conversation_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
    )


class RouteDecision(BaseModel):
    keys: list[str] = Field(
        default_factory=list,
        max_length=8,
    )

    semantic: list[str] = Field(
        default_factory=list,
        max_length=4,
    )

    search: bool

    response: str | None = None


class GroundedAnswer(BaseModel):
    response: str = Field(min_length=1, max_length=6000)

    confidence: int = Field(ge=1, le=100)


class ChatResponse(BaseModel):
    interaction_id: str
    conversation_id: str

    response: str

    # Applicable to document-grounded answers.
    # None means this was a direct response without retrieval.
    confidence: int | None = Field(
        default=None,
        ge=1,
        le=100,
    )