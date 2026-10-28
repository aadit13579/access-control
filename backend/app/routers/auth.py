# app/routers/auth.py
"""POST /api/auth/authorize — single authorization check."""

from fastapi import APIRouter, Depends
from psycopg import Connection

from app.models import AccessCheckRequest
from app.database import get_db
from app.services.auth_service import authorize_user

router = APIRouter(prefix="/api/auth", tags=["Authorization"])


@router.post("/authorize")
def check_access(
    payload: AccessCheckRequest,
    db: Connection = Depends(get_db)
):
    result = authorize_user(
        db=db,
        user_id=payload.user_id,
        action=payload.action,
        job_id=payload.job_id
    )

    return result
