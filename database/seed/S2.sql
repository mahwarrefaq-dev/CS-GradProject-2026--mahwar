-- S2.sql - synthetic dataset S2 for «محور» (NFR-05, TC-22: dashboard load time)
-- One project, 1,000 tasks x 5 progress snapshots = 5,000 task_snapshots records.
-- 100 chains of 10 tasks linked finish-to-start = 900 dependencies.
-- Deterministic: every value is derived from the task number i (1..1000); no random().
-- Independent of S1 (own users and project). Suggested dashboard as_of: 2026-12-31.
-- Load:  psql -U mahwar -d mahwar -v ON_ERROR_STOP=1 -f database/seed/S2.sql
BEGIN;

-- Users: same synthetic test password as S1 (see S1_expected.md)
INSERT INTO users (username, display_alias, password_hash, role_id)
SELECT v.username, v.alias, '$2b$12$2wHtWbmJ819u.kRMPndF5uheZqXjnbWHMOghPRHy4Y9IAM7rqfogy', r.role_id
FROM (VALUES
  ('pm.s2',     'مدير-2', 'PROJECT_MANAGER'),
  ('member.s2', 'عضو-2',  'TEAM_MEMBER')
) AS v(username, alias, role_code)
JOIN roles r ON r.role_code = v.role_code;

INSERT INTO projects (project_code, project_name, project_type, manager_user_id,
                      planned_start_date, planned_end_date, team_size, status, data_mode)
SELECT 'PRJ-S2', 'مشروع اختبار الأداء S2', 'software', u.user_id,
       DATE '2026-01-01', DATE '2026-12-31', 1, 'active', 'synthetic'
FROM users u WHERE u.username = 'pm.s2';

INSERT INTO project_members (project_id, user_id, joined_at)
SELECT p.project_id, u.user_id, DATE '2026-01-01'
FROM projects p, users u
WHERE p.project_code = 'PRJ-S2' AND u.username IN ('pm.s2', 'member.s2');

-- 1,000 tasks. Chain g = (i-1)/10 (0..99), position k = (i-1)%10 (0..9).
-- start = 2026-01-01 + 3g + 5k ; duration 5 days ; priority cycles high/medium/low.
INSERT INTO tasks (project_id, task_code, task_name, priority, assignee_user_id,
                   planned_start_date, planned_due_date)
SELECT p.project_id,
       'T' || lpad(i::text, 4, '0'),
       'مهمة اصطناعية ' || i,
       (ARRAY['high','medium','low'])[(i % 3) + 1],
       u.user_id,
       DATE '2026-01-01' + (3 * ((i - 1) / 10) + 5 * ((i - 1) % 10)),
       DATE '2026-01-01' + (3 * ((i - 1) / 10) + 5 * ((i - 1) % 10)) + 4
FROM generate_series(1, 1000) AS i
JOIN projects p ON p.project_code = 'PRJ-S2'
JOIN users u ON u.username = 'member.s2';

INSERT INTO baselines (project_id, version_no, created_by, created_at, note)
SELECT p.project_id, 1, u.user_id, TIMESTAMPTZ '2026-01-01 06:00:00+00', 'خط الأساس لمجموعة الأداء S2'
FROM projects p, users u
WHERE p.project_code = 'PRJ-S2' AND u.username = 'pm.s2';

INSERT INTO baseline_tasks (baseline_id, task_id, planned_start_date, planned_due_date, priority)
SELECT b.baseline_id, t.task_id, t.planned_start_date, t.planned_due_date, t.priority
FROM tasks t
JOIN projects p ON p.project_id = t.project_id AND p.project_code = 'PRJ-S2'
JOIN baselines b ON b.project_id = p.project_id AND b.version_no = 1;

-- 900 FS dependencies: task i depends on task i-1 inside the same chain of 10.
INSERT INTO dependencies (predecessor_task_id, successor_task_id, dependency_type, lag_days, created_by)
SELECT tp.task_id, ts.task_id, 'FS', 0, u.user_id
FROM generate_series(1, 1000) AS i
JOIN projects p ON p.project_code = 'PRJ-S2'
JOIN tasks tp ON tp.project_id = p.project_id AND tp.task_code = 'T' || lpad((i - 1)::text, 4, '0')
JOIN tasks ts ON ts.project_id = p.project_id AND ts.task_code = 'T' || lpad(i::text, 4, '0')
JOIN users u ON u.username = 'pm.s2'
WHERE (i - 1) % 10 <> 0;

-- 5 snapshots per task (j = 0..4) on days start+0, +1, +3, +4, +6.
-- progress = 20j; the last snapshot is 'completed' (100%) when i % 3 = 0,
-- otherwise 80% 'in_progress' dated after the due date (an overdue task).
INSERT INTO task_snapshots (task_id, baseline_id, snapshot_date, snapshot_timestamp, update_source,
                            progress_pct, status_at_snapshot, remaining_estimate_days, recorded_by)
SELECT t.task_id, b.baseline_id, d.snap_d, (d.snap_d + TIME '12:00') AT TIME ZONE 'UTC', 'import',
       d.pct, d.status, GREATEST(5 - j, 0), t.assignee_user_id
FROM generate_series(1, 1000) AS i
CROSS JOIN generate_series(0, 4) AS j
JOIN projects p ON p.project_code = 'PRJ-S2'
JOIN tasks t ON t.project_id = p.project_id AND t.task_code = 'T' || lpad(i::text, 4, '0')
JOIN baselines b ON b.project_id = p.project_id AND b.version_no = 1
CROSS JOIN LATERAL (
  SELECT t.planned_start_date + (ARRAY[0, 1, 3, 4, 6])[j + 1] AS snap_d,
         CASE WHEN j = 4 AND i % 3 = 0 THEN 100 ELSE 20 * j END AS pct,
         CASE WHEN j = 0 THEN 'not_started'
              WHEN j = 4 AND i % 3 = 0 THEN 'completed'
              ELSE 'in_progress' END AS status
) d;

COMMIT;
