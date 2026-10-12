from fastapi import APIRouter

from rag.app.api.chat import chat
from rag.app.api.ingest import ingest

app = APIRouter()
app.include_router(ingest)
app.include_router(chat)
