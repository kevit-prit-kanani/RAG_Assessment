# RAG Assessment

A PDF-based retrieval-augmented generation (RAG) API built with **FastAPI** and
managed with **uv**. It extracts and chunks PDF content, creates embeddings,
stores chunks in MongoDB, and answers questions using keyword and vector
retrieval. **LiteLLM Proxy** provides the model API, and **Langfuse** receives
LLM traces.

## How it works

1. Upload a PDF to the ingestion API. The service extracts text, splits it into
   chunks, creates embeddings through LiteLLM, and stores the chunks in MongoDB.
2. Send a question to the chat API. LiteLLM routes the question and creates
   query embeddings; MongoDB performs keyword and vector searches; the results
   are combined and passed to the model for a document-grounded answer.
3. LLM calls are instrumented with Langfuse.

## Requirements

- Python 3.14 (see `.python-version`)
- [uv](https://docs.astral.sh/uv/)
- Docker Engine or Docker Desktop with the Docker Compose plugin
- A MongoDB deployment that supports MongoDB Vector Search and Atlas Search
  (MongoDB Atlas is suitable)
- The companion LiteLLM Proxy Compose project and its configuration
- API credentials/configuration for the model provider and Langfuse

MongoDB runs separately from this repository's Compose services. Configure a
MongoDB connection string with access to a database and collection. The vector
search index is created by the application when documents are inserted. Create
the Atlas Search text index named by `MONGODB_SEARCH_INDEX` on the chunks
collection, with the `text` field indexed, before using keyword search.

## Get the repositories

Clone this project:

```bash
git clone https://github.com/kevit-prit-kanani/RAG_Assessment.git
cd RAG_Assessment
```

The root `compose.yaml` also includes a separate LiteLLM Proxy Compose file at
`../../../litellm-proxy/docker-compose.quickstart.yml`. The helper script
`dev.sh` expects that proxy checkout at `$HOME/litellm-proxy` by default, with
its own `.env` file. If you do not already have the proxy repository, clone
the proxy repository used by your deployment:

```bash
git clone <LITELLM_PROXY_REPOSITORY_URL> "$HOME/litellm-proxy"
```

Place the proxy checkout where the Compose include path resolves (or update
that include path if you keep it elsewhere), and configure the proxy according
to its own setup instructions before starting this application.

## Configure environment variables

Create the application environment file from the checked-in template:

```bash
cp .env.example .env
```

Edit `.env` and provide real values for the following:

| Variable                      | Purpose                                                                   |
| ----------------------------- | ------------------------------------------------------------------------- |
| `OPENAI_API_KEY`              | Model-provider credential, if required by the configured LiteLLM provider |
| `OPENAI_EMBEDDING_MODEL`      | Embedding model used for PDF and query embeddings                         |
| `OPENAI_EMBEDDING_DIMENSIONS` | Embedding vector size; must match the MongoDB vector index                |
| `OPENAI_CHAT_MODEL`           | Chat model configured in LiteLLM                                          |
| `MONGODB_URI`                 | MongoDB connection string                                                 |
| `MONGODB_DB`                  | Database name                                                             |
| `MONGODB_CHUNKS_COLLECTION`   | Collection where chunks and embeddings are stored                         |
| `MONGODB_VECTOR_INDEX`        | MongoDB Vector Search index name                                          |
| `MONGODB_VECTOR_DIMENSIONS`   | Vector index dimensions; keep consistent with the embedding model         |
| `MONGODB_SEARCH_INDEX`        | MongoDB Atlas Search text index name                                      |
| `LANGFUSE_SECRET_KEY`         | Langfuse secret key                                                       |
| `LANGFUSE_PUBLIC_KEY`         | Langfuse public key                                                       |
| `LANGFUSE_BASE_URL`           | Langfuse server URL                                                       |
| `LITELLM_PROXY_API_BASE`      | LiteLLM Proxy URL                                                         |
| `LITELLM_PROXY_API_KEY`       | Virtual key accepted by the LiteLLM Proxy                                 |

Use the model names and credentials configured by your LiteLLM Proxy. The
Compose service sets `LITELLM_PROXY_API_BASE` to `http://litellm:4000` for
container-to-container requests; `localhost` in the template is for running the
application directly on your host. The application `.env` and the proxy
repository's `.env` are separate files. Do not commit either `.env` file.

## Install dependencies with uv

Install uv if it is not already available:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Install the required Python version and, from the repository root, the locked
project dependencies:

```bash
uv python install 3.14
uv sync --locked
```

To run the API directly on the host after configuring `.env` and starting an
accessible LiteLLM Proxy:

```bash
uv run uvicorn main:main --reload
```

The API is then available at `http://localhost:8000`; interactive API
documentation is at `http://localhost:8000/docs`.

## Run with Docker Compose

Ensure the companion proxy Compose project and its `.env` are set up, and that
MongoDB is reachable using the URI in this project's `.env`. From this
repository root:

```bash
docker compose up --build
```

Compose builds the FastAPI image, starts the LiteLLM Proxy services included
from the companion Compose project, waits for LiteLLM readiness, then starts
the API on port `8000`. The source and `PDF/` directory are mounted for local
development. To stop the services:

```bash
docker compose down
```

## Run the API from the Dockerfile

Build and start the API without Compose:

```bash
docker build -t rag .
docker run --rm --env-file .env -p 8000:8000 rag
```

Open `http://localhost:8000/docs` in a browser. The container listens on
`0.0.0.0` so Docker can forward its port; `0.0.0.0` is not the browser URL.
`--env-file` passes the settings into the container, so mounting `.env` into
`/app/.env` is not necessary.

## API usage

Open `http://localhost:8000/docs` to try the endpoints interactively.

### Ingest a PDF

Preview the first processed chunk without storing it:

```bash
curl -X POST http://localhost:8000/ingest/preview \
  -F "file=@./PDF/2. PGDM Healthcare Brochure_final_Open_new_addition_artwork.pdf"
```

Process the PDF and insert its chunks and embeddings into MongoDB:

```bash
curl -X POST http://localhost:8000/ingest/insert \
  -F "file=@./PDF/2. PGDM Healthcare Brochure_final_Open_new_addition_artwork.pdf"
```

### Ask a question

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What does the document say about the program?",
    "conversation_id": "demo-conversation"
  }'
```

The response includes an `interaction_id`, `conversation_id`, answer text, and
a confidence score for document-grounded answers. A new conversation ID is
generated when one is not provided.

### Check MongoDB connectivity

```bash
curl http://localhost:8000/get_db_ping
```

## Project structure

This tree lists repository files that are not excluded by `.gitignore`. It
omits ignored files such as `.env`, `.venv/`, Python bytecode, and `logs/`.

```text
.
├── .dockerignore
├── .env.example
├── .gitignore
├── .python-version
├── Dockerfile
├── PDF/
│   └── 2. PGDM Healthcare Brochure_final_Open_new_addition_artwork.pdf
├── README.md
├── compose.yaml
├── dev.sh
├── main.py
├── pyproject.toml
├── src/
│   ├── app.py
│   └── rag/
│       ├── __init__.py
│       └── app/
│           ├── api/
│           │   ├── chat.py
│           │   ├── ingest.py
│           │   └── search.py
│           ├── core/
│           │   ├── config.py
│           │   └── llm.py
│           ├── db/
│           │   └── mongodb.py
│           ├── ingestion/
│           │   └── chunker.py
│           └── schemas/
│               └── chat.py
└── uv.lock
```

### Golden Dataset

```link
https://docs.google.com/spreadsheets/d/1ZQYzO-VY232Oph9RqVVdaDPKqMha52qXq5RYK-McC5U/edit?usp=sharing
```
