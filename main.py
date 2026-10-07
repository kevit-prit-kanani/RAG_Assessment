from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from src.app import app
from src.rag.app.db.mongodb import db

main = FastAPI()

main.include_router(app)


@main.get("/")
def read_root():
    return RedirectResponse(url="/docs")


@main.get("/get_db_ping")
async def get_db_pint():
    return await db.ping()
