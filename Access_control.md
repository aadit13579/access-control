# Access Control Service — Project Summary

> A full-stack role-based access control system for shipment job management.
> Backend: **FastAPI + PostgreSQL**. Frontend: **React + Vite + IBM Carbon Design System**.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Database Schema](#3-database-schema)
4. [Authorization Engine](#4-authorization-engine)
5. [Backend — API Routers](#5-backend--api-routers)
6. [Backend — Services Layer](#6-backend--services-layer)
7. [Frontend — Structure](#7-frontend--structure)
8. [Frontend — Pages](#8-frontend--pages)
9. [Frontend — Components](#9-frontend--components)
10. [Frontend — Hooks](#10-frontend--hooks)
11. [Key Design Decisions](#11-key-design-decisions)
12. [API Summary Table](#12-api-summary-table)

---

## 1. Project Overview

The Access Control Service answers one question consistently:

> **May this user perform this action on this job, at this time?**

It manages shipment jobs through a lifecycle (`confirmed → prepared → checked → filed → cancelled / closed → reopened`) and enforces:

- **Role-based permissions** scoped by client, branch, direction, and mode
- **Segregation of duties** (e.g. a Maker cannot also Check their own job)
- **Absence management** (absent users are automatically denied)
- **Two-person control** for sensitive actions (cancel, reopen)
- **Historical audit reconstruction** — who *could have* acted at any past point in time
- **Explainable decisions** — every denial has a machine-readable reason code

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Frontend  (React + Vite + Carbon Design System)        │
│  Port 5173                                              │
│                                                         │
│  Pages        Hooks (data fetch)    Components (UI)     │
│  ──────        ─────────────────    ────────────────    │
│  JobsPage      useWaitingJobs       JobsTable           │
│  WaitingPage   useActions           JobHistory          │
│  JobDetails    useJobHistory        JobActionPanel      │
│  AuthorizationPage useApprovals     AuthorizationResult │
│  ApprovalsPage                      ApprovalDecisionCell│
│  GrantsPage                         StatusNotifications │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP / REST (CORS open)
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Backend  (FastAPI + psycopg3)                          │
│  Port 8000                                              │
│                                                         │
│  Routers → Services → PostgreSQL                        │
│                                                         │
│  auth_service.authorize_user()  ◄── central engine     │
│  job_service.execute_transition()                       │
└────────────────────────┬────────────────────────────────┘
                         │ psycopg3 connection pool
                         ▼
┌─────────────────────────────────────────────────────────┐
│  PostgreSQL                                             │
│                                                         │
│  Policy tables: roles, actions, role_permissions,       │
│                 role_grant_authority, sod_rules,        │
│                 action_approval_rules                   │
│                                                         │
│  Operational: users, grants, jobs, absences, approvals  │
│                                                         │
│  Audit (append-only): job_events, grant_events,         │
│                       role_permission_log               │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Database Schema

All policy is stored as data — no hardcoded role logic in Python.

### Enums

| Enum | Values |
|---|---|
| `direction` | `import`, `export` |
| `mode` | `air`, `fcl`, `lcl` |
| `stage` | `confirmed`, `prepared`, `checked`, `filed`, `cancelled`, `reopened`, `closed` |

### Core Tables

#### `users`
Stores identity only — never permissions.

| Column | Type | Notes |
|---|---|---|
| `id` | serial PK | |
| `name` | text | |
| `kind` | text | `staff`, `client`, `system` |
| `client_id` | int FK→clients | Required for kind=`client` |
| `is_active` | boolean | Inactive users are always denied |

#### `roles`
Named responsibility types (e.g. maker, checker, filer, viewer, manager, admin, parser).

| Column | Notes |
|---|---|
| `code` PK | |
| `external_ok` | Whether client-side users may hold this role |

#### `role_permissions`
Maps roles to permitted action codes. Many-to-many.

#### `role_grant_authority`
Controls which manager role may grant which target role. Prevents privilege escalation.

#### `actions`
Defines every valid action code, valid source stages, and result stage.

| Column | Notes |
|---|---|
| `code` PK | `view`, `prepare`, `check`, `file`, `cancel`, `reopen`, `approve`, `reject`, `parse`, `manage_grants`, `reassign` |
| `from_stages` | Array of valid source stages; `NULL` = any stage (e.g. `view`) |
| `to_stage` | Resulting stage after action; `NULL` = no transition (read-only actions) |

#### `action_approval_rules`
Actions listed here require the two-person approval workflow before execution.

| Column | Notes |
|---|---|
| `action` FK→actions | e.g. `cancel`, `reopen` |
| `approvals_required` | Currently `1` |

#### `sod_rules`
Segregation-of-duties rules stored as data.

| Column | Notes |
|---|---|
| `action` | The action being attempted |
| `blocked_if_actor_did` | A prior action by the same user that blocks it |

Example: `action=check, blocked_if_actor_did=prepare` → a user who prepared this job cannot check it.

#### `grants`
Scoped, time-bounded role assignments.

| Column | Notes |
|---|---|
| `user_id` | Who holds the grant |
| `role_code` | What role they hold |
| `client_id` / `client_all` | Exactly one must be set (specific client OR all) |
| `branch_id` / `branch_all` | Same pattern |
| `direction` / `direction_all` | Same pattern |
| `mode` / `mode_all` | Same pattern |
| `valid_from` / `valid_to` | Time window; active grants use `valid_to = 'infinity'` |
| `granted_by` | Manager who issued the grant |
| `revoked_by` | Set when revoked; `NULL` for active grants |

Index on `(user_id, valid_from, valid_to)` for fast grant lookups.

#### `jobs`
Current business state of each shipment.

| Column | Notes |
|---|---|
| `ref` | Human-readable unique reference |
| `stage` | Current workflow stage (enum) |
| `version` | Optimistic concurrency counter, incremented on each transition |

Index on `(stage, client_id, branch_id)`.

#### `absences`
Active absence windows per user. Authorization denies any request falling inside `[starts_at, ends_at)`.

#### `approvals`
Pending two-person approval requests.

| Column | Notes |
|---|---|
| `status` | `pending`, `approved`, `rejected` |
| `requested_by` | The user who raised the request |
| `decided_by` | Set to deciding user on approval/rejection |

DB constraint: `decided_by <> requested_by` (two-person rule enforced at schema level).

### Audit Tables (append-only)

| Table | Records |
|---|---|
| `job_events` | Every action attempt (allowed and denied) with actor, stage, grant, reason |
| `grant_events` | Every grant creation and revocation event |
| `role_permission_log` | Every addition/removal of an action from a role |

Append-only triggers (`prevent_modification`) block `UPDATE` and `DELETE` on `job_events` and `role_permission_log`.

---

## 4. Authorization Engine

**File:** [`backend/app/services/auth_service.py`](backend/app/services/auth_service.py)

The central `authorize_user(db, user_id, action, job_id, as_of=None)` function is used by every endpoint that needs to check or perform an action. It evaluates the following checks in order — **fail-closed** at every step:

| Step | Check | Denial Code |
|---|---|---|
| 1 | User exists and is active | `USER_NOT_FOUND`, `USER_INACTIVE` |
| 2 | Job exists | `JOB_NOT_FOUND` |
| 3 | Action is defined | `UNKNOWN_ACTION` |
| 4 | Job is in a permitted stage for this action | `INVALID_STAGE` |
| 5 | User is not absent at `as_of` | `USER_ABSENT` |
| 6 | At least one active, scope-matching grant provides this action | `NO_MATCHING_GRANT` |
| 7 | No SoD rule is violated by prior actions on this job | `SOD_VIOLATION` |
| ✓ | **Allowed** — returns authorizing grant, role, and scope | `AUTHORIZED` |

The `as_of` parameter defaults to `now()` for current authorization but accepts a historical timestamp for point-in-time audit queries.

---

## 5. Backend — API Routers

| File | Route(s) | Tag |
|---|---|---|
| `routers/get_all_users.py` | `GET /api/users` | Users |
| `routers/get_user.py` | `GET /api/users/{user_id}` | Users |
| `routers/get_roles.py` | `GET /api/users/{user_id}/permissions` | Roles |
| `routers/auth.py` | `POST /api/auth/authorize` | Authorization |
| `routers/get_actions.py` | `GET /api/actions` | Actions |
| `routers/jobs_waiting.py` | `GET /api/jobs/waiting` | Jobs |
| `routers/jobs_action.py` | `POST /api/jobs/{job_id}/action` | Jobs |
| `routers/jobs_approvals.py` | `POST /api/jobs/{job_id}/approvals/request` | Jobs |
| `routers/jobs_approvals.py` | `POST /api/jobs/approvals/{approval_id}/decide` | Jobs |
| `routers/jobs_history.py` | `GET /api/jobs/{job_id}/history` | Jobs |
| `routers/jobs_history.py` | `GET /api/jobs/{job_id}/who-could-act` | Jobs |
| `routers/get_approvals.py` | `GET /api/approvals` | Actions |
| `routers/grants_create.py` | `POST /api/grants/` | Grants |
| `routers/grants_revoke.py` | `POST /api/grants/{grant_id}/revoke` | Grants |

### Grant creation validation (`grants_create.py`)
1. Manager cannot grant to themselves
2. Manager must hold an active grant with `manage_grants` permission
3. Manager's role must be authorized to grant the requested role (`role_grant_authority`)
4. Manager's grant scope must cover the scope being delegated (no scope escalation)
5. Idempotency check — duplicate active grant is skipped, not errored
6. Immutable audit event written to `grant_events` in the same transaction

### Approval workflow (`jobs_approvals.py`)
**Request:**
1. Action must be listed in `action_approval_rules`
2. Requester must be independently authorized for the action
3. Duplicate pending request is skipped

**Decide:**
1. Approver must differ from requester (two-person rule)
2. Approver must independently hold the `approve`/`reject` permission
3. If approved: requester is re-authorized at execution time
4. Transition, approval update, and audit event are atomic in one transaction

---

## 6. Backend — Services Layer

### `auth_service.authorize_user()`
The canonical authorization function. Used by: authorization API, jobs/waiting, jobs/action, approval request, approval decide (twice — for approver and requester).

### `job_service.execute_transition()`
Locks the job row with `SELECT FOR UPDATE`, re-runs `authorize_user()` after the lock, advances `stage`, increments `version`, and appends an immutable `job_events` row.

### `job_service.get_approval_requirement()`
Checks `action_approval_rules` for a given action. Returns the rule if approval is required, or `None`.

### `job_service.record_job_event()`
Inserts an immutable `job_events` row. Used for both allowed and denied attempts.

---

## 7. Frontend — Structure

```
frontend/src/
├── types/
│   └── index.ts              # Shared domain types (Job, Action, HistoryItem, Approval, etc.)
├── context/
│   └── UserContext.tsx        # Global user selection and permissions
├── hooks/
│   ├── useActions.ts          # Fetch /api/actions with optional preselect
│   ├── useWaitingJobs.ts      # Fetch /api/jobs/waiting for a user/action
│   ├── useJobHistory.ts       # Fetch job history, exposes reload()
│   └── useApprovals.ts        # Fetch pending approvals
├── components/
│   ├── AppHeader.tsx          # Navigation bar + user switcher
│   ├── JobsTable.tsx          # Reusable Carbon DataTable for job lists
│   ├── JobHistory.tsx         # History tiles on Job Details page
│   ├── JobActionPanel.tsx     # Action picker, auth check, perform/raise panel
│   ├── AuthorizationResult.tsx# Authorization check result tile
│   ├── ApprovalDecisionCell.tsx # Reason + Approve/Reject buttons per approval
│   └── StatusNotifications.tsx # Error/success inline notifications
└── pages/
    ├── JobsPage.tsx            # All viewable jobs
    ├── WaitingPage.tsx         # Jobs awaiting a specific action
    ├── JobDetailsPage.tsx      # Job history + action panel
    ├── AuthorizationPage.tsx   # Manual authorization check tool
    ├── ApprovalsPage.tsx       # Pending approvals management
    └── GrantsPage.tsx          # Grant creation form
```

### `UserContext.tsx`
Loads all users from `/api/users` on startup and sets the first user as the default. When the selected user changes, re-fetches permissions from `/api/users/{user_id}/permissions`. The `permissions` array drives conditional navigation in the header (Grants and Approvals links only shown if the user holds the relevant permissions).

---

## 8. Frontend — Pages

| Page | Route | Purpose |
|---|---|---|
| `JobsPage` | `/jobs` | Lists all jobs the current user can `view`. Clicking a row navigates to Job Details. |
| `WaitingPage` | `/waiting` | Selects an action from a dropdown, then lists jobs the user is authorized to perform that action on. Clicking a row navigates to Job Details pre-selecting that action. |
| `JobDetailsPage` | `/jobs/:jobId` | Two-column layout: left shows the full job history (audit trail), right shows the action panel. Supports Back navigation to either `/jobs` or `/waiting` depending on entry point. |
| `AuthorizationPage` | `/authorization` | Debug/admin tool: select a job and an action, run an authorization check, and view the full engine response including reason code, grant, scope, and SoD details. |
| `ApprovalsPage` | `/approvals` | Shows all pending approvals. Users with `approve`/`reject` permissions can enter a reason and approve or reject each request. Redirects to `/jobs` if user has neither permission. |
| `GrantsPage` | `/grants` | Form to create a new scoped role grant. Redirects to `/jobs` if user lacks `manage_grants`. Supports all scope dimensions (client, branch, direction, mode) with null = ALL semantics. |

---

## 9. Frontend — Components

### `AppHeader`
Carbon `Header` with navigation links. User switcher Dropdown on the right changes the active user globally via `UserContext`. Grants and Approvals links are conditionally rendered based on the current user's permissions.

### `JobsTable`
Generic Carbon `DataTable` wrapper. Accepts headers, rows, an optional `onRowClick` handler (makes rows clickable with pointer cursor), and an optional `stageColumnKey` to render that column's value as a blue `Tag`.

### `JobHistory`
Renders the ordered list of `HistoryItem` tiles. Each tile shows: actor name, action (colored Tag by outcome: green=allowed, red=denied), stage transition, reason, grant ID, and timestamp.

### `JobActionPanel`
Self-contained panel with its own local state for authorization status. Flow:
1. User selects an action from the Dropdown
2. Clicks **Check action** → calls `POST /api/auth/authorize`
3. If allowed: shows reason and reveals the Reason textarea + submit button
4. Submit calls either `POST /api/jobs/{id}/action` or `POST /api/jobs/{id}/approvals/request` based on `approvals_required`
5. On success: calls `onActionSuccess()` to reload history; resets authorization state

### `AuthorizationResult`
Tile displaying the full response from `POST /api/auth/authorize`: allowed/denied tag, user, job, action, reason code, reason, current stage, role, grant ID, and grant scope breakdown.

### `ApprovalDecisionCell`
The decision column for a single approval row: a `TextArea` for the reason, and conditional Approve / Reject `Button` components based on the user's `canApprove` / `canReject` permissions.

### `StatusNotifications`
Renders an error `InlineNotification` and/or a success `InlineNotification` based on nullable props. Used across all pages.

---

## 10. Frontend — Hooks

| Hook | API Called | Returns |
|---|---|---|
| `useActions(apiBaseUrl, options?)` | `GET /api/actions` | `{ actions, selectedAction, setSelectedAction, loading, error }` |
| `useWaitingJobs(apiBaseUrl, userId, action)` | `GET /api/jobs/waiting` | `{ data, jobs, loading, error }` |
| `useJobHistory(apiBaseUrl, jobId)` | `GET /api/jobs/{jobId}/history` | `{ history, loading, error, setError, reload }` |
| `useApprovals(apiBaseUrl)` | `GET /api/approvals` | `{ approvals, setApprovals, loading, error, setError }` |

`useActions` supports two preselect options:
- `preselectCode` — select a specific action by code (used when entering Job Details from Waiting)
- `onlyWithFromStages` — select the first action that has `from_stages != null` (used on the Waiting page)

`useJobHistory` exposes a `reload()` function so the page can refresh history after a successful action.

---

## 11. Key Design Decisions

### Single authorization engine
`authorize_user()` is called by every endpoint that needs a permission check — not duplicated. The waiting-list endpoint and the action endpoint use identical logic, so the jobs shown on Waiting are always consistent with what the action endpoint will allow.

### Double-authorization on transition
`execute_transition()` re-runs `authorize_user()` after acquiring `SELECT FOR UPDATE` on the job row. This handles the race where a grant expires or the job stage changes between the initial check and execution.

### Fail-closed
Every unknown or missing condition results in denial. There is no default-allow path.

### Policy as data
Roles, permissions, grant authority, workflow transitions, SoD rules, and approval requirements are all rows in tables. Changing operational policy does not require a code change or deploy.

### Scope semantics: value XOR all
Each scope dimension in `grants` has a `{dim}_id` / `{dim}_all` pair with a DB `CHECK` constraint ensuring exactly one is set. This prevents ambiguous or overly broad accidental grants.

### Append-only audit
`job_events` and `role_permission_log` have `BEFORE UPDATE OR DELETE` triggers that raise an exception. Evidence cannot be silently removed.

### Historical reconstruction
`who-could-act` uses `role_permission_log` to find the latest permission change on or before the requested timestamp — not the current permission state. This answers questions like "who *could have* filed this job on October 3rd?" accurately even after subsequent permission changes.

### Frontend: hooks extract data fetching
Data fetching is extracted into custom hooks so pages contain only layout and user interaction logic. This follows the Single Responsibility Principle and allows hooks to be reused across pages (e.g. `useWaitingJobs` is used by both `JobsPage` and `AuthorizationPage`).

---

## 12. API Summary Table

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/users` | List all active users |
| `GET` | `/api/users/{user_id}` | Get a single user |
| `GET` | `/api/users/{user_id}/permissions` | Get user's current role permissions |
| `POST` | `/api/auth/authorize` | Check if user may perform action on job |
| `GET` | `/api/actions` | List all actions with stage rules and approval requirements |
| `GET` | `/api/jobs/waiting` | List jobs a user is authorized to act on |
| `POST` | `/api/jobs/{job_id}/action` | Perform a direct (non-approval) action |
| `POST` | `/api/jobs/{job_id}/approvals/request` | Raise a two-person approval request |
| `POST` | `/api/jobs/approvals/{approval_id}/decide` | Approve or reject a pending request |
| `GET` | `/api/jobs/{job_id}/history` | Get full audit trail for a job |
| `GET` | `/api/jobs/{job_id}/who-could-act` | Historical: who was authorized at a past timestamp |
| `GET` | `/api/approvals` | List all pending approvals |
| `POST` | `/api/grants/` | Create a new scoped role grant |
| `POST` | `/api/grants/{grant_id}/revoke` | Revoke an active grant |

See [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) for full request/response details.

