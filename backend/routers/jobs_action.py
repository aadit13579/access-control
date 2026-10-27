# app/routers/jobs_action.py
"""POST /api/jobs/{job_id}/action — perform a state-changing action."""

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.models import JobActionRequest
from app.database import get_db
from app.services.auth_service import authorize_user
from app.services.job_service import (
    get_approval_requirement,
    record_job_event,
    execute_transition,
)

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.post("/{job_id}/action")
def perform_job_action(
    job_id: int,
    payload: JobActionRequest,
    db: Connection = Depends(get_db),
):
    """
    Perform a state-changing action.

    If action_approval_rules says the action requires approval, this
    endpoint refuses to bypass the approval workflow and directs the
    caller to create an approval request instead.
    """

    try:
        with db.cursor() as cur:

            # 1. If approval is required, do not bypass it.
            approval_rule = get_approval_requirement(
                cur,
                payload.action,
            )

            if approval_rule:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": (
                            f"Action '{payload.action}' requires "
                            "independent approval."
                        ),
                        "approval_request_endpoint": (
                            f"/api/jobs/{job_id}/approvals/request"
                        ),
                    },
                )

            # 2. Normal authorization.
            decision = authorize_user(
                db=db,
                user_id=payload.user_id,
                action=payload.action,
                job_id=job_id,
            )

            if not decision["allowed"]:
                # Obtain current stage for the denial audit record.
                cur.execute(
                    """
                    SELECT stage
                    FROM jobs
                    WHERE id = %s;
                    """,
                    (job_id,),
                )

                job = cur.fetchone()

                if job:
                    cur.execute(
                        """
                        SELECT to_stage
                        FROM actions
                        WHERE code = %s;
                        """,
                        (payload.action,),
                    )
                    action_row = cur.fetchone()

                    record_job_event(
                        cur,
                        job_id=job_id,
                        actor_id=payload.user_id,
                        action=payload.action,
                        from_stage=job["stage"],
                        to_stage=(
                            action_row["to_stage"]
                            if action_row
                            else None
                        ),
                        outcome="denied",
                        grant_id=None,
                        reason=decision["reason"],
                    )

                    db.commit()

                raise HTTPException(
                    status_code=403,
                    detail=decision,
                )

            transition = execute_transition(
                cur=cur,
                db=db,
                job_id=job_id,
                user_id=payload.user_id,
                action=payload.action,
                reason=payload.reason,
                authorization=decision,
            )

            db.commit()

            return {
                "status": "success",
                "transition": transition,
            }

    except HTTPException:
        # If a denied action was deliberately committed above for audit,
        # rollback here is harmless because there is no open transaction.
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise
