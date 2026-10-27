# app/services/job_service.py
"""
Shared helpers for job-related operations.

These functions encapsulate reusable DB logic consumed by multiple
route handlers (actions, approvals, history).
"""

from fastapi import HTTPException
from psycopg import Connection

from app.services.auth_service import authorize_user


def get_approval_requirement(cur, action: str):
    """
    Return the approval rule for an action, or None if the action does
    not require approval.
    """
    cur.execute(
        """
        SELECT action, approvals_required
        FROM action_approval_rules
        WHERE action = %s;
        """,
        (action,),
    )
    return cur.fetchone()


def record_job_event(
    cur,
    *,
    job_id: int,
    actor_id: int,
    action: str,
    from_stage,
    to_stage,
    outcome: str,
    grant_id: int | None,
    reason: str | None,
):
    """Insert an immutable audit row into job_events."""
    cur.execute(
        """
        INSERT INTO job_events (
            job_id,
            actor_id,
            action,
            from_stage,
            to_stage,
            outcome,
            grant_id,
            reason
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """,
        (
            job_id,
            actor_id,
            action,
            from_stage,
            to_stage,
            outcome,
            grant_id,
            reason,
        ),
    )


def execute_transition(
    *,
    cur,
    db: Connection,
    job_id: int,
    user_id: int,
    action: str,
    reason: str | None,
    authorization: dict,
):
    """
    Execute one state-changing action after authorization has already
    succeeded.

    The job row is locked before changing it and version is incremented.
    """

    cur.execute(
        """
        SELECT
            j.id,
            j.stage,
            j.version,
            a.to_stage
        FROM jobs j
        JOIN actions a
          ON a.code = %s
        WHERE j.id = %s
        FOR UPDATE;
        """,
        (action, job_id),
    )

    row = cur.fetchone()

    if not row:
        raise HTTPException(
            status_code=404,
            detail="Job or action not found.",
        )

    if row["to_stage"] is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Action '{action}' is not configured as a "
                "state-changing action."
            ),
        )

    from_stage = row["stage"]
    to_stage = row["to_stage"]

    # Re-authorize after locking the job so that a concurrent state
    # change cannot make the earlier decision stale.
    fresh_decision = authorize_user(
        db=db,
        user_id=user_id,
        action=action,
        job_id=job_id,
    )

    if not fresh_decision["allowed"]:
        record_job_event(
            cur,
            job_id=job_id,
            actor_id=user_id,
            action=action,
            from_stage=from_stage,
            to_stage=to_stage,
            outcome="denied",
            grant_id=None,
            reason=fresh_decision["reason"],
        )

        raise HTTPException(
            status_code=403,
            detail=fresh_decision,
        )

    cur.execute(
        """
        UPDATE jobs
        SET
            stage = %s,
            version = version + 1
        WHERE id = %s;
        """,
        (to_stage, job_id),
    )

    record_job_event(
        cur,
        job_id=job_id,
        actor_id=user_id,
        action=action,
        from_stage=from_stage,
        to_stage=to_stage,
        outcome="allowed",
        grant_id=fresh_decision["grant_id"],
        reason=reason,
    )

    return {
        "job_id": job_id,
        "action": action,
        "from_stage": from_stage,
        "to_stage": to_stage,
        "grant_id": fresh_decision["grant_id"],
    }
