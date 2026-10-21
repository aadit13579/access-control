CREATE TYPE direction AS ENUM ('import','export');

CREATE TYPE mode      AS ENUM ('air','fcl','lcl');

CREATE TYPE stage     AS ENUM ('confirmed','prepared','checked','filed','cancelled','reopened', 'closed');

CREATE TABLE branches (
    id serial PRIMARY KEY,
    name text UNIQUE NOT NULL
);

CREATE TABLE clients (
    id serial PRIMARY KEY,
    name text UNIQUE NOT NULL
);

-- users holds facts about the person only, never their roles.
CREATE TABLE users (
    id serial PRIMARY KEY,
    name text NOT NULL,
    kind text NOT NULL CHECK (
        kind IN ('staff', 'client', 'system')
    ),
    client_id int REFERENCES clients, -- client-side users belong to one client
    is_active boolean NOT NULL DEFAULT true,
    CHECK (
        (kind = 'client') = (client_id IS NOT NULL)
    )
);

CREATE TABLE absences (
    user_id int NOT NULL REFERENCES users,
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL,
    CHECK (starts_at < ends_at)
);

-- If roles and stage rules are hardcoded in Python, that request needs a deploy. As rows, it’s an INSERT by an admin.
CREATE TABLE actions (
  code text PRIMARY KEY,                       -- view, prepare, check, file, cancel, reopen, ...
  from_stages stage[],                         -- stages the job must be in (NULL = any, e.g. view)
  to_stage stage                               -- NULL = no transition
);

CREATE TABLE roles (
    code text PRIMARY KEY,
    external_ok boolean NOT NULL DEFAULT false -- may a client-side user hold this role?
);

CREATE TABLE role_permissions (
    role_code text REFERENCES roles,
    action text REFERENCES actions,
    PRIMARY KEY (role_code, action)
);

CREATE TABLE role_grant_authority ( -- who may hand out which roles (Q8)
    manager_role text REFERENCES roles,
    grantable_role text REFERENCES roles,
    PRIMARY KEY (manager_role, grantable_role)
);

CREATE TABLE sod_rules ( -- maker/checker as data (Q3)
    action text REFERENCES actions,
    blocked_if_actor_did text REFERENCES actions,
    PRIMARY KEY (action, blocked_if_actor_did)
);

-- WHERE: one row = one role over one scope for one time window
CREATE TABLE grants (
    id bigserial PRIMARY KEY,
    user_id int NOT NULL REFERENCES users,
    role_code text NOT NULL REFERENCES roles,
    client_id int REFERENCES clients,
    client_all boolean NOT NULL DEFAULT false,
    branch_id int REFERENCES branches,
    branch_all boolean NOT NULL DEFAULT false,
    direction direction,
    direction_all boolean NOT NULL DEFAULT false,
    mode mode,
    mode_all boolean NOT NULL DEFAULT false,
    valid_from timestamptz NOT NULL DEFAULT now(),
    valid_to timestamptz NOT NULL DEFAULT 'infinity',
    granted_by int NOT NULL REFERENCES users,
    reason text NOT NULL,
    revoked_by int REFERENCES users,
    CHECK (
        (client_id IS NOT NULL) <> client_all
    ), -- exactly one: a value OR "all"
    CHECK (
        (branch_id IS NOT NULL) <> branch_all
    ),
    CHECK (
        (direction IS NOT NULL) <> direction_all
    ),
    CHECK (
        (mode IS NOT NULL) <> mode_all
    ),
    CHECK (valid_from < valid_to)
);

CREATE INDEX ON grants (user_id, valid_from, valid_to);

-- THINGS
CREATE TABLE jobs (
    id bigserial PRIMARY KEY,
    ref text UNIQUE NOT NULL,
    client_id int NOT NULL REFERENCES clients,
    branch_id int NOT NULL REFERENCES branches,
    direction direction NOT NULL,
    mode mode NOT NULL,
    stage stage NOT NULL,
    owner_id int REFERENCES users, -- NULL = in the pool, anyone eligible
    version int NOT NULL DEFAULT 1 -- optimistic concurrency
);

CREATE INDEX ON jobs (stage, client_id, branch_id);

-- HISTORY: append-only (revoke UPDATE/DELETE, or add a trigger)
CREATE TABLE job_events (
    id bigserial PRIMARY KEY,
    job_id bigint NOT NULL REFERENCES jobs,
    actor_id int NOT NULL REFERENCES users,
    action text NOT NULL,
    from_stage stage,
    to_stage stage,
    outcome text NOT NULL CHECK (
        outcome IN ('allowed', 'denied')
    ),
    grant_id bigint REFERENCES grants, -- the grant that authorised it (Q10, Q11)
    reason text,
    at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE approvals ( -- two-person rule for risky actions (Q6)
    id bigserial PRIMARY KEY,
    job_id bigint NOT NULL REFERENCES jobs,
    action text NOT NULL,
    requested_by int NOT NULL REFERENCES users,
    reason text NOT NULL,
    decided_by int REFERENCES users,
    status text NOT NULL DEFAULT 'pending'
);

CREATE OR REPLACE FUNCTION prevent_modification()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'Table % is append-only: % operations are not allowed',
        TG_TABLE_NAME,
        TG_OP;
END;
$$;

CREATE TRIGGER job_events_append_only
BEFORE UPDATE OR DELETE
ON job_events
FOR EACH ROW
EXECUTE FUNCTION prevent_modification();

CREATE TABLE role_permission_log (
    id bigserial PRIMARY KEY,
    role_code text NOT NULL,
    action text NOT NULL,
    change text NOT NULL CHECK (
        change IN ('add', 'remove')
    ),
    changed_by int NOT NULL REFERENCES users,
    reason text NOT NULL,
    at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER role_permission_log_append_only
BEFORE UPDATE OR DELETE ON role_permission_log
FOR EACH ROW EXECUTE FUNCTION prevent_modification();

ALTER TABLE approvals
ADD CONSTRAINT approvals_action_fk FOREIGN KEY (action) REFERENCES actions (code);

ALTER TABLE approvals
ADD CONSTRAINT approvals_status_check CHECK (
    status IN (
        'pending',
        'approved',
        'rejected'
    )
);

ALTER TABLE approvals
ADD CONSTRAINT approvals_two_person_rule CHECK (
    decided_by IS NULL
    OR decided_by <> requested_by
);

CREATE TABLE action_approval_rules (
    action text PRIMARY KEY REFERENCES actions (code),
    approvals_required int NOT NULL DEFAULT 1 CHECK (approvals_required > 0)
);