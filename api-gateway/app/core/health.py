from fastapi import APIRouter


router = APIRouter(tags=["Проверка приложения"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

