"""GET /api/actions — list all actions with stage transitions and approval rules."""

from fastapi import APIRouter, Depends
from psycopg import Connection

from app.database import get_db

router = APIRouter(prefix="/api", tags=["Actions"])


@router.get("/actions")
def get_actions(
    db: Connection = Depends(get_db),
):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                a.code,
                a.from_stages,
                a.to_stage,
                COALESCE(aar.approvals_required, 0) AS approvals_required
            FROM actions a
            LEFT JOIN action_approval_rules aar
                ON aar.action = a.code
            ORDER BY a.code;
            """
        )
        rows = cur.fetchall()

    return {
        "actions": [
            {
                "code": row["code"],
                "from_stages": row["from_stages"],
                "to_stage": row["to_stage"],
                "approvals_required": row["approvals_required"],
            }
            for row in rows
        ]
    }
