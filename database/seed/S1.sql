-- S1.sql - synthetic dataset S1 for «محور» (Chapter 4, section 4.11; Test_Plan TC-01..TC-26)
-- Ten tasks whose expected results are computed by hand in S1_expected.md.
-- Reference date for all expected results: as_of = 2026-03-16.
-- Fully synthetic (data_mode = 'synthetic'); pseudonymous codes only (NFR-01).
-- Requires: database/Schema_Script.sql already run (roles and rule_parameters seeded).
-- Load:  psql -U mahwar -d mahwar -v ON_ERROR_STOP=1 -f database/seed/S1.sql
-- Test password of every S1 user: see S1_expected.md (bcrypt hash stored here).
BEGIN;

-- Users (TBL-02) -------------------------------------------------------------
INSERT INTO users (username, display_alias, password_hash, role_id)
SELECT v.username, v.alias, '$2b$12$2wHtWbmJ819u.kRMPndF5uheZqXjnbWHMOghPRHy4Y9IAM7rqfogy', r.role_id
FROM (VALUES
  ('pm.s1',      'مدير-1',   'PROJECT_MANAGER'),
  ('member.a',   'عضو-أ',    'TEAM_MEMBER'),
  ('member.b',   'عضو-ب',    'TEAM_MEMBER'),
  ('member.c',   'عضو-ج',    'TEAM_MEMBER'),
  ('admin.s1',   'مسؤول-1',  'SYSTEM_ADMIN'),
  ('planner.s1', 'مخطط-1',   'PLANNER')
) AS v(username, alias, role_code)
JOIN roles r ON r.role_code = v.role_code;

-- Project (TBL-03) and members (TBL-04) --------------------------------------
INSERT INTO projects (project_code, project_name, project_type, manager_user_id,
                      planned_start_date, planned_end_date, team_size, status, data_mode)
SELECT 'PRJ-S1', 'مشروع اختبار S1', 'software', u.user_id,
       DATE '2026-03-01', DATE '2026-03-31', 3, 'active', 'synthetic'
FROM users u WHERE u.username = 'pm.s1';

INSERT INTO project_members (project_id, user_id, joined_at)
SELECT p.project_id, u.user_id, DATE '2026-03-01'
FROM projects p, users u
WHERE p.project_code = 'PRJ-S1' AND u.username IN ('pm.s1', 'member.a', 'member.b', 'member.c');

-- Tasks (TBL-06) -------------------------------------------------------------
INSERT INTO tasks (project_id, task_code, task_name, priority, assignee_user_id,
                   planned_start_date, planned_due_date)
SELECT p.project_id, v.code, v.name, v.priority, u.user_id, v.start_d::date, v.due_d::date
FROM (VALUES
  ('T01', 'تحليل المتطلبات',          'high',   'member.a', '2026-03-01', '2026-03-03'),
  ('T02', 'تصميم قاعدة البيانات',     'high',   'member.a', '2026-03-04', '2026-03-06'),
  ('T03', 'تصميم الواجهات',           'medium', 'member.b', '2026-03-04', '2026-03-07'),
  ('T04', 'إعداد بيئة التطوير',       'low',    'member.b', '2026-03-01', '2026-03-02'),
  ('T05', 'تطوير الخدمة الخلفية',     'high',   'member.a', '2026-03-07', '2026-03-12'),
  ('T06', 'تطوير الواجهة',            'medium', 'member.b', '2026-03-08', '2026-03-13'),
  ('T07', 'واجهات API للتقارير',      'high',   'member.c', '2026-03-13', '2026-03-19'),
  ('T08', 'اختبار التكامل',           'high',   'member.b', '2026-03-20', '2026-03-24'),
  ('T09', 'ترحيل البيانات',           'medium', 'member.a', '2026-03-13', '2026-03-22'),
  ('T10', 'التوثيق',                  'low',    'member.b', '2026-03-11', '2026-03-20')
) AS v(code, name, priority, assignee, start_d, due_d)
JOIN projects p ON p.project_code = 'PRJ-S1'
JOIN users u ON u.username = v.assignee;

-- Baseline v1 (TBL-05) and its task copy (TBL-07) ----------------------------
INSERT INTO baselines (project_id, version_no, created_by, created_at, note)
SELECT p.project_id, 1, u.user_id, TIMESTAMPTZ '2026-03-01 06:00:00+00', 'خط الأساس الأول لمجموعة S1'
FROM projects p, users u
WHERE p.project_code = 'PRJ-S1' AND u.username = 'pm.s1';

INSERT INTO baseline_tasks (baseline_id, task_id, planned_start_date, planned_due_date, priority)
SELECT b.baseline_id, t.task_id, t.planned_start_date, t.planned_due_date, t.priority
FROM tasks t
JOIN projects p ON p.project_id = t.project_id AND p.project_code = 'PRJ-S1'
JOIN baselines b ON b.project_id = p.project_id AND b.version_no = 1;

-- Dependencies (TBL-11), finish-to-start only, lag 0 --------------------------
INSERT INTO dependencies (predecessor_task_id, successor_task_id, dependency_type, lag_days, created_by)
SELECT tp.task_id, ts.task_id, 'FS', 0, u.user_id
FROM (VALUES
  ('T01', 'T02'), ('T01', 'T03'), ('T02', 'T05'), ('T03', 'T06'),
  ('T05', 'T07'), ('T05', 'T09'), ('T07', 'T08'), ('T06', 'T08')
) AS v(pred, succ)
JOIN projects p ON p.project_code = 'PRJ-S1'
JOIN tasks tp ON tp.project_id = p.project_id AND tp.task_code = v.pred
JOIN tasks ts ON ts.project_id = p.project_id AND ts.task_code = v.succ
JOIN users u ON u.username = 'pm.s1';

-- Task snapshots (TBL-08), append-only; T05 has two snapshots (TC-06) --------
INSERT INTO task_snapshots (task_id, baseline_id, snapshot_date, snapshot_timestamp, update_source,
                            progress_pct, status_at_snapshot, remaining_estimate_days, blocker_note, recorded_by)
SELECT t.task_id, b.baseline_id, v.snap_d::date, v.snap_ts::timestamptz, 'manual',
       v.pct, v.status, v.remaining, v.blocker, t.assignee_user_id
FROM (VALUES
  ('T01', '2026-03-03', '2026-03-03 12:00:00+00', 100, 'completed',   0.0,  NULL),
  ('T02', '2026-03-06', '2026-03-06 12:00:00+00', 100, 'completed',   0.0,  NULL),
  ('T03', '2026-03-07', '2026-03-07 12:00:00+00', 100, 'completed',   0.0,  NULL),
  ('T04', '2026-03-02', '2026-03-02 12:00:00+00', 100, 'completed',   0.0,  NULL),
  ('T05', '2026-03-10', '2026-03-10 12:00:00+00',  50, 'in_progress', 3.0,  NULL),
  ('T05', '2026-03-15', '2026-03-15 12:00:00+00',  80, 'in_progress', 2.0,  NULL),
  ('T06', '2026-03-15', '2026-03-15 13:00:00+00',  60, 'blocked',     3.0,  'بانتظار توفر خادم الاختبار R3'),
  ('T07', '2026-03-15', '2026-03-15 14:00:00+00',   0, 'not_started', 7.0,  NULL),
  ('T08', '2026-03-08', '2026-03-08 12:00:00+00',   0, 'not_started', 5.0,  NULL),
  ('T09', '2026-03-15', '2026-03-15 15:00:00+00',  30, 'in_progress', 7.0,  NULL),
  ('T10', '2026-03-15', '2026-03-15 16:00:00+00',  40, 'in_progress', 6.0,  NULL)
) AS v(code, snap_d, snap_ts, pct, status, remaining, blocker)
JOIN projects p ON p.project_code = 'PRJ-S1'
JOIN tasks t ON t.project_id = p.project_id AND t.task_code = v.code
JOIN baselines b ON b.project_id = p.project_id AND b.version_no = 1;

-- Resources (TBL-12) ---------------------------------------------------------
INSERT INTO resources (resource_code, resource_type, linked_user_id, default_capacity_hours)
SELECT v.code, v.rtype, u.user_id, v.cap
FROM (VALUES
  ('R1', 'human',     'member.a', 8.00),
  ('R2', 'human',     'member.b', 8.00),
  ('R3', 'equipment', NULL,       8.00),
  ('R4', 'human',     'member.c', 8.00)
) AS v(code, rtype, username, cap)
LEFT JOIN users u ON u.username = v.username;

-- Resource snapshots (TBL-13): R2 drops to 60% (M2, TC-09), R3 drops to 45% (H3)
INSERT INTO resource_snapshots (resource_id, snapshot_date, capacity_hours, availability_pct, note, recorded_by, recorded_at)
SELECT r.resource_id, v.snap_d::date, v.cap, v.avail, v.note, u.user_id, (v.snap_d || ' 08:00:00+00')::timestamptz
FROM (VALUES
  ('R1', '2026-03-01', 8.00, 100, NULL),
  ('R2', '2026-03-01', 8.00, 100, NULL),
  ('R2', '2026-03-14', 4.80,  60, 'دوام جزئي'),
  ('R3', '2026-03-01', 8.00, 100, NULL),
  ('R3', '2026-03-14', 3.60,  45, 'صيانة جزئية'),
  ('R4', '2026-03-01', 8.00, 100, NULL)
) AS v(code, snap_d, cap, avail, note)
JOIN resources r ON r.resource_code = v.code
JOIN users u ON u.username = 'planner.s1';

-- Task allocations (TBL-14) --------------------------------------------------
INSERT INTO task_allocations (task_id, resource_id, allocated_hours)
SELECT t.task_id, r.resource_id, v.hours
FROM (VALUES
  ('T05', 'R1', 48), ('T06', 'R2', 48), ('T06', 'R3', 16), ('T07', 'R4', 56),
  ('T08', 'R2', 40), ('T08', 'R3', 16), ('T09', 'R1', 80), ('T10', 'R2', 40)
) AS v(code, res, hours)
JOIN projects p ON p.project_code = 'PRJ-S1'
JOIN tasks t ON t.project_id = p.project_id AND t.task_code = v.code
JOIN resources r ON r.resource_code = v.res;

-- Scenarios (TBL-15): status 'draft'; results are computed by the application.
-- expected_finish_date holds the hand-computed value (TC-17, TC-18, TC-19).
INSERT INTO scenarios (project_id, baseline_id, as_of_date, scenario_type, title, assumptions,
                       expected_finish_date, status, created_by)
SELECT p.project_id, b.baseline_id, DATE '2026-03-16', v.stype, v.title, v.assumptions, v.expected::date, 'draft', u.user_id
FROM (VALUES
  ('predecessor_delay', 'SC1: تأخر T05 ثلاثة أيام',
   'تأخر المهمة T05 ثلاثة أيام تقويمية على المسار الأطول؛ علاقات FS دون فاصل؛ المهام المكتملة لا تتغير.', '2026-03-27'),
  ('member_absence',    'SC2: غياب member.c أربعة أيام',
   'غياب العضو member.c من 2026-03-18 إلى 2026-03-21؛ يتداخل يومان مع T07 فتطول بيومين.', '2026-03-26'),
  ('resource_outage',   'SC3: تعطل R3 بتوفر 50%',
   'توفر المورد R3 بنسبة 50% من 2026-03-20 إلى 2026-03-23؛ الزيادة = سقف(4 × 0.5) = 2 يوم على كل مهمة مخصص لها R3 وتتداخل مع الفترة.', '2026-03-26')
) AS v(stype, title, assumptions, expected)
JOIN projects p ON p.project_code = 'PRJ-S1'
JOIN baselines b ON b.project_id = p.project_id AND b.version_no = 1
JOIN users u ON u.username = 'pm.s1';

-- Treatment options for SC1 (TBL-16), cost known for O1 only (TC-20) --------
INSERT INTO treatment_options (scenario_id, option_label, description, cost_estimate, cost_source, quality_note, created_by)
SELECT s.scenario_id, v.label, v.descr, v.cost, v.cost_source, NULL, u.user_id
FROM (VALUES
  ('O1', 'إضافة عضو مساعد في T07 لتقليص مدتها يومين', 1500.00, 'تقدير اصطناعي لأغراض الاختبار'),
  ('O2', 'تقليص نطاق T08 يومًا واحدًا',                NULL,    NULL),
  ('O3', 'عمل إضافي في T05 لتقليص مدتها يومًا واحدًا', NULL,    NULL)
) AS v(label, descr, cost, cost_source)
JOIN scenarios s ON s.title LIKE 'SC1:%'
JOIN projects p ON p.project_id = s.project_id AND p.project_code = 'PRJ-S1'
JOIN users u ON u.username = 'pm.s1';

-- Scenario changes (TBL-17): disruptions (option_id NULL) and option changes --
INSERT INTO scenario_changes (scenario_id, option_id, change_kind, target_task_id, change_amount_days)
SELECT s.scenario_id, o.option_id, v.kind, t.task_id, v.amount
FROM (VALUES
  (NULL, 'delay_task',      'T05',  3.0),
  ('O1', 'change_duration', 'T07', -2.0),
  ('O2', 'change_duration', 'T08', -1.0),
  ('O3', 'change_duration', 'T05', -1.0)
) AS v(opt, kind, code, amount)
JOIN scenarios s ON s.title LIKE 'SC1:%'
JOIN projects p ON p.project_id = s.project_id AND p.project_code = 'PRJ-S1'
JOIN tasks t ON t.project_id = p.project_id AND t.task_code = v.code
LEFT JOIN treatment_options o ON o.scenario_id = s.scenario_id AND o.option_label = v.opt;

INSERT INTO scenario_changes (scenario_id, change_kind, target_user_id, period_start, period_end)
SELECT s.scenario_id, 'absence_member', u.user_id, DATE '2026-03-18', DATE '2026-03-21'
FROM scenarios s
JOIN projects p ON p.project_id = s.project_id AND p.project_code = 'PRJ-S1'
JOIN users u ON u.username = 'member.c'
WHERE s.title LIKE 'SC2:%';

INSERT INTO scenario_changes (scenario_id, change_kind, target_resource_id, availability_pct, period_start, period_end)
SELECT s.scenario_id, 'outage_resource', r.resource_id, 50, DATE '2026-03-20', DATE '2026-03-23'
FROM scenarios s
JOIN projects p ON p.project_id = s.project_id AND p.project_code = 'PRJ-S1'
JOIN resources r ON r.resource_code = 'R3'
WHERE s.title LIKE 'SC3:%';

COMMIT;
