from fastapi import APIRouter

router = APIRouter()


@router.post("/participant/register")
async def register_participant():
    return {}
