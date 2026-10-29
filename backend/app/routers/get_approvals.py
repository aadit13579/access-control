"""GET /api/approvals — list pending approval requests."""

from fastapi import APIRouter, Depends
from psycopg import Connection

from app.database import get_db

router = APIRouter(prefix="/api", tags=["Approvals"])


@router.get("/approvals")
def get_approvals(
    db: Connection = Depends(get_db),
):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT id, job_id, action, requested_by, reason, decided_by
            FROM approvals
            WHERE status = 'pending'
            ORDER BY job_id, id;
            """
        )
        rows = cur.fetchall()

    return {
        "approvals": [
            {
                "id": row["id"],
                "job_id": row["job_id"],
                "action": row["action"],
                "requested_by": row["requested_by"],
                "reason": row["reason"],
                "decided_by": row["decided_by"],
            }
            for row in rows
        ]
    }
