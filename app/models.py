# app/models.py
from pydantic import BaseModel
from typing import Optional, Dict

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
    
class GrantRoleRequest(BaseModel):
    manager_id: int        # Fixed: Changed = to :
    target_user_id: int    # Fixed: Changed = to :
    role_code: str         # Fixed: Changed = to :
    
    # Scopes - All default to None (which will translate to _all = true in DB)
    client_id: Optional[int] = None
    branch_id: Optional[int] = None
    direction: Optional[str] = None
    mode: Optional[str] = None
    reason: str = "API Grant"
    
class RevokeGrantRequest(BaseModel):
    manager_id: int
    reason: str