import hashlib

import litellm
import tiktoken
from unstructured.chunking.title import chunk_by_title
from unstructured.partition.pdf import partition_pdf

from src.rag.app.core.config import get_settings

settings = get_settings()

TOKENIZER_MODEL = settings.openai_embedding_model
EMBEDDING_MODEL = "openai/" + TOKENIZER_MODEL


def file_hash(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def tokenize(text: str):
    try:
        encoder = tiktoken.encoding_for_model(TOKENIZER_MODEL)
    except KeyError:
        encoder = tiktoken.get_encoding("cl100k_base")
    return len(encoder.encode(text=text))


def ingest_pdf(path: str) -> list[dict]:
    document_id = file_hash(path=path)

    # 1. Partition
    elements = partition_pdf(
        filename=path,
        strategy="hi_res",
        infer_table_structure=True,
    )

    chunks = chunk_by_title(
        elements=elements,
        max_characters=1800,
        new_after_n_chars=1400,
        combine_text_under_n_chars=1000,
        multipage_sections=False,
        overlap=150,
        overlap_all=False,
        include_orig_elements=False,
    )

    documents = []

    for index, chunk in enumerate(chunks):
        text = (chunk.text or "").strip()

        if not text:
            continue

        metadata = getattr(chunk, "metadata", None)
        page_number = getattr(metadata, "page_numver", None) if metadata else None
        documents.append(
            {
                "document_id": document_id,
                "chunk_id": f"{document_id}:{index}",
                "chunk_index": index,
                "text": text,
                "token_count": tokenize(text),
                "character_count": len(text),
                "embedding": None,
                "embedding_model": None,
                "embedding_dimensions": None,
                "metadata": {
                    "source": {
                        "filename": path.split("/")[-1],
                        "mime_type": "application/pdf",
                    },
                    "location": {
                        "page_start": page_number,
                        "page_end": page_number,
                    },
                    "structure": {"element_type": type(chunk).__name__},
                },
                "chunking": {
                    "strategy": "by_title",
                    "max_characters": 1800,
                    "new_after_n_chars": 1400,
                },
                "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            }
        )
    texts = [document["text"] for document in documents]
    response = litellm.embedding(model=EMBEDDING_MODEL, input=texts)
    vectors = [item["embedding"] for item in response.data]

    # 5. Attach embeddings
    for document, vector in zip(
        documents,
        vectors,
    ):
        document["embedding"] = vector
        document["embedding_model"] = EMBEDDING_MODEL
        document["embedding_dimensions"] = len(vector)
    return documents