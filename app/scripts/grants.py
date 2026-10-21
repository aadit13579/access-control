from fastapi import APIRouter, Depends, HTTPException
from psycopg import Connection

from app.models import GrantRoleRequest, RevokeGrantRequest
from app.database import get_db


router = APIRouter(prefix="/api/grants", tags=["Grants"])


@router.post("/")
def create_grant(
    payload: GrantRoleRequest,
    db: Connection = Depends(get_db)
):
    try:
        with db.cursor() as cur:

            # ---------------------------------------------------------
            # 1. Work out the scope being requested.
            #
            # If an ID/value is None, that dimension means ALL.
            # ---------------------------------------------------------
            c_all = payload.client_id is None
            b_all = payload.branch_id is None
            d_all = payload.direction is None
            m_all = payload.mode is None
            if payload.manager_id == payload.target_user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Users may not grant roles to themselves."
                )

            # ---------------------------------------------------------
            # 2. Check:
            #    a) manager has manage_grants permission
            #    b) manager's role may grant the requested role
            #    c) manager's own grant covers the scope being delegated
            #
            # Example:
            # Manager has Client 1 only:
            #   - may grant Client 1
            #   - may NOT grant Client 2
            #   - may NOT grant ALL clients
            #
            # Manager has ALL clients:
            #   - may grant Client 1
            #   - may grant Client 2
            #   - may grant ALL clients
            # ---------------------------------------------------------
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

                  AND (
                      g.client_all
                      OR (%s = FALSE AND g.client_id = %s)
                  )

                  AND (
                      g.branch_all
                      OR (%s = FALSE AND g.branch_id = %s)
                  )

                  AND (
                      g.direction_all
                      OR (%s = FALSE AND g.direction = %s)
                  )

                  AND (
                      g.mode_all
                      OR (%s = FALSE AND g.mode = %s)
                  )
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
                )
            )

            is_authorized = cur.fetchone()["exists"]

            if not is_authorized:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Manager lacks authority to grant this role "
                        "or the requested scope is broader than the "
                        "manager's own active grant."
                    )
                )

            # ---------------------------------------------------------
            # 3. Idempotency check:
            #    do not create the exact same active grant twice.
            # ---------------------------------------------------------
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
                )
            )

            existing_grant = cur.fetchone()

            if existing_grant:
                return {
                    "status": "skipped",
                    "message": "Exact active grant already exists",
                    "grant_id": existing_grant["id"],
                }

            # ---------------------------------------------------------
            # 4. Create the grant.
            #
            # Do NOT return valid_to here because active grants may use
            # PostgreSQL's special timestamp value 'infinity', which
            # Python datetime cannot represent.
            # ---------------------------------------------------------
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
                granted_by,
                reason;
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
                )
            )

            grant = cur.fetchone()

            # ---------------------------------------------------------
            # 5. Write immutable grant history.
            #
            # PostgreSQL copies valid_to directly from grants into
            # grant_events. This avoids sending 'infinity' through
            # Python/psycopg.
            # ---------------------------------------------------------
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

            # Grant creation + audit event succeed together.
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


@router.post("/{grant_id}/revoke")
def revoke_grant(
    grant_id: int,
    payload: RevokeGrantRequest,
    db: Connection = Depends(get_db)
):
    try:
        with db.cursor() as cur:

            # ---------------------------------------------------------
            # 1. Get and lock the grant being revoked.
            #
            # Do not SELECT valid_to directly because an active grant
            # may contain PostgreSQL 'infinity'.
            # ---------------------------------------------------------
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
                    detail="Grant not found."
                )

            if not grant["is_active"]:
                return {
                    "status": "skipped",
                    "message": "Grant is already expired or revoked.",
                    "grant_id": grant_id,
                }

            # ---------------------------------------------------------
            # 2. Check:
            #    a) manager may manage grants
            #    b) manager's role may manage this target role
            #    c) target grant lies within manager's own scope
            # ---------------------------------------------------------
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

                  AND (
                      g.client_all
                      OR (%s = FALSE AND g.client_id = %s)
                  )

                  AND (
                      g.branch_all
                      OR (%s = FALSE AND g.branch_id = %s)
                  )

                  AND (
                      g.direction_all
                      OR (%s = FALSE AND g.direction = %s)
                  )

                  AND (
                      g.mode_all
                      OR (%s = FALSE AND g.mode = %s)
                  )
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
                )
            )

            is_authorized = cur.fetchone()["exists"]

            if not is_authorized:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        "Manager lacks authority to revoke this role "
                        "or the grant is outside the manager's own scope."
                    )
                )

            # ---------------------------------------------------------
            # 3. Revoke the grant immediately.
            #
            # After this UPDATE, valid_to is a normal finite timestamp,
            # so it is safe for psycopg/Python to read it.
            # ---------------------------------------------------------
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

            cur.execute(
                revoke_query,
                (
                    payload.manager_id,
                    grant_id,
                )
            )

            revoked_grant = cur.fetchone()

            # ---------------------------------------------------------
            # 4. Record immutable revocation history.
            # ---------------------------------------------------------
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
                )
            )

            # Revocation + audit event succeed together.
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
