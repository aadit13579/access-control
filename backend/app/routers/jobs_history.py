# app/routers/jobs_history.py
"""
GET /api/jobs/{job_id}/history     — audit trail for a job
GET /api/jobs/{job_id}/who-could-act — historical access query
"""

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection
from datetime import datetime

from app.database import get_db

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.get("/{job_id}/history")
def job_history(
    job_id: int,
    db: Connection = Depends(get_db),
):
    query = """
    SELECT
        je.id,
        je.actor_id,
        u.name AS actor_name,
        je.action,
        je.from_stage,
        je.to_stage,
        je.outcome,
        je.grant_id,
        je.reason,
        je.at
    FROM job_events je
    JOIN users u
      ON u.id = je.actor_id
    WHERE je.job_id = %s
    ORDER BY je.at ASC, je.id ASC;
    """

    with db.cursor() as cur:
        cur.execute(query, (job_id,))

        return {
            "job_id": job_id,
            "history": cur.fetchall(),
        }


@router.get("/{job_id}/who-could-act")
def who_could_act(
    job_id: int,
    action: str,
    at: datetime,
    db: Connection = Depends(get_db)
):
    with db.cursor() as cur:

        # ---------------------------------------------------------
        # 1. Get the job whose historical access we are checking
        # ---------------------------------------------------------
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
            WHERE id = %s;
            """,
            (job_id,)
        )

        job = cur.fetchone()

        if not job:
            raise HTTPException(
                status_code=404,
                detail="Job not found."
            )

        # ---------------------------------------------------------
        # 2. Find users whose grants covered this job at that time
        #
        # grants.valid_from / valid_to already preserve the period
        # during which the grant was effective.
        # ---------------------------------------------------------
        query = """
        SELECT DISTINCT
            u.id AS user_id,
            u.name AS user_name,
            g.id AS grant_id,
            g.role_code

        FROM grants g

        JOIN users u
          ON u.id = g.user_id

        WHERE %s >= g.valid_from
          AND %s < g.valid_to

          AND (
              g.client_all
              OR g.client_id = %s
          )

          AND (
              g.branch_all
              OR g.branch_id = %s
          )

          AND (
              g.direction_all
              OR g.direction = %s
          )

          AND (
              g.mode_all
              OR g.mode = %s
          )

          -- -----------------------------------------------------
          -- Historical role permission check
          --
          -- The latest permission change on/before the requested
          -- timestamp must have been 'add'.
          -- -----------------------------------------------------
          AND (
              SELECT rpl.change
              FROM role_permission_log rpl
              WHERE rpl.role_code = g.role_code
                AND rpl.action = %s
                AND rpl.at <= %s
              ORDER BY rpl.at DESC, rpl.id DESC
              LIMIT 1
          ) = 'add'

        ORDER BY u.id;
        """

        cur.execute(
            query,
            (
                at,
                at,

                job["client_id"],
                job["branch_id"],
                job["direction"],
                job["mode"],

                action,
                at,
            )
        )

        users = cur.fetchall()

        return {
            "job_id": job_id,
            "job_ref": job["ref"],
            "action": action,
            "at": at,
            "count": len(users),
            "users": users,
        }
