from fastapi import FastAPI
from app.core.database.seed import seed
from app.features.auth.router import auth
from app.features.users.router import users
from app.features.notebooks.router import notebooks
from app.core.lifespan import lifespan
import asyncio


def create_app():
    app = FastAPI(lifespan=lifespan)
    seed()
    app.include_router(auth)
    app.include_router(users)
    app.include_router(notebooks)

    return app


app = create_app()


@app.get("/")
async def root():
    return {
        "message": "Hello World! Notatnik API działa.",
        "docs": "Wejdź na /docs żeby zobaczyć dokumentację Swagger",
    }
