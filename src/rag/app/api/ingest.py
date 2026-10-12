from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from rag.app.db.mongodb import store_embeddings
from rag.app.ingestion.chunker import ingest_pdf

ingest = APIRouter(prefix="/ingest", tags=["ingestion"])

PDF_DIR = Path()


async def save_pdf(file: UploadFile):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    PDF_DIR.mkdir(parents=True, exist_ok=True)

    pdf_path = PDF_DIR / file.filename

    with pdf_path.open("wb") as buffer:
        while chunk := await file.read(1024 * 1024):
            buffer.write(chunk)

    return pdf_path


@ingest.post("/preview")
async def preview(file: UploadFile):
    pdf_path = await save_pdf(file=file)

    documents = ingest_pdf(str(pdf_path))

    return {
        "filename": file.filename,
        "count": len(documents),
        "documents": documents[:1],
    }


@ingest.post("/insert")
async def insert(file: UploadFile = File(...)):
    pdf_path = await save_pdf(file=file)

    documents = ingest_pdf(str(pdf_path))

    await store_embeddings(documents=documents)

    return {
        "filename": file.filename,
        "count": len(documents),
        "message": "PDF processed and embeddings inserted into MongoDB",
    }
