## Sample Data

The repository includes a deterministic demo dataset designed to exercise the awkward authorization cases in the assignment rather than only the happy path.

### Load the demo data

From the repository root, after creating the schema:

```bash
psql -U postgres -d <database_name> -f demo_seed.sql
```

`demo_seed.sql` clears the demo tables, restarts their identity sequences, and loads the same IDs every time. This makes the API examples and recorded walkthrough reproducible.

If `psql` is not on the Windows `PATH`, the same file can be opened and executed in pgAdmin's Query Tool.

### Demo organizations

**Branches**

| ID | Branch |
|---:|---|
| 1 | Mumbai |
| 2 | Delhi |

**Clients**

| ID | Client |
|---:|---|
| 1 | ACME Imports |
| 2 | Beta Exports |

### Demo users and access

The following descriptions are the intended plain-English access definitions for the seeded users.

| User | Kind | Access in plain terms |
|---|---|---|
| **Ravi Maker** (`user_id=1`) | Staff | **Maker for every client, every branch, both directions, and every mode.** Ravi also has a **Checker** grant only for **ACME Imports, Mumbai branch, imports, all modes**. This demonstrates that one user can hold different roles over different scopes. |
| **Priya Checker** (`user_id=2`) | Staff | **Checker for ACME Imports, Mumbai branch, imports, all modes.** Priya is used in the “why can she do this?” demonstration. |
| **Amit MakerChecker** (`user_id=3`) | Staff | **Maker and Checker for ACME Imports, Mumbai branch, import, air jobs.** Amit is deliberately both qualified to prepare and check. The demo history records that he prepared `ACME-001`, so segregation-of-duties prevents him from checking that same job. |
| **Meera Filer** (`user_id=4`) | Staff | **Filer for ACME Imports, Mumbai branch, import, air jobs.** |
| **Alice ClientUser** (`user_id=5`) | Client | Client employee belonging to **ACME Imports**. Alice has the externally permitted **Viewer** role for **ACME only**, across all branches, directions, and modes. She can follow ACME shipments but cannot view Beta Exports jobs. |
| **Maya Admin** (`user_id=6`) | Staff | **Admin across all clients, branches, directions, and modes.** Maya can perform operational administration such as approve/reject and manage grants. The grant API still prevents her from granting a role to herself. |
| **ParserBot** (`user_id=7`) | System | Automated **Parser** account across all clients, branches, directions, and modes. Parser activity is recorded with ParserBot's own `actor_id` rather than being treated as an unaudited system bypass. |
| **Karan AbsentMaker** (`user_id=8`) | Staff | **Maker for ACME Imports, Mumbai branch, import, air jobs**, but has a seeded active absence covering the demo period. Authorization therefore denies actions while Karan is absent. |
| **Neha Manager** (`user_id=9`) | Staff | **Manager for ACME Imports only**, across all branches, directions, and modes. Neha can manage grants and request sensitive actions within ACME, but the grant API prevents her from delegating authority outside her own client scope. |
| **Sonia FormerChecker** (`user_id=10`) | Staff | Former **Checker for ACME Imports, Mumbai branch, imports, all modes**. Her grant is valid from **1 October 2026 until 10 October 2026** and is then revoked. She is included specifically to demonstrate historical authorization and responsibility changes. |

### Role permissions

| Role | Permissions |
|---|---|
| `maker` | `view`, `prepare` |
| `checker` | `view`, `check` |
| `filer` | `view`, `file` |
| `viewer` | `view` |
| `parser` | `view`, `parse` |
| `manager` | `view`, `cancel`, `reopen`, `approve`, `reject`, `manage_grants`, `reassign` |
| `admin` | `view`, `prepare`, `check`, `file`, `cancel`, `reopen`, `approve`, `reject`, `manage_grants`, `reassign` |

Only the `viewer` role is marked `external_ok = true` in the demo data.

### Grant authority

The demo configures grant authority separately from ordinary job permissions.

- `manager` may grant: `maker`, `checker`, `filer`, `viewer`, `parser`
- `admin` may grant: `maker`, `checker`, `filer`, `viewer`, `parser`, `manager`
- `admin -> admin` is deliberately not configured
- the API also rejects `manager_id == target_user_id`
- the API prevents a manager from delegating a broader client/branch/direction/mode scope than the manager already holds

### Segregation of duties

The seeded SoD rule is:

```text
check is blocked if the same actor previously performed prepare
```

This is demonstrated by `Amit MakerChecker` on `ACME-001`.

Amit has both Maker and Checker qualifications, but because the job history says he prepared that specific job, the authorization engine denies his `check` attempt. Priya can check the same job because she has a valid Checker grant and did not prepare it.

### Sensitive-action approval

The demo marks both `cancel` and `reopen` as requiring one independent approval.

The seeded workflow includes a pending cancellation request for `ACME-004`. The requester and approver must be different users. The approver must have the appropriate `approve` or `reject` permission, and the original requester is re-authorized before the job transition is executed.

### Demo jobs

| Job ID | Reference | Scope | Stage | Purpose |
|---:|---|---|---|---|
| 1 | `ACME-001` | ACME / Mumbai / import / air | `prepared` | Main Maker/Checker and SoD demonstration. Amit prepared it; Priya can check it. |
| 2 | `ACME-002` | ACME / Mumbai / import / air | `checked` | Ready for filing; demonstrates Filer authorization. |
| 3 | `ACME-003` | ACME / Mumbai / import / air | `confirmed` | Owned by Karan, who is currently absent. |
| 4 | `ACME-004` | ACME / Mumbai / import / air | `filed` | Has a pending cancellation request and demonstrates two-person approval. |
| 5 | `ACME-005` | ACME / Mumbai / import / air | `closed` | Demonstrates the reopen workflow. |
| 6 | `BETA-001` | Beta / Delhi / export / FCL | `confirmed` | Different-client scope test and ParserBot audit example. |

### Seeded audit cases

The seed deliberately includes historical records:

- Amit prepared `ACME-001`, enabling the Maker/Checker conflict demonstration.
- ParserBot updated `BETA-001`, showing that automated actors are auditable.
- Sonia's historical Checker grant was later revoked, allowing the `who_could_act` endpoint to distinguish past authorization from current authorization.
- `ACME-004` has a pending high-risk cancellation approval.

### Scale dataset

A second script generates the required scale case:

```bash
psql -U postgres -d <database_name> -f scale_seed.sql
```

`scale_seed.sql` generates:

- **500 users**
- **200,000 jobs**
- scoped grants distributed across the generated users
- deterministic clients, branches, directions, modes, and stages

The scale dataset is intended for list and authorization-performance testing. The smaller `demo_seed.sql` dataset is intentionally deterministic and human-readable so that edge cases can be demonstrated during the walkthrough.
