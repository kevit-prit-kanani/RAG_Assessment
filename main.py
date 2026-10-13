from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from rag.app.core.config import get_settings
from rag.app.core.llm import config_litellm
from src.app import app
from src.rag.app.db.mongodb import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    config_litellm(get_settings())
    yield


main = FastAPI(lifespan=lifespan)

main.include_router(app)
main.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict in production to your actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@main.get("/")
def read_root():
    return RedirectResponse(url="/docs")


@main.get("/get_db_ping")
async def get_db_pint():
    return await db.ping()
