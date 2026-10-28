# app/routers/auth.py
"""POST /api/{user_id} — single authorization check."""

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.database import get_db

router = APIRouter(prefix="/api", tags=["Users"])


@router.get("/users")
def get_all_users(
    db: Connection = Depends(get_db)
):
    try:
        with db.cursor() as cur:
            cur.execute(
                """
                SELECT id, name, kind, client_id
                FROM users
                WHERE is_active = true;
                """
            )
            action_row = cur.fetchall()

        if not action_row:
            raise HTTPException(status_code=404, detail="Users not found or inactive.")

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
    

