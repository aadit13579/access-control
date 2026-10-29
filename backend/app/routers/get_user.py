"""GET /api/users/{user_id} — get a single active user by ID."""

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.database import get_db

router = APIRouter(prefix="/api", tags=["Users"])


@router.get("/users/{user_id}")
def get_user_by_id(
    user_id: int,
    db: Connection = Depends(get_db),
):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, kind, client_id
            FROM users
            WHERE is_active = true AND id = %s;
            """,
            (user_id,),
        )
        user = cur.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found or inactive.")

    return {
        "status": "success",
        "data": user,
    }
