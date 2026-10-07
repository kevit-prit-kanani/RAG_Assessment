from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

ingest = APIRouter(prefix="ingest", tags=["ingestion"])

PDF_DIR = Path()


async def save_pdf(file: UploadFile):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
