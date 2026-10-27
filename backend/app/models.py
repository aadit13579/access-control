# app/models.py
from pydantic import BaseModel
from typing import Optional, Dict, Literal


# ── Authorization ────────────────────────────────────────────────────

class AccessCheckRequest(BaseModel):
    user_id: int
    action: str
    job_id: int


class AccessCheckResponse(BaseModel):
    allowed: bool
    grant_id: Optional[int] = None
    role_code: Optional[str] = None
    grant_scope: Optional[Dict[str, str]] = None 
    reason: str


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
    
    # Scopes - All default to None (which will translate to _all = true in DB)
    client_id: Optional[int] = None
    branch_id: Optional[int] = None
    direction: Optional[str] = None
    mode: Optional[str] = None
    reason: str = "API Grant"
    

class RevokeGrantRequest(BaseModel):
    manager_id: int
    reason: str