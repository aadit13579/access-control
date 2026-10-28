from fastapi import APIRouter, Depends
from psycopg import Connection

from app.database import get_db

router = APIRouter(prefix="/api", tags=["Roles"])


@router.get("/users/{user_id}/permissions")
def get_user_permissions(
    user_id: int,
    db: Connection = Depends(get_db),
):
    with db.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT
                g.user_id,
                rp.role_code,
                rp.action
            FROM role_permissions rp
            JOIN grants g
                ON g.role_code = rp.role_code
            WHERE g.user_id = %s
            AND g.valid_from <= NOW()
            AND g.valid_to > NOW()
            ORDER BY rp.role_code, rp.action;
            """,
            (user_id,),
        )

        rows = cur.fetchall()

    roles: dict[str, list[str]] = {}
    all_permissions: set[str] = set()

    for row in rows:
        role_code = row["role_code"]
        action = row["action"]

        if role_code not in roles:
            roles[role_code] = []

        roles[role_code].append(action)
        all_permissions.add(action)

    return {
        "user_id": user_id,
        "roles": [
            {
                "role_code": role_code,
                "permissions": permissions,
            }
            for role_code, permissions in roles.items()
        ],
        "permissions": sorted(all_permissions),
    }