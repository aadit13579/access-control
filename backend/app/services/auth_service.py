"""
Canonical authorization engine.

Used by:
  - POST /api/auth/authorize
  - GET /api/jobs/waiting
  - POST /api/jobs/{job_id}/action
  - POST /api/jobs/{job_id}/approvals/request
  - POST /api/jobs/approvals/{approval_id}/decide

Fail-closed: any unmet condition results in denied access.
"""

from datetime import datetime, timezone
from typing import Any

from psycopg import Connection


def authorize_user(
    db: Connection,
    user_id: int,
    action: str,
    job_id: int,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """
    Evaluate whether `user_id` is permitted to perform `action` on `job_id`
    at `as_of` timestamp (defaults to current UTC time).

    Returns a dict with `allowed` (bool), `reason_code` (str), and `reason` (str).
    """
    if as_of is None:
        as_of = datetime.now(timezone.utc)

    with db.cursor() as cur:
        # 1. User check: exists and active
        cur.execute(
            """
            SELECT id, name, kind, client_id, is_active
            FROM users
            WHERE id = %s;
            """,
            (user_id,),
        )
        user = cur.fetchone()

        if not user:
            return {
                "allowed": False,
                "reason_code": "USER_NOT_FOUND",
                "reason": "Denied: user does not exist.",
            }

        if not user["is_active"]:
            return {
                "allowed": False,
                "reason_code": "USER_INACTIVE",
                "reason": "Denied: user account is inactive.",
            }

        # 2. Job check: exists
        cur.execute(
            """
            SELECT id, ref, client_id, branch_id, direction, mode, stage, owner_id, version
            FROM jobs
            WHERE id = %s;
            """,
            (job_id,),
        )
        job = cur.fetchone()

        if not job:
            return {
                "allowed": False,
                "reason_code": "JOB_NOT_FOUND",
                "reason": "Denied: job does not exist.",
            }

        # 3. Action check: exists
        cur.execute(
            """
            SELECT code, from_stages, to_stage
            FROM actions
            WHERE code = %s;
            """,
            (action,),
        )
        action_row = cur.fetchone()

        if not action_row:
            return {
                "allowed": False,
                "reason_code": "UNKNOWN_ACTION",
                "reason": f"Denied: action '{action}' is not defined.",
            }

        # 4. Stage check: job is in a valid source stage
        if (
            action_row["from_stages"] is not None
            and job["stage"] not in action_row["from_stages"]
        ):
            return {
                "allowed": False,
                "reason_code": "INVALID_STAGE",
                "reason": (
                    f"Denied: action '{action}' cannot be performed "
                    f"while job is in stage '{job['stage']}'."
                ),
                "current_stage": job["stage"],
            }

        # 5. Absence check: user is not absent at evaluation time
        cur.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM absences
                WHERE user_id = %s
                  AND %s >= starts_at
                  AND %s < ends_at
            ) AS absent;
            """,
            (user_id, as_of, as_of),
        )

        if cur.fetchone()["absent"]:
            return {
                "allowed": False,
                "reason_code": "USER_ABSENT",
                "reason": "Denied: user is absent at the requested time.",
            }

        # 6. Grant check: active grant covering job scope and providing action
        cur.execute(
            """
            SELECT
                g.id AS grant_id,
                g.role_code,
                g.client_id,
                g.client_all,
                g.branch_id,
                g.branch_all,
                g.direction,
                g.direction_all,
                g.mode,
                g.mode_all,
                g.granted_by,
                g.revoked_by
            FROM grants g
            JOIN role_permissions rp
              ON rp.role_code = g.role_code
            WHERE g.user_id = %s
              AND rp.action = %s
              AND %s >= g.valid_from
              AND %s < g.valid_to
              AND (g.client_all OR g.client_id = %s)
              AND (g.branch_all OR g.branch_id = %s)
              AND (g.direction_all OR g.direction = %s)
              AND (g.mode_all OR g.mode = %s)
            ORDER BY g.id;
            """,
            (
                user_id,
                action,
                as_of,
                as_of,
                job["client_id"],
                job["branch_id"],
                job["direction"],
                job["mode"],
            ),
        )
        matching_grants = cur.fetchall()

        if not matching_grants:
            return {
                "allowed": False,
                "reason_code": "NO_MATCHING_GRANT",
                "reason": (
                    "Denied: no grant active at the requested time "
                    "provides this action for this job's scope."
                ),
                "job_scope": {
                    "client_id": job["client_id"],
                    "branch_id": job["branch_id"],
                    "direction": str(job["direction"]),
                    "mode": str(job["mode"]),
                },
            }

        # 7. Segregation of duties (SoD) check
        cur.execute(
            """
            SELECT
                sod.blocked_if_actor_did,
                je.id AS event_id,
                je.at
            FROM sod_rules sod
            JOIN job_events je
              ON je.job_id = %s
             AND je.actor_id = %s
             AND je.action = sod.blocked_if_actor_did
             AND je.outcome = 'allowed'
             AND je.at <= %s
            WHERE sod.action = %s
            LIMIT 1;
            """,
            (job_id, user_id, as_of, action),
        )
        sod_violation = cur.fetchone()

        if sod_violation:
            return {
                "allowed": False,
                "reason_code": "SOD_VIOLATION",
                "reason": (
                    f"Denied: user previously performed "
                    f"'{sod_violation['blocked_if_actor_did']}' "
                    f"on this job and may not perform '{action}'."
                ),
                "blocking_event_id": sod_violation["event_id"],
            }

        # 8. Authorized: return grant details and scope
        grant = matching_grants[0]
        scope = {
            "client": (
                "ALL" if grant["client_all"] else f"Client ID: {grant['client_id']}"
            ),
            "branch": (
                "ALL" if grant["branch_all"] else f"Branch ID: {grant['branch_id']}"
            ),
            "direction": (
                "ALL" if grant["direction_all"] else str(grant["direction"])
            ),
            "mode": (
                "ALL" if grant["mode_all"] else str(grant["mode"])
            ),
        }

        return {
            "allowed": True,
            "reason_code": "AUTHORIZED",
            "reason": (
                f"Authorized by Grant #{grant['grant_id']} ({grant['role_code']})."
            ),
            "grant_id": grant["grant_id"],
            "role_code": grant["role_code"],
            "grant_scope": scope,
            "job_stage": job["stage"],
            "as_of": as_of,
        }
