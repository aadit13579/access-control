# API Documentation

Base URL: `http://localhost:8000`

---

## Table of Contents

1. [Users](#1-users)
   - [GET /api/users](#get-apiusers)
   - [GET /api/users/{user_id}](#get-apiusersuser_id)
   - [GET /api/users/{user_id}/permissions](#get-apiusersuser_idpermissions)
2. [Authorization](#2-authorization)
   - [POST /api/auth/authorize](#post-apiauthauthorize)
3. [Actions](#3-actions)
   - [GET /api/actions](#get-apiactions)
4. [Jobs](#4-jobs)
   - [GET /api/jobs/waiting](#get-apijobswaiting)
   - [POST /api/jobs/{job_id}/action](#post-apijobsjob_idaction)
   - [POST /api/jobs/{job_id}/approvals/request](#post-apijobsjob_idapprovalsrequest)
   - [POST /api/jobs/approvals/{approval_id}/decide](#post-apijobsapprovalsapproval_iddecide)
   - [GET /api/jobs/{job_id}/history](#get-apijobsjob_idhistory)
   - [GET /api/jobs/{job_id}/who-could-act](#get-apijobsjob_idwho-could-act)
5. [Approvals](#5-approvals)
   - [GET /api/approvals](#get-apiapprovals)
6. [Grants](#6-grants)
   - [POST /api/grants/](#post-apigrants)
   - [POST /api/grants/{grant_id}/revoke](#post-apigrantsgrant_idrevoke)

---

## 1. Users

### `GET /api/users`
Fetches all active users (used for user switcher / directory).

#### cURL
```bash
curl -X GET "http://localhost:8000/api/users"
```

#### Response Format (200 OK)
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "name": "Aditi",
      "kind": "staff",
      "client_id": null
    },
    {
      "id": 2,
      "name": "Rahul",
      "kind": "client",
      "client_id": 3
    }
  ]
}
```

---

### `GET /api/users/{user_id}`
Fetches a single active user by ID.

#### cURL
```bash
curl -X GET "http://localhost:8000/api/users/1"
```

#### Response Format (200 OK)
```json
{
  "status": "success",
  "data": {
    "id": 1,
    "name": "Aditi",
    "kind": "staff",
    "client_id": null
  }
}
```

---

### `GET /api/users/{user_id}/permissions`
Returns the flat list of all actions the user currently holds through any active grant, plus a breakdown by role. Used by the frontend to conditionally show/hide navigation items such as Approvals and Grants.

#### cURL
```bash
curl -X GET "http://localhost:8000/api/users/1/permissions"
```

#### Response Format (200 OK)
```json
{
  "user_id": 1,
  "roles": [
    {
      "role_code": "maker",
      "permissions": ["prepare", "view"]
    },
    {
      "role_code": "checker",
      "permissions": ["check", "view"]
    }
  ],
  "permissions": ["check", "prepare", "view"]
}
```

> **Note:** `permissions` is the deduplicated union of all role permissions. The frontend checks this list directly (e.g. `permissions.includes('approve')`) to determine which UI features are available.

---

## 2. Authorization

### `POST /api/auth/authorize`
Checks if a user is permitted to perform a given action on a specific job (fail-closed canonical evaluation).

#### cURL
```bash
curl -X POST "http://localhost:8000/api/auth/authorize" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "action": "prepare",
    "job_id": 101
  }'
```

#### Request Body
| Field | Type | Required | Description |
|---|---|---|---|
| `user_id` | int | ✓ | ID of the user performing the action |
| `action` | string | ✓ | Action code (e.g. `prepare`, `check`) |
| `job_id` | int | ✓ | ID of the job being acted on |

#### Response Format (200 OK - Allowed)
```json
{
  "allowed": true,
  "reason_code": "AUTHORIZED",
  "reason": "Authorized by Grant #2 (ops_specialist).",
  "grant_id": 2,
  "role_code": "ops_specialist",
  "grant_scope": {
    "client": "ALL",
    "branch": "Branch ID: 1",
    "direction": "export",
    "mode": "air"
  },
  "job_stage": "confirmed",
  "as_of": "2026-10-27T16:42:00Z"
}
```

#### Response Format (200 OK - Denied)
```json
{
  "allowed": false,
  "reason_code": "NO_MATCHING_GRANT",
  "reason": "Denied: no grant active at the requested time provides this action for this job's scope.",
  "job_scope": {
    "client_id": 1,
    "branch_id": 2,
    "direction": "export",
    "mode": "air"
  }
}
```

#### Denial Reason Codes

| Reason Code | Meaning |
|---|---|
| `USER_NOT_FOUND` | User ID does not exist |
| `USER_INACTIVE` | User account has been deactivated |
| `JOB_NOT_FOUND` | Job ID does not exist |
| `UNKNOWN_ACTION` | Action code is not defined in the `actions` table |
| `INVALID_STAGE` | Job is not in a stage where this action is permitted |
| `USER_ABSENT` | User has an active absence at the current time |
| `NO_MATCHING_GRANT` | No active grant covers this user/action/job scope combination |
| `SOD_VIOLATION` | Segregation-of-duties: user previously performed a conflicting action on this job |

---

## 3. Actions

### `GET /api/actions`
Returns all defined actions with their stage constraints and approval requirements. Used by the frontend to populate the action dropdown.

#### cURL
```bash
curl -X GET "http://localhost:8000/api/actions"
```

#### Response Format (200 OK)
```json
{
  "actions": [
    {
      "code": "cancel",
      "from_stages": ["filed"],
      "to_stage": "cancelled",
      "approvals_required": 1
    },
    {
      "code": "check",
      "from_stages": ["prepared"],
      "to_stage": "checked",
      "approvals_required": 0
    },
    {
      "code": "file",
      "from_stages": ["checked"],
      "to_stage": "filed",
      "approvals_required": 0
    },
    {
      "code": "prepare",
      "from_stages": ["confirmed"],
      "to_stage": "prepared",
      "approvals_required": 0
    },
    {
      "code": "reopen",
      "from_stages": ["closed"],
      "to_stage": "reopened",
      "approvals_required": 1
    },
    {
      "code": "view",
      "from_stages": null,
      "to_stage": null,
      "approvals_required": 0
    }
  ]
}
```

> **Note:** `from_stages: null` means the action may be performed in any job stage (e.g. `view`). `approvals_required > 0` means the action must go through the approval workflow before execution.

---

## 4. Jobs

### `GET /api/jobs/waiting`
Lists all jobs where the specified user currently has authorization to perform the requested action. Uses the same canonical `authorize_user()` engine as action execution — not a shortcut.

#### cURL
```bash
curl -X GET "http://localhost:8000/api/jobs/waiting?user_id=1&action=prepare"
```

#### Query Parameters
| Parameter | Type | Required | Description |
|---|---|---|---|
| `user_id` | int | ✓ | ID of the user |
| `action` | string | ✓ | Action code to check authorization against |

#### Response Format (200 OK)
```json
{
  "user_id": 1,
  "action": "prepare",
  "count": 1,
  "jobs": [
    {
      "id": 101,
      "ref": "JOB-2026-001",
      "client_id": 1,
      "branch_id": 1,
      "direction": "export",
      "mode": "air",
      "stage": "confirmed",
      "grant_id": 2,
      "role_code": "ops_specialist"
    }
  ]
}
```

---

### `POST /api/jobs/{job_id}/action`
Performs a state-changing action directly (if independent approval is not required).

#### cURL
```bash
curl -X POST "http://localhost:8000/api/jobs/101/action" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "action": "prepare",
    "reason": "Completed initial customs documentation"
  }'
```

#### Request Body
| Field | Type | Required | Description |
|---|---|---|---|
| `user_id` | int | ✓ | ID of the acting user |
| `action` | string | ✓ | Action code to perform |
| `reason` | string | — | Reason recorded in the audit trail |

#### Response Format (200 OK)
```json
{
  "status": "success",
  "transition": {
    "job_id": 101,
    "action": "prepare",
    "from_stage": "confirmed",
    "to_stage": "prepared",
    "grant_id": 2
  }
}
```

#### Response Format (409 Conflict - Requires Approval)
```json
{
  "detail": {
    "message": "Action 'cancel' requires independent approval.",
    "approval_request_endpoint": "/api/jobs/101/approvals/request"
  }
}
```

> **Note:** Authorization is checked twice — once before locking the row, and again after `SELECT FOR UPDATE` — to handle concurrent state changes safely. All denied attempts are still written to `job_events` as `outcome = 'denied'`.

---

### `POST /api/jobs/{job_id}/approvals/request`
Creates a pending approval request for actions requiring two-person review (e.g. cancellation, reopen).

#### cURL
```bash
curl -X POST "http://localhost:8000/api/jobs/101/approvals/request" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 1,
    "action": "cancel",
    "reason": "Customer requested shipment termination"
  }'
```

#### Request Body
| Field | Type | Required | Description |
|---|---|---|---|
| `user_id` | int | ✓ | ID of the requesting user |
| `action` | string | ✓ | Action being requested (must exist in `action_approval_rules`) |
| `reason` | string | ✓ | Reason for the request |

#### Response Format (200 OK)
```json
{
  "status": "success",
  "approval": {
    "id": 5,
    "job_id": 101,
    "action": "cancel",
    "requested_by": 1,
    "status": "pending"
  },
  "message": "Approval request created."
}
```

#### Response Format (200 OK - Duplicate skipped)
```json
{
  "status": "skipped",
  "message": "A pending approval request already exists.",
  "approval_id": 5
}
```

---

### `POST /api/jobs/approvals/{approval_id}/decide`
Second authorized user approves or rejects an approval request. If approved, the transition executes atomically.

#### cURL
```bash
curl -X POST "http://localhost:8000/api/jobs/approvals/5/decide" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 2,
    "decision": "approved"
  }'
```

#### Request Body
| Field | Type | Required | Description |
|---|---|---|---|
| `user_id` | int | ✓ | ID of the deciding user (must differ from requester) |
| `decision` | `"approved"` \| `"rejected"` | ✓ | The decision |

#### Response Format (200 OK - Approved)
```json
{
  "status": "approved",
  "approval_id": 5,
  "requested_by": 1,
  "decided_by": 2,
  "message": "Approval granted and job action executed.",
  "transition": {
    "job_id": 101,
    "action": "cancel",
    "from_stage": "prepared",
    "to_stage": "cancelled",
    "grant_id": 1
  }
}
```

#### Response Format (200 OK - Rejected)
```json
{
  "status": "rejected",
  "approval_id": 5,
  "job_id": 101,
  "action": "cancel",
  "decided_by": 2,
  "message": "Approval request rejected. Job was not changed."
}
```

> **Note:** The approver must independently hold the `approve` (or `reject`) permission. The requester is re-authorized at execution time. Requester cannot decide their own request (enforced by DB constraint and API check). All of this is atomic in one transaction.

---

### `GET /api/jobs/{job_id}/history`
Fetches the immutable audit trail of all actions and state transitions for a job.

#### cURL
```bash
curl -X GET "http://localhost:8000/api/jobs/101/history"
```

#### Response Format (200 OK)
```json
{
  "job_id": 101,
  "history": [
    {
      "id": 12,
      "actor_id": 1,
      "actor_name": "Aditi",
      "action": "prepare",
      "from_stage": "confirmed",
      "to_stage": "prepared",
      "outcome": "allowed",
      "grant_id": 2,
      "reason": "Completed initial customs documentation",
      "at": "2026-10-27T10:30:00Z"
    }
  ]
}
```

> **Note:** `job_events` is append-only — a database trigger prevents `UPDATE` or `DELETE`. Both allowed and denied attempts are recorded, providing a complete audit trail.

---

### `GET /api/jobs/{job_id}/who-could-act`
Historical point-in-time audit query to check which users held active grants for a specific action on this job at timestamp `at`.

#### cURL
```bash
curl -X GET "http://localhost:8000/api/jobs/101/who-could-act?action=prepare&at=2026-10-27T10:00:00Z"
```

#### Query Parameters
| Parameter | Type | Required | Description |
|---|---|---|---|
| `action` | string | ✓ | Action code to check |
| `at` | ISO 8601 datetime | ✓ | Point in time for the historical query |

#### Response Format (200 OK)
```json
{
  "job_id": 101,
  "job_ref": "JOB-2026-001",
  "action": "prepare",
  "at": "2026-10-27T10:00:00Z",
  "count": 1,
  "users": [
    {
      "user_id": 1,
      "user_name": "Aditi",
      "grant_id": 2,
      "role_code": "ops_specialist"
    }
  ]
}
```

> **Note:** Uses `role_permission_log` to reconstruct the historical state of role permissions at the given timestamp, not just the current state. This enables answering "who *could have* acted on the 3rd?" accurately even after permission changes.

---

## 5. Approvals

### `GET /api/approvals`
Returns all pending approval requests (where `decided_by IS NULL` / `status = 'pending'`). Used by the Approvals page to show outstanding items to users with `approve` or `reject` permissions.

#### cURL
```bash
curl -X GET "http://localhost:8000/api/approvals"
```

#### Response Format (200 OK)
```json
{
  "approvals": [
    {
      "id": 5,
      "job_id": 101,
      "action": "cancel",
      "requested_by": 1,
      "reason": "Customer requested shipment termination",
      "decided_by": null
    }
  ]
}
```

> **Note:** The frontend further filters `decided_by === null` on the client side as a guard, but the server already only returns `status = 'pending'` rows.

---

## 6. Grants

### `POST /api/grants/`
Creates a scoped role grant for a user (validates manager's authority and delegation scope).

#### cURL
```bash
curl -X POST "http://localhost:8000/api/grants/" \
  -H "Content-Type: application/json" \
  -d '{
    "manager_id": 1,
    "target_user_id": 2,
    "role_code": "ops_specialist",
    "client_id": null,
    "branch_id": 1,
    "direction": "export",
    "mode": null,
    "reason": "Assigned to Air Export desk"
  }'
```

#### Request Body
| Field | Type | Required | Description |
|---|---|---|---|
| `manager_id` | int | ✓ | ID of the user creating the grant (must have `manage_grants`) |
| `target_user_id` | int | ✓ | ID of the user receiving the grant |
| `role_code` | string | ✓ | Role to grant (must exist in `roles`) |
| `client_id` | int \| null | — | Specific client; `null` = all clients |
| `branch_id` | int \| null | — | Specific branch; `null` = all branches |
| `direction` | `"import"` \| `"export"` \| null | — | Specific direction; `null` = all directions |
| `mode` | `"air"` \| `"fcl"` \| `"lcl"` \| null | — | Specific mode; `null` = all modes |
| `reason` | string | — | Reason recorded in grant audit log |

#### Validation Rules
- Manager cannot grant to themselves (`manager_id == target_user_id` → 403)
- Manager's own active grant must cover the scope being delegated
- Manager's role must be authorized to grant the requested role (via `role_grant_authority`)
- Duplicate identical active grant is skipped (idempotent)

#### Response Format (200 OK)
```json
{
  "status": "success",
  "grant_id": 8
}
```

#### Response Format (200 OK - Duplicate skipped)
```json
{
  "status": "skipped",
  "message": "Exact active grant already exists",
  "grant_id": 8
}
```

---

### `POST /api/grants/{grant_id}/revoke`
Revokes an active role grant immediately and appends to the immutable grant audit log.

#### cURL
```bash
curl -X POST "http://localhost:8000/api/grants/8/revoke" \
  -H "Content-Type: application/json" \
  -d '{
    "manager_id": 1,
    "reason": "Role reassignment to branch 2"
  }'
```

#### Request Body
| Field | Type | Required | Description |
|---|---|---|---|
| `manager_id` | int | ✓ | ID of the user revoking the grant |
| `reason` | string | ✓ | Reason recorded in revocation audit log |

#### Response Format (200 OK)
```json
{
  "status": "success",
  "grant_id": 8,
  "revoked_by": 1,
  "valid_to": "2026-10-27T22:15:00.123456Z",
  "message": "Grant revoked successfully."
}
```

#### Response Format (200 OK - Already expired)
```json
{
  "status": "skipped",
  "message": "Grant is already expired or revoked.",
  "grant_id": 8
}
```
