from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/")
def read_root():
    return {"message": "Tea & Coffee Orders API ☕🍵"}
