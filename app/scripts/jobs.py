from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from psycopg import Connection
from datetime import datetime

from app.database import get_db
from app.scripts.auth import authorize_user


router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


# ---------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------

class JobActionRequest(BaseModel):
    user_id: int
    action: str
    reason: str | None = None


class ApprovalRequest(BaseModel):
    user_id: int
    action: str
    reason: str


class ApprovalDecisionRequest(BaseModel):
    user_id: int
    decision: Literal["approved", "rejected"]


# ---------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------

def _get_approval_requirement(
    cur,
    action: str,
):
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


def _record_job_event(
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


def _execute_transition(
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
        _record_job_event(
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

    _record_job_event(
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


# ---------------------------------------------------------------------
# Waiting jobs
# ---------------------------------------------------------------------

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


# ---------------------------------------------------------------------
# Request approval for a risky action
# ---------------------------------------------------------------------

@router.post("/{job_id}/approvals/request")
def request_approval(
    job_id: int,
    payload: ApprovalRequest,
    db: Connection = Depends(get_db),
):
    """
    Create a pending approval request for an action that is configured
    in action_approval_rules.

    The requester must already be authorized to perform the action.
    No job state is changed at this point.
    """

    try:
        with db.cursor() as cur:

            # 1. Confirm that this action requires approval.
            approval_rule = _get_approval_requirement(
                cur,
                payload.action,
            )

            if not approval_rule:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Action '{payload.action}' does not require "
                        "approval. Use the normal action endpoint."
                    ),
                )

            # The current approvals table supports one independent
            # decision per approval request.
            if approval_rule["approvals_required"] != 1:
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Current approval workflow supports exactly "
                        "one independent approver."
                    ),
                )

            # 2. Requester must actually be authorized for the action.
            decision = authorize_user(
                db=db,
                user_id=payload.user_id,
                action=payload.action,
                job_id=job_id,
            )

            if not decision["allowed"]:
                raise HTTPException(
                    status_code=403,
                    detail=decision,
                )

            # 3. Avoid duplicate pending requests by the same requester.
            cur.execute(
                """
                SELECT id
                FROM approvals
                WHERE job_id = %s
                  AND action = %s
                  AND requested_by = %s
                  AND status = 'pending'
                ORDER BY id DESC
                LIMIT 1;
                """,
                (
                    job_id,
                    payload.action,
                    payload.user_id,
                ),
            )

            existing = cur.fetchone()

            if existing:
                return {
                    "status": "skipped",
                    "message": "A pending approval request already exists.",
                    "approval_id": existing["id"],
                }

            # 4. Create the request.
            cur.execute(
                """
                INSERT INTO approvals (
                    job_id,
                    action,
                    requested_by,
                    reason,
                    status
                )
                VALUES (%s, %s, %s, %s, 'pending')
                RETURNING id, job_id, action, requested_by, status;
                """,
                (
                    job_id,
                    payload.action,
                    payload.user_id,
                    payload.reason,
                ),
            )

            approval = cur.fetchone()

            db.commit()

            return {
                "status": "success",
                "approval": approval,
                "message": "Approval request created.",
            }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------
# Second person approves/rejects.
#
# If approved, the requested action is executed in the SAME transaction.
# This avoids leaving an old approved request that could later be reused.
# ---------------------------------------------------------------------

@router.post("/approvals/{approval_id}/decide")
def decide_approval(
    approval_id: int,
    payload: ApprovalDecisionRequest,
    db: Connection = Depends(get_db),
):
    """
    A second authorized user approves or rejects the request.

    If approved:
      1. approver must be different from requester
      2. approver must independently be authorized for the same action
      3. requester is re-authorized
      4. job transition is executed immediately
      5. job_event is written

    Approval decision + job transition + audit event are atomic.
    """

    try:
        with db.cursor() as cur:

            # 1. Lock the approval request.
            cur.execute(
                """
                SELECT
                    id,
                    job_id,
                    action,
                    requested_by,
                    reason,
                    decided_by,
                    status
                FROM approvals
                WHERE id = %s
                FOR UPDATE;
                """,
                (approval_id,),
            )

            approval = cur.fetchone()

            if not approval:
                raise HTTPException(
                    status_code=404,
                    detail="Approval request not found.",
                )

            if approval["status"] != "pending":
                raise HTTPException(
                    status_code=409,
                    detail=(
                        f"Approval request has already been "
                        f"{approval['status']}."
                    ),
                )

            # 2. Enforce the two-person rule.
            if payload.user_id == approval["requested_by"]:
                raise HTTPException(
                    status_code=403,
                    detail="Requester cannot decide their own approval request.",
                )

            # 3. The second person must independently have authority
            #    for the same action on the same job.
            decision_action = (
                "approve"
                if payload.decision == "approved"
                else "reject"
            )

            approver_decision = authorize_user(
                db=db,
                user_id=payload.user_id,
                action=decision_action,
                job_id=approval["job_id"],
            )

            if not approver_decision["allowed"]:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "message": f"User is not authorized to {decision_action} this request.",
                        "authorization": approver_decision,
                    },
                )

            # ---------------------------------------------------------
            # Rejection: record decision, but do not change the job.
            # ---------------------------------------------------------
            if payload.decision == "rejected":
                cur.execute(
                    """
                    UPDATE approvals
                    SET
                        status = 'rejected',
                        decided_by = %s
                    WHERE id = %s;
                    """,
                    (
                        payload.user_id,
                        approval_id,
                    ),
                )

                db.commit()

                return {
                    "status": "rejected",
                    "approval_id": approval_id,
                    "job_id": approval["job_id"],
                    "action": approval["action"],
                    "decided_by": payload.user_id,
                    "message": "Approval request rejected. Job was not changed.",
                }

            # ---------------------------------------------------------
            # Approval: requester must STILL be authorized now.
            # ---------------------------------------------------------
            requester_decision = authorize_user(
                db=db,
                user_id=approval["requested_by"],
                action=approval["action"],
                job_id=approval["job_id"],
            )

            if not requester_decision["allowed"]:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": (
                            "Approval cannot be executed because the "
                            "requester is no longer authorized."
                        ),
                        "authorization": requester_decision,
                    },
                )

            # 4. Mark the approval approved.
            cur.execute(
                """
                UPDATE approvals
                SET
                    status = 'approved',
                    decided_by = %s
                WHERE id = %s;
                """,
                (
                    payload.user_id,
                    approval_id,
                ),
            )

            # 5. Execute the action immediately in the same transaction.
            transition = _execute_transition(
                cur=cur,
                db=db,
                job_id=approval["job_id"],
                user_id=approval["requested_by"],
                action=approval["action"],
                reason=approval["reason"],
                authorization=requester_decision,
            )

            db.commit()

            return {
                "status": "approved",
                "approval_id": approval_id,
                "requested_by": approval["requested_by"],
                "decided_by": payload.user_id,
                "message": "Approval granted and job action executed.",
                "transition": transition,
            }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise


# ---------------------------------------------------------------------
# Normal job action endpoint
# ---------------------------------------------------------------------

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
            approval_rule = _get_approval_requirement(
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

                    _record_job_event(
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

            transition = _execute_transition(
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


# ---------------------------------------------------------------------
# Job history
# ---------------------------------------------------------------------

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
