from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from src.rag.app.db.mongodb import db

app = FastAPI()


@app.get("/")
def read_root():
    return RedirectResponse(url="/docs")


@app.get("/get_db_ping")
async def get_db_pint():
    return await db.ping()
