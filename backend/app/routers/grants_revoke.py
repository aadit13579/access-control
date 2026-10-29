"""POST /api/grants/{grant_id}/revoke — revoke an active grant."""

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.database import get_db
from app.models import RevokeGrantRequest

router = APIRouter(prefix="/api/grants", tags=["Grants"])


@router.post("/{grant_id}/revoke")
def revoke_grant(
    grant_id: int,
    payload: RevokeGrantRequest,
    db: Connection = Depends(get_db),
):
    try:
        with db.cursor() as cur:
            # 1. Lock and check active status
            grant_query = """
            SELECT
                id,
                user_id,
                role_code,
                client_id,
                client_all,
                branch_id,
                branch_all,
                direction,
                direction_all,
                mode,
                mode_all,
                revoked_by,
                (
                    CURRENT_TIMESTAMP >= valid_from
                    AND CURRENT_TIMESTAMP < valid_to
                    AND revoked_by IS NULL
                ) AS is_active
            FROM grants
            WHERE id = %s
            FOR UPDATE;
            """

            cur.execute(grant_query, (grant_id,))
            grant = cur.fetchone()

            if not grant:
                raise HTTPException(
                    status_code=404,
                    detail="Grant not found.",
                )

            if not grant["is_active"]:
                return {
                    "status": "skipped",
                    "message": "Grant is already expired or revoked.",
                    "grant_id": grant_id,
                }

            # 2. Check manager authority and scope coverage
            auth_query = """
            SELECT EXISTS (
                SELECT 1
                FROM grants g
                JOIN role_permissions rp
                  ON rp.role_code = g.role_code
                JOIN role_grant_authority rga
                  ON rga.manager_role = g.role_code
                WHERE g.user_id = %s
                  AND rp.action = 'manage_grants'
                  AND rga.grantable_role = %s
                  AND CURRENT_TIMESTAMP >= g.valid_from
                  AND CURRENT_TIMESTAMP < g.valid_to
                  AND g.revoked_by IS NULL
                  AND (g.client_all OR (%s = FALSE AND g.client_id = %s))
                  AND (g.branch_all OR (%s = FALSE AND g.branch_id = %s))
                  AND (g.direction_all OR (%s = FALSE AND g.direction = %s))
                  AND (g.mode_all OR (%s = FALSE AND g.mode = %s))
            );
            """

            cur.execute(
                auth_query,
                (
                    payload.manager_id,
                    grant["role_code"],
                    grant["client_all"],
                    grant["client_id"],
                    grant["branch_all"],
                    grant["branch_id"],
                    grant["direction_all"],
                    grant["direction"],
                    grant["mode_all"],
                    grant["mode"],
                ),
            )

            is_authorized = cur.fetchone()["exists"]

            if not is_authorized:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Manager lacks authority to revoke this role "
                        "or the grant is outside the manager's own scope."
                    ),
                )

            # 3. Revoke the grant immediately
            revoke_query = """
            UPDATE grants
            SET
                valid_to = CURRENT_TIMESTAMP,
                revoked_by = %s
            WHERE id = %s
            RETURNING
                id,
                user_id,
                role_code,
                client_id,
                client_all,
                branch_id,
                branch_all,
                direction,
                direction_all,
                mode,
                mode_all,
                valid_from,
                valid_to,
                revoked_by;
            """

            cur.execute(revoke_query, (payload.manager_id, grant_id))
            revoked_grant = cur.fetchone()

            # 4. Record immutable revocation history
            event_query = """
            INSERT INTO grant_events (
                grant_id,
                target_user_id,
                action,
                role_code,
                client_id,
                client_all,
                branch_id,
                branch_all,
                direction,
                direction_all,
                mode,
                mode_all,
                valid_from,
                valid_to,
                actor_id,
                reason
            )
            VALUES (
                %s, %s, 'revoke', %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s
            );
            """

            cur.execute(
                event_query,
                (
                    revoked_grant["id"],
                    revoked_grant["user_id"],
                    revoked_grant["role_code"],
                    revoked_grant["client_id"],
                    revoked_grant["client_all"],
                    revoked_grant["branch_id"],
                    revoked_grant["branch_all"],
                    revoked_grant["direction"],
                    revoked_grant["direction_all"],
                    revoked_grant["mode"],
                    revoked_grant["mode_all"],
                    revoked_grant["valid_from"],
                    revoked_grant["valid_to"],
                    payload.manager_id,
                    payload.reason,
                ),
            )

            db.commit()

            return {
                "status": "success",
                "grant_id": grant_id,
                "revoked_by": payload.manager_id,
                "valid_to": revoked_grant["valid_to"],
                "message": "Grant revoked successfully.",
            }

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
