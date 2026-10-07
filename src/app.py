from fastapi import APIRouter

from rag.app.api.ingest import ingest

app = APIRouter()
app.include_router(ingest)
