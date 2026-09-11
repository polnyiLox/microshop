from typing import Annotated

from fastapi import APIRouter, Depends
from pymongo.asynchronous.database import AsyncDatabase

from app.api.dependencies import get_database


router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_handler(
        database: Annotated[AsyncDatabase, Depends(get_database)],
) -> dict[str, str]:
    await database.command("ping")
    return {
        "status": "ok",
        "mongodb": "ok",
    }
