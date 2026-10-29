"""
Approval workflow endpoints:
  - POST /api/jobs/{job_id}/approvals/request
  - POST /api/jobs/approvals/{approval_id}/decide
"""

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.database import get_db
from app.models import ApprovalDecisionRequest, ApprovalRequest
from app.services.auth_service import authorize_user
from app.services.job_service import (
    execute_transition,
    get_approval_requirement,
)

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.post("/{job_id}/approvals/request")
def request_approval(
    job_id: int,
    payload: ApprovalRequest,
    db: Connection = Depends(get_db),
):
    """
    Create a pending approval request for an action configured in action_approval_rules.

    The requester must already be authorized. No job state changes at this point.
    """
    try:
        with db.cursor() as cur:
            # 1. Confirm that this action requires approval
            approval_rule = get_approval_requirement(cur, payload.action)

            if not approval_rule:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Action '{payload.action}' does not require "
                        "approval. Use the normal action endpoint."
                    ),
                )

            if approval_rule["approvals_required"] != 1:
                raise HTTPException(
                    status_code=500,
                    detail="Current approval workflow supports exactly one independent approver.",
                )

            # 2. Requester must be authorized for the action
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

            # 3. Deduplicate pending requests by the same requester
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
                (job_id, payload.action, payload.user_id),
            )
            existing = cur.fetchone()

            if existing:
                return {
                    "status": "skipped",
                    "message": "A pending approval request already exists.",
                    "approval_id": existing["id"],
                }

            # 4. Create the request
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


@router.post("/approvals/{approval_id}/decide")
def decide_approval(
    approval_id: int,
    payload: ApprovalDecisionRequest,
    db: Connection = Depends(get_db),
):
    """
    A second authorized user approves or rejects the request.

    If approved:
      1. Approver must differ from requester (two-person rule)
      2. Approver must independently be authorized to approve/reject
      3. Requester is re-authorized at decision time
      4. Job transition executes atomically
    """
    try:
        with db.cursor() as cur:
            # 1. Lock the approval request
            cur.execute(
                """
                SELECT id, job_id, action, requested_by, reason, decided_by, status
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
                    detail=f"Approval request has already been {approval['status']}.",
                )

            # 2. Enforce two-person rule
            if payload.user_id == approval["requested_by"]:
                raise HTTPException(
                    status_code=403,
                    detail="Requester cannot decide their own approval request.",
                )

            # 3. Approver must hold approve/reject permission
            decision_action = (
                "approve" if payload.decision == "approved" else "reject"
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

            # Rejection: record decision without changing job
            if payload.decision == "rejected":
                cur.execute(
                    """
                    UPDATE approvals
                    SET status = 'rejected', decided_by = %s
                    WHERE id = %s;
                    """,
                    (payload.user_id, approval_id),
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

            # Approval: requester must STILL be authorized
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

            # 4. Mark approved
            cur.execute(
                """
                UPDATE approvals
                SET status = 'approved', decided_by = %s
                WHERE id = %s;
                """,
                (payload.user_id, approval_id),
            )

            # 5. Execute state transition atomically
            transition = execute_transition(
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
