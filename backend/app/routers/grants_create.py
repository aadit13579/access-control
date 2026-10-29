"""POST /api/grants/ — create a new scoped role grant."""

from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.database import get_db
from app.models import GrantRoleRequest

router = APIRouter(prefix="/api/grants", tags=["Grants"])


@router.post("/")
def create_grant(
    payload: GrantRoleRequest,
    db: Connection = Depends(get_db),
):
    if payload.manager_id == payload.target_user_id:
        raise HTTPException(
            status_code=403,
            detail="Users may not grant roles to themselves.",
        )

    c_all = payload.client_id is None
    b_all = payload.branch_id is None
    d_all = payload.direction is None
    m_all = payload.mode is None

    try:
        with db.cursor() as cur:
            # 1. Check authority and delegation scope
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
                    payload.role_code,
                    c_all,
                    payload.client_id,
                    b_all,
                    payload.branch_id,
                    d_all,
                    payload.direction,
                    m_all,
                    payload.mode,
                ),
            )

            is_authorized = cur.fetchone()["exists"]

            if not is_authorized:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Manager lacks authority to grant this role "
                        "or the requested scope is broader than the "
                        "manager's own active grant."
                    ),
                )

            # 2. Idempotency check: avoid duplicate active grants
            exist_query = """
            SELECT id
            FROM grants
            WHERE user_id = %s
              AND role_code = %s
              AND client_id IS NOT DISTINCT FROM %s
              AND branch_id IS NOT DISTINCT FROM %s
              AND direction IS NOT DISTINCT FROM %s
              AND mode IS NOT DISTINCT FROM %s
              AND CURRENT_TIMESTAMP >= valid_from
              AND CURRENT_TIMESTAMP < valid_to
              AND revoked_by IS NULL;
            """

            cur.execute(
                exist_query,
                (
                    payload.target_user_id,
                    payload.role_code,
                    payload.client_id,
                    payload.branch_id,
                    payload.direction,
                    payload.mode,
                ),
            )

            existing_grant = cur.fetchone()

            if existing_grant:
                return {
                    "status": "skipped",
                    "message": "Exact active grant already exists",
                    "grant_id": existing_grant["id"],
                }

            # 3. Create the grant
            insert_query = """
            INSERT INTO grants (
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
                granted_by,
                reason
            )
            VALUES (
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s,
                %s, %s
            )
            RETURNING id;
            """

            cur.execute(
                insert_query,
                (
                    payload.target_user_id,
                    payload.role_code,
                    payload.client_id,
                    c_all,
                    payload.branch_id,
                    b_all,
                    payload.direction,
                    d_all,
                    payload.mode,
                    m_all,
                    payload.manager_id,
                    payload.reason,
                ),
            )

            grant = cur.fetchone()

            # 4. Write immutable audit history
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
            SELECT
                id,
                user_id,
                'grant',
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
                granted_by,
                reason
            FROM grants
            WHERE id = %s;
            """

            cur.execute(event_query, (grant["id"],))
            db.commit()

            return {
                "status": "success",
                "grant_id": grant["id"],
            }

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise
