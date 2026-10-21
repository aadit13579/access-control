# Access Control Service — Design Document

## 1. Model

The service answers one question consistently:

> **May this user perform this action on this job, at this time?**

The model separates identity, capability, scope, workflow state, and history.

- `users` stores identity only: staff, client-side user, or system account.
- `roles` describes reusable responsibility types such as Maker, Checker, Filer, Viewer, Manager, Admin, and Parser.
- `role_permissions` maps roles to actions such as `view`, `prepare`, `check`, `file`, `cancel`, `reopen`, `approve`, and `reject`.
- `grants` assign a role to a user over a specific scope and time window.
- `jobs` store the current business state of each shipment.
- `actions` define which stages an action may start from and, where relevant, the resulting stage.
- `sod_rules` implement segregation-of-duties rules such as Maker/Checker separation.
- `absences` represent temporary unavailability.
- `approvals` and `action_approval_rules` implement two-person control for sensitive actions.
- `job_events`, `grant_events`, and `role_permission_log` preserve historical evidence.

A grant is scoped independently across client, branch, direction, mode, and validity period. This lets one person hold multiple responsibilities without creating a new role for every combination. For example, the same person can be Maker for all clients and Checker only for ACME/Mumbai/import jobs.

The authorization engine is fail-closed. An action is allowed only when the system can positively establish that the user is active, the action exists, the job is in a permitted stage, a matching grant exists, the scope matches, the user is not absent, and segregation-of-duties rules are satisfied.

## 2. Key Decisions and Trade-offs

### Data-driven policy

Roles, role permissions, grant authority, workflow transitions, approval requirements, and segregation-of-duties rules are stored as data rather than hardcoded per-role logic in Python.

**Benefit:** operational policy can change without rewriting the authorization engine.

**Trade-off:** authorization queries become more involved because several policy tables must be evaluated together.

### Scoped and time-bounded grants

A role is never assumed to apply everywhere. A grant can be broad (`client_all`, `branch_all`, etc.) or narrow.

**Benefit:** the model handles both organization-wide staff and highly restricted staff.

**Trade-off:** users with mixed responsibilities may need multiple grants.

### Authorization is checked at action time

Permission is not inherited merely because someone previously worked on a job. If a grant expires or is revoked, later actions fail.

**Benefit:** responsibility changes take effect immediately.

**Trade-off:** every mutation must call the authorization engine rather than relying on a session-level permission snapshot.

### Append-only audit history

Operational events, grant changes, and role-permission changes are retained as audit evidence. Append-only triggers prevent normal `UPDATE` and `DELETE` operations on audit tables.

**Benefit:** the system can explain both current and historical authorization.

### Two-person control for risky actions

`cancel` and `reopen` require an independent approval. The requester cannot approve their own request, and the original requester is re-authorized before the transition is executed.

**Benefit:** sensitive changes require deliberate second-person control.

## 3. Answers to the Design Questions

### 1. Should everyone see everything? How does seeing differ from acting?

No. `view` is an action like any other. A user's grant and role permissions determine whether they may see a job, and separate action permissions determine whether they may prepare, check, file, cancel, or otherwise modify it. Visibility therefore does not imply mutation rights.

### 2. Maker for every client, Checker for a few? Checker for one client/branch/imports only?

A user may hold multiple grants. One grant can make the user a Maker with `client_all = true`, while separate Checker grants restrict them to particular clients.

A narrow Checker grant can specify one `client_id`, one `branch_id`, `direction = 'import'`, and either one mode or `mode_all = true`.

### 3. What if the preparer is also qualified to approve/check?

Qualification alone is not enough. `sod_rules` can block `check` when the same actor previously performed `prepare` on that job. The engine examines successful `job_events`, so a qualified Checker can still be denied on a job they prepared.

### 4. What if the person responsible for a job is absent?

Absence is recorded in `absences`. Responsibility is not transferred automatically. The chosen policy is that an authorized manager reassigns the job to another eligible user. The replacement user must still independently satisfy normal authorization rules.

### 5. What happens to half-finished jobs when responsibilities change?

Authorization is checked again on every action. If the user's grant expires or is revoked, later actions fail. The job remains in its current stage until another authorized user continues it.

### 6. Who may cancel a filed job or reopen a closed one, and what should it take?

`cancel` and `reopen` are privileged actions. Role permissions determine who may request them, and `action_approval_rules` marks them as requiring independent approval.

The flow is:

1. an authorized requester creates the request;
2. an `approvals` row is created as `pending`;
3. another authorized user approves or rejects it;
4. requester and approver must be different people;
5. requester is authorized again immediately before execution;
6. if still valid, the job transitions and the event is appended to `job_events`.

The configured transitions are `filed -> cancelled` and `closed -> reopened`.

### 7. What if a client's own employee needs to follow shipments?

A client-side identity uses `users.kind = 'client'` and must belong to one `client_id`. Only roles with `external_ok = true` may be assigned to client users. A typical example is a Viewer grant restricted to the employee's own client.

### 8. What if an admin needs to fix a stuck job? What if an admin tries to increase their own power?

Administrative roles may receive operational recovery permissions such as reopen, approve, reject, or reassign.

Privilege escalation is constrained in two ways:

- the grant API rejects self-grants (`manager_id == target_user_id`);
- a manager cannot delegate a scope broader than the manager's own active grant.

Thus an administrator can solve operational problems without being able to independently widen their own authorization.

### 9. How should an overnight parser be treated?

Automation is represented as `users.kind = 'system'`. The parser receives only the role and grants required for its work and appears in audit history under its own `actor_id`. It is not an authorization bypass.

### 10. How do you answer “why can she do this and he can't?”

The authorization API returns evidence, not only a boolean.

For an allowed request it returns the authorizing grant, role, scope, and explanation. For a denied request it returns a specific reason code such as `NO_MATCHING_GRANT`, `INVALID_STAGE`, `USER_ABSENT`, or `SOD_VIOLATION`.

This makes two users' outcomes directly comparable.

### 11. How do you answer “who could have changed this job on the 3rd?”

Historical authorization is reconstructed using the job's scope, grants valid at the requested timestamp, and the role-permission state at that time.

`grant_events` records grant creation/revocation history, `role_permission_log` records permission changes, and the `who_could_act` API answers who was authorized at a historical timestamp. `job_events` separately answers who actually acted.

### 12. How is a new kind of role introduced while engineering is busy?

Insert the role into `roles`, map its actions in `role_permissions`, optionally configure `role_grant_authority`, and issue grants. Because the authorization engine reads these tables generically, introducing the role does not normally require Python changes.

### 13. How does “jobs waiting for me” stay consistent with actual authorization?

The waiting-list endpoint uses the same central `authorize_user()` function as action execution. A candidate job is included only when the canonical authorization engine returns `allowed = true` for the requested action.

The current implementation favors correctness and simplicity over large-list performance. At the 200,000-job scale, the same authorization predicate should be implemented as a set-based SQL query rather than authorizing every candidate job one at a time.

### 14. What happens when the system is unsure?

The system denies the action. Unknown actions, missing grants, invalid stages, scope mismatches, absences, SoD conflicts, missing approvals, revoked authority, and stale state all fail closed. A job is not mutated unless authorization can be positively established.

## 4. Scale and Performance

The target scale is 500 users and 200,000 jobs. Indexes on grant validity/user fields and job stage/scope fields reduce lookup cost.

A `scale_seed.sql` script generates the scale case using PostgreSQL `generate_series()`, which is much faster than issuing hundreds of thousands of individual application inserts.

The main known optimization area is the current `/jobs/waiting` implementation: it is logically correct because it reuses `authorize_user()`, but for large datasets it should be converted to a set-based authorization query so that list performance does not grow as one authorization call per job.

## 5. Conclusion

The design deliberately separates:

**Identity + Role + Scoped Grant + Action + Job State + Policy Rules + Time**

from the final authorization decision.

This supports broad and narrow responsibilities, client-side users, automation accounts, segregation of duties, absences, sensitive-action approvals, historical reconstruction, explainable decisions, and future role changes without embedding organizational policy directly into application code.
