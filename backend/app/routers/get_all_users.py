"""GET /api/users — list active users."""

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.database import get_db

router = APIRouter(prefix="/api", tags=["Users"])


@router.get("/users")
def get_all_users(
    db: Connection = Depends(get_db),
):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, kind, client_id
            FROM users
            WHERE is_active = true
            ORDER BY id;
            """
        )
        users = cur.fetchall()

    if not users:
        raise HTTPException(status_code=404, detail="No active users found.")

    return {
        "status": "success",
        "data": users,
    }
