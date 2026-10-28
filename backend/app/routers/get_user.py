# app/routers/auth.py
"""GET /api/{user_id} ."""

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.database import get_db

router = APIRouter(prefix="/api", tags=["User"])


@router.get("/users/{user_id}")
def get_user_by_id(
    user_id: int,
    db: Connection = Depends(get_db)
):
    try:
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, kind, client_id
                FROM users
                WHERE is_active = true AND id = %s;
                """,
                (user_id,),
            )
            action_row = cur.fetchone()

        if not action_row:
            raise HTTPException(status_code=404, detail="User not found or inactive.")

        result = {
            "status": "success",
            "data": action_row,
        }

        return result

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise
    

