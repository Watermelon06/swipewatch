from fastapi import APIRouter

from ..deps import Db
from ..models import User
from ..security import make_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/anon")
async def anon(db: Db):
    user = User()
    db.add(user)
    await db.commit()
    return {"token": make_token(user.id), "user_id": str(user.id)}
