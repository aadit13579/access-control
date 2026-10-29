from typing import Literal
from pydantic import BaseModel


# ── Authorization ────────────────────────────────────────────────────

class AccessCheckRequest(BaseModel):
    user_id: int
    action: str
    job_id: int


# ── Jobs ─────────────────────────────────────────────────────────────

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


# ── Grants ───────────────────────────────────────────────────────────

class GrantRoleRequest(BaseModel):
    manager_id: int
    target_user_id: int
    role_code: str

    # Scopes - None translates to _all = true in DB
    client_id: int | None = None
    branch_id: int | None = None
    direction: str | None = None
    mode: str | None = None
    reason: str = "API Grant"


class RevokeGrantRequest(BaseModel):
    manager_id: int
    reason: str
