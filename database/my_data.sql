-- demo_seed.sql
-- DEV/DEMO ONLY. Clears demo tables and inserts a deterministic walkthrough dataset.

ALTER TYPE stage ADD VALUE IF NOT EXISTS 'closed';

TRUNCATE TABLE approvals,
action_approval_rules,
job_events,
jobs,
absences,
grant_events,
grants,
role_permission_log,
role_grant_authority,
sod_rules,
role_permissions,
actions,
roles,
users,
clients,
branches
RESTART IDENTITY CASCADE;

INSERT INTO branches (name) VALUES ('Mumbai'), ('Delhi');

INSERT INTO clients (name) VALUES ('ACME Imports'), ('Beta Exports');

INSERT INTO
    users (
        name,
        kind,
        client_id,
        is_active
    )
VALUES (
        'Ravi Maker',
        'staff',
        NULL,
        true
    ),
    (
        'Priya Checker',
        'staff',
        NULL,
        true
    ),
    (
        'Amit MakerChecker',
        'staff',
        NULL,
        true
    ),
    (
        'Meera Filer',
        'staff',
        NULL,
        true
    ),
    (
        'Alice ClientUser',
        'client',
        1,
        true
    ),
    (
        'Maya Admin',
        'staff',
        NULL,
        true
    ),
    (
        'ParserBot',
        'system',
        NULL,
        true
    ),
    (
        'Karan AbsentMaker',
        'staff',
        NULL,
        true
    ),
    (
        'Neha Manager',
        'staff',
        NULL,
        true
    ),
    (
        'Sonia FormerChecker',
        'staff',
        NULL,
        true
    );

INSERT INTO actions (code, from_stages, to_stage) VALUES
    ('view',          NULL,                              NULL),
    ('prepare',       ARRAY['confirmed']::stage[],       'prepared'),
    ('check',         ARRAY['prepared']::stage[],        'checked'),
    ('file',          ARRAY['checked']::stage[],         'filed'),
    ('cancel',        ARRAY['filed']::stage[],           'cancelled'),
    ('reopen',        ARRAY['closed']::stage[],          'reopened'),
    ('approve',       NULL,                              NULL),
    ('reject',        NULL,                              NULL),
    ('manage_grants', NULL,                              NULL),
    ('reassign',      NULL,                              NULL),
    ('parse',         NULL,                              NULL);

INSERT INTO
    roles (code, external_ok)
VALUES ('maker', false),
    ('checker', false),
    ('filer', false),
    ('viewer', true),
    ('parser', false),
    ('manager', false),
    ('admin', false);

INSERT INTO
    role_permissions (role_code, action)
VALUES ('maker', 'view'),
    ('maker', 'prepare'),
    ('checker', 'view'),
    ('checker', 'check'),
    ('filer', 'view'),
    ('filer', 'file'),
    ('viewer', 'view'),
    ('parser', 'view'),
    ('parser', 'parse'),
    ('manager', 'view'),
    ('manager', 'cancel'),
    ('manager', 'reopen'),
    ('manager', 'approve'),
    ('manager', 'reject'),
    ('manager', 'manage_grants'),
    ('manager', 'reassign'),
    ('admin', 'view'),
    ('admin', 'prepare'),
    ('admin', 'check'),
    ('admin', 'file'),
    ('admin', 'cancel'),
    ('admin', 'reopen'),
    ('admin', 'approve'),
    ('admin', 'reject'),
    ('admin', 'manage_grants'),
    ('admin', 'reassign');

INSERT INTO role_permission_log (role_code, action, change, changed_by, reason, at)
SELECT role_code, action, 'add', 6, 'Initial demo permission state',
       '2026-10-01 00:00:00+00'::timestamptz
FROM role_permissions;

INSERT INTO
    role_grant_authority (manager_role, grantable_role)
VALUES ('manager', 'maker'),
    ('manager', 'checker'),
    ('manager', 'filer'),
    ('manager', 'viewer'),
    ('manager', 'parser'),
    ('admin', 'maker'),
    ('admin', 'checker'),
    ('admin', 'filer'),
    ('admin', 'viewer'),
    ('admin', 'parser'),
    ('admin', 'manager');

INSERT INTO
    sod_rules (action, blocked_if_actor_did)
VALUES ('check', 'prepare');

INSERT INTO
    action_approval_rules (action, approvals_required)
VALUES ('cancel', 1),
    ('reopen', 1);

-- Grants
INSERT INTO
    grants (
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
        granted_by,
        reason
    )
VALUES (
        1,
        'maker',
        NULL,
        true,
        NULL,
        true,
        NULL,
        true,
        NULL,
        true,
        '2026-10-01 00:00:00+00',
        'infinity',
        6,
        'Maker for all clients'
    ),
    (
        1,
        'checker',
        1,
        false,
        1,
        false,
        'import',
        false,
        NULL,
        true,
        '2026-10-01 00:00:00+00',
        'infinity',
        6,
        'Checker only for ACME Mumbai imports'
    ),
    (
        2,
        'checker',
        1,
        false,
        1,
        false,
        'import',
        false,
        NULL,
        true,
        '2026-10-01 00:00:00+00',
        'infinity',
        6,
        'ACME Mumbai import checker'
    ),
    (
        3,
        'maker',
        1,
        false,
        1,
        false,
        'import',
        false,
        'air',
        false,
        '2026-10-01 00:00:00+00',
        'infinity',
        6,
        'ACME air maker'
    ),
    (
        3,
        'checker',
        1,
        false,
        1,
        false,
        'import',
        false,
        'air',
        false,
        '2026-10-01 00:00:00+00',
        'infinity',
        6,
        'ACME air checker'
    ),
    (
        4,
        'filer',
        1,
        false,
        1,
        false,
        'import',
        false,
        'air',
        false,
        '2026-10-01 00:00:00+00',
        'infinity',
        6,
        'ACME air filer'
    ),
    (
        5,
        'viewer',
        1,
        false,
        NULL,
        true,
        NULL,
        true,
        NULL,
        true,
        '2026-10-01 00:00:00+00',
        'infinity',
        6,
        'Client employee may view ACME shipments'
    ),
    (
        6,
        'admin',
        NULL,
        true,
        NULL,
        true,
        NULL,
        true,
        NULL,
        true,
        '2026-10-01 00:00:00+00',
        'infinity',
        6,
        'Initial bootstrap admin grant'
    ),
    (
        7,
        'parser',
        NULL,
        true,
        NULL,
        true,
        NULL,
        true,
        NULL,
        true,
        '2026-10-01 00:00:00+00',
        'infinity',
        6,
        'Automated overnight parser'
    ),
    (
        8,
        'maker',
        1,
        false,
        1,
        false,
        'import',
        false,
        'air',
        false,
        '2026-10-01 00:00:00+00',
        'infinity',
        6,
        'ACME air maker'
    ),
    (
        9,
        'manager',
        1,
        false,
        NULL,
        true,
        NULL,
        true,
        NULL,
        true,
        '2026-10-01 00:00:00+00',
        'infinity',
        6,
        'Manager for ACME only'
    );

INSERT INTO
    grants (
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
        granted_by,
        reason,
        revoked_by
    )
VALUES (
        10,
        'checker',
        1,
        false,
        1,
        false,
        'import',
        false,
        NULL,
        true,
        '2026-10-01 00:00:00+00',
        '2026-10-10 00:00:00+00',
        6,
        'Temporary checker assignment',
        6
    );

-- Grant audit events
INSERT INTO
    grant_events (
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
        reason,
        at
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
    reason,
    valid_from
FROM grants
WHERE
    user_id <> 10;

INSERT INTO grant_events (
    grant_id, target_user_id, action, role_code,
    client_id, client_all, branch_id, branch_all,
    direction, direction_all, mode, mode_all,
    valid_from, valid_to, actor_id, reason, at
)
SELECT
    id, user_id, 'grant', role_code,
    client_id, client_all, branch_id, branch_all,
    direction, direction_all, mode, mode_all,
    valid_from, 'infinity'::timestamptz, granted_by,
    'Temporary checker assignment created', valid_from
FROM grants
WHERE user_id = 10;

INSERT INTO
    grant_events (
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
        reason,
        at
    )
SELECT
    id,
    user_id,
    'revoke',
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
    6,
    'Temporary responsibility ended',
    valid_to
FROM grants
WHERE
    user_id = 10;

-- Karan is absent during the live demo.
INSERT INTO
    absences (user_id, starts_at, ends_at)
VALUES (
        8,
        CURRENT_TIMESTAMP - INTERVAL '1 day',
        CURRENT_TIMESTAMP + INTERVAL '2 days'
    );

INSERT INTO
    jobs (
        ref,
        client_id,
        branch_id,
        direction,
        mode,
        stage,
        owner_id
    )
VALUES (
        'ACME-001',
        1,
        1,
        'import',
        'air',
        'prepared',
        NULL
    ),
    (
        'ACME-002',
        1,
        1,
        'import',
        'air',
        'checked',
        4
    ),
    (
        'ACME-003',
        1,
        1,
        'import',
        'air',
        'confirmed',
        8
    ),
    (
        'ACME-004',
        1,
        1,
        'import',
        'air',
        'filed',
        9
    ),
    (
        'ACME-005',
        1,
        1,
        'import',
        'air',
        'closed',
        9
    ),
    (
        'BETA-001',
        2,
        2,
        'export',
        'fcl',
        'confirmed',
        NULL
    );

-- Amit prepared Job 1. SoD now blocks Amit from checking it.
INSERT INTO
    job_events (
        job_id,
        actor_id,
        action,
        from_stage,
        to_stage,
        outcome,
        grant_id,
        reason,
        at
    )
VALUES (
        1,
        3,
        'prepare',
        'confirmed',
        'prepared',
        'allowed',
        (
            SELECT id
            FROM grants
            WHERE
                user_id = 3
                AND role_code = 'maker'
            ORDER BY id
            LIMIT 1
        ),
        'Checklist prepared by Amit',
        CURRENT_TIMESTAMP - INTERVAL '30 minutes'
    );

-- Automated system-account history example.
INSERT INTO
    job_events (
        job_id,
        actor_id,
        action,
        from_stage,
        to_stage,
        outcome,
        grant_id,
        reason,
        at
    )
VALUES (
        6,
        7,
        'parse',
        'confirmed',
        'confirmed',
        'allowed',
        (
            SELECT id
            FROM grants
            WHERE
                user_id = 7
                AND role_code = 'parser'
            ORDER BY id
            LIMIT 1
        ),
        'Overnight parser refreshed shipment data',
        CURRENT_TIMESTAMP - INTERVAL '2 hours'
    );

-- Pending cancel request for Q6.
INSERT INTO
    approvals (
        job_id,
        action,
        requested_by,
        reason,
        status
    )
VALUES (
        4,
        'cancel',
        9,
        'Filed against the wrong invoice',
        'pending'
    );

-- Quick verification
SELECT id, name, kind, client_id FROM users ORDER BY id;

SELECT
    id,
    ref,
    client_id,
    branch_id,
    direction,
    mode,
    stage,
    owner_id
FROM jobs
ORDER BY id;

SELECT
    id,
    job_id,
    action,
    requested_by,
    decided_by,
    status
FROM approvals
ORDER BY id;