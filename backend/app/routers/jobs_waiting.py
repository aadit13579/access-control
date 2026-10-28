# app/routers/jobs_waiting.py
"""GET /api/jobs/waiting — list jobs a user may act on."""

from fastapi import APIRouter, Depends
from psycopg import Connection

from app.database import get_db
from app.services.auth_service import authorize_user

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.get("/waiting")
def list_jobs_waiting(
    user_id: int,
    action: str,
    db: Connection = Depends(get_db),
):
    """
    Return only jobs for which the canonical authorization engine says
    the user may currently perform `action`.
    """

    with db.cursor() as cur:
        cur.execute(
            """
            SELECT
                id,
                ref,
                client_id,
                branch_id,
                direction,
                mode,
                stage
            FROM jobs
            ORDER BY id;
            """
        )
        candidates = cur.fetchall()

    jobs = []

    for job in candidates:
        decision = authorize_user(
            db=db,
            user_id=user_id,
            action=action,
            job_id=job["id"],
        )

        if decision["allowed"]:
            jobs.append(
                {
                    "id": job["id"],
                    "ref": job["ref"],
                    "client_id": job["client_id"],
                    "branch_id": job["branch_id"],
                    "direction": job["direction"],
                    "mode": job["mode"],
                    "stage": job["stage"],
                    "grant_id": decision["grant_id"],
                    "role_code": decision["role_code"],
                }
            )

    return {
        "user_id": user_id,
        "action": action,
        "count": len(jobs),
        "jobs": jobs,
    }
