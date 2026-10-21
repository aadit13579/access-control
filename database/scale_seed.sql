-- scale_seed.sql
-- Development/test data generator for:
--   500 staff users
--   50 clients
--   10 branches
--   200,000 jobs
--   500 checker grants (one client per user)
--
-- Assumptions:
--   1. Role 'checker' exists.
--   2. Action 'check' exists and checker has permission for it.
--   3. User id 6 exists and is used only as the seed-data granted_by actor.
--   4. This is run against a development/test database.
--
-- All generated data uses SCALE_ / SCALE- prefixes.

BEGIN;

-- ------------------------------------------------------------
-- 1. Clients
-- ------------------------------------------------------------
INSERT INTO clients (name)
SELECT 'SCALE_CLIENT_' || lpad(gs::text, 3, '0')
FROM generate_series(1, 50) AS gs
ON CONFLICT (name) DO NOTHING;

-- ------------------------------------------------------------
-- 2. Branches
-- ------------------------------------------------------------
INSERT INTO branches (name)
SELECT 'SCALE_BRANCH_' || lpad(gs::text, 3, '0')
FROM generate_series(1, 10) AS gs
ON CONFLICT (name) DO NOTHING;

-- ------------------------------------------------------------
-- 3. 500 staff users
--
-- users.name is not UNIQUE in the schema, so NOT EXISTS is used
-- to make this reasonably safe to rerun before those users are
-- involved in other test data.
-- ------------------------------------------------------------
INSERT INTO users (name, kind, client_id, is_active)
SELECT
    'SCALE_USER_' || lpad(gs::text, 4, '0'),
    'staff',
    NULL,
    true
FROM generate_series(1, 500) AS gs
WHERE NOT EXISTS (
    SELECT 1
    FROM users u
    WHERE u.name = 'SCALE_USER_' || lpad(gs::text, 4, '0')
);

-- ------------------------------------------------------------
-- Build deterministic lookup tables for the generated objects.
-- ------------------------------------------------------------
CREATE TEMP TABLE scale_clients AS
SELECT
    row_number() OVER (ORDER BY id)::int AS rn,
    id
FROM clients
WHERE name LIKE 'SCALE_CLIENT_%';

CREATE TEMP TABLE scale_branches AS
SELECT
    row_number() OVER (ORDER BY id)::int AS rn,
    id
FROM branches
WHERE name LIKE 'SCALE_BRANCH_%';

CREATE TEMP TABLE scale_users AS
SELECT
    row_number() OVER (ORDER BY id)::int AS rn,
    id
FROM users
WHERE name LIKE 'SCALE_USER_%'
ORDER BY id
LIMIT 500;

-- Fail naturally later if these counts are not what we expect.
-- Useful visibility while running in psql:
SELECT 'scale_users' AS item, count(*) AS count FROM scale_users;
SELECT 'scale_clients' AS item, count(*) AS count FROM scale_clients;
SELECT 'scale_branches' AS item, count(*) AS count FROM scale_branches;

-- ------------------------------------------------------------
-- 4. Give every scale user a checker grant for one client.
--
-- Scope:
--   client    = one of the 50 scale clients
--   branch    = ALL
--   direction = ALL
--   mode      = ALL
--
-- This creates useful authorization selectivity: each user only
-- covers about 1/50th of the generated jobs by client.
--
-- Existing exact active grants are not duplicated.
-- ------------------------------------------------------------
INSERT INTO grants (
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
    granted_by,
    reason
)
SELECT
    su.id,
    'checker',
    sc.id,
    false,
    NULL,
    true,
    NULL,
    true,
    NULL,
    true,
    6,
    'Scale test seed grant'
FROM scale_users su
JOIN scale_clients sc
  ON sc.rn = ((su.rn - 1) % 50) + 1
WHERE EXISTS (
    SELECT 1 FROM users WHERE id = 6
)
AND EXISTS (
    SELECT 1 FROM roles WHERE code = 'checker'
)
AND NOT EXISTS (
    SELECT 1
    FROM grants g
    WHERE g.user_id = su.id
      AND g.role_code = 'checker'
      AND g.client_id = sc.id
      AND g.client_all = false
      AND g.branch_id IS NULL
      AND g.branch_all = true
      AND g.direction IS NULL
      AND g.direction_all = true
      AND g.mode IS NULL
      AND g.mode_all = true
      AND CURRENT_TIMESTAMP >= g.valid_from
      AND CURRENT_TIMESTAMP < g.valid_to
      AND g.revoked_by IS NULL
);


-- ------------------------------------------------------------
-- 4b. Mirror scale grants into immutable grant_events.
--     This keeps the directly seeded grants consistent with the
--     audit design normally enforced by the grant API.
-- ------------------------------------------------------------
INSERT INTO grant_events (
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
    reason
)
SELECT
    g.id,
    g.user_id,
    'grant',
    g.role_code,
    g.client_id,
    g.client_all,
    g.branch_id,
    g.branch_all,
    g.direction,
    g.direction_all,
    g.mode,
    g.mode_all,
    g.valid_from,
    g.valid_to,
    g.granted_by,
    g.reason
FROM grants g
JOIN scale_users su
  ON su.id = g.user_id
WHERE g.reason = 'Scale test seed grant'
  AND NOT EXISTS (
      SELECT 1
      FROM grant_events ge
      WHERE ge.grant_id = g.id
        AND ge.action = 'grant'
  );

-- ------------------------------------------------------------
-- 5. 200,000 jobs
--
-- Distribution is deterministic:
--   50 clients
--   10 branches
--   import/export alternating
--   air/fcl/lcl rotating
--   workflow stages rotating
--
-- owner_id is NULL so jobs are in the common pool.
-- ------------------------------------------------------------
INSERT INTO jobs (
    ref,
    client_id,
    branch_id,
    direction,
    mode,
    stage,
    owner_id
)
SELECT
    'SCALE-JOB-' || lpad(gs::text, 6, '0'),

    sc.id,
    sb.id,

    CASE
        WHEN gs % 2 = 0 THEN 'import'::direction
        ELSE 'export'::direction
    END,

    CASE gs % 3
        WHEN 0 THEN 'air'::mode
        WHEN 1 THEN 'fcl'::mode
        ELSE 'lcl'::mode
    END,

    CASE gs % 7
        WHEN 0 THEN 'confirmed'::stage
        WHEN 1 THEN 'prepared'::stage
        WHEN 2 THEN 'checked'::stage
        WHEN 3 THEN 'filed'::stage
        WHEN 4 THEN 'cancelled'::stage
        WHEN 5 THEN 'reopened'::stage
        ELSE 'closed'::stage
    END,

    NULL
FROM generate_series(1, 200000) AS gs
JOIN scale_clients sc
  ON sc.rn = ((gs - 1) % 50) + 1
JOIN scale_branches sb
  ON sb.rn = ((gs - 1) % 10) + 1
ON CONFLICT (ref) DO NOTHING;

COMMIT;

-- ------------------------------------------------------------
-- Verification
-- ------------------------------------------------------------

SELECT count(*) AS scale_users
FROM users
WHERE name LIKE 'SCALE_USER_%';

SELECT count(*) AS scale_jobs
FROM jobs
WHERE ref LIKE 'SCALE-JOB-%';

SELECT stage, count(*) AS jobs
FROM jobs
WHERE ref LIKE 'SCALE-JOB-%'
GROUP BY stage
ORDER BY stage;

SELECT count(*) AS scale_checker_grants
FROM grants g
JOIN users u ON u.id = g.user_id
WHERE u.name LIKE 'SCALE_USER_%'
  AND g.role_code = 'checker'
  AND CURRENT_TIMESTAMP >= g.valid_from
  AND CURRENT_TIMESTAMP < g.valid_to
  AND g.revoked_by IS NULL;

-- Example user IDs for API testing:
SELECT id, name
FROM users
WHERE name LIKE 'SCALE_USER_%'
ORDER BY id
LIMIT 10;
