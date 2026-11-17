-- Schema_Script.sql - Mehwar database (Chapter 4 simplified design, draft not yet approved)
-- Generated from the design data dictionary; PostgreSQL 15+
BEGIN;

-- TBL-01 roles (FR-01, NFR-02)
CREATE TABLE roles (
    role_id SMALLINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    role_code VARCHAR(30) NOT NULL UNIQUE CHECK (role_code IN ('PROJECT_MANAGER','TEAM_MEMBER','SYSTEM_ADMIN','PLANNER')),
    role_name_ar VARCHAR(60) NOT NULL,
    description VARCHAR(255)
);

-- TBL-02 users (FR-01, NFR-01, NFR-02)
CREATE TABLE users (
    user_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE CHECK (username ~ '^[a-z0-9._-]{3,50}$'),
    display_alias VARCHAR(60) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role_id SMALLINT NOT NULL REFERENCES roles(role_id) ON DELETE RESTRICT,
    is_active BOOLEAN NOT NULL DEFAULT true,
    failed_login_count SMALLINT NOT NULL DEFAULT 0 CHECK (failed_login_count >= 0),
    locked_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ
);

-- TBL-03 projects (FR-02, NFR-01)
CREATE TABLE projects (
    project_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_code VARCHAR(20) NOT NULL UNIQUE,
    project_name VARCHAR(150) NOT NULL,
    project_type VARCHAR(50),
    manager_user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    planned_start_date DATE NOT NULL,
    planned_end_date DATE NOT NULL CHECK (planned_end_date >= planned_start_date),
    team_size SMALLINT CHECK (team_size > 0),
    status VARCHAR(20) NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','active','on_hold','closed')),
    data_mode VARCHAR(10) NOT NULL DEFAULT 'synthetic' CHECK (data_mode IN ('synthetic','real')),
    consent_ref VARCHAR(255),
    consent_date DATE CHECK (data_mode = 'synthetic' OR (consent_ref IS NOT NULL AND consent_date IS NOT NULL)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- TBL-04 project_members (FR-01, FR-03, NFR-02)
CREATE TABLE project_members (
    project_id BIGINT REFERENCES projects(project_id) ON DELETE RESTRICT,
    user_id BIGINT REFERENCES users(user_id) ON DELETE RESTRICT,
    joined_at DATE NOT NULL DEFAULT current_date,
    PRIMARY KEY (project_id, user_id)
);

-- TBL-05 baselines (FR-02, FR-03)
CREATE TABLE baselines (
    baseline_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
    version_no SMALLINT NOT NULL,
    created_by BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    note VARCHAR(255),
    UNIQUE (project_id, version_no)
);

-- TBL-06 tasks (FR-02, FR-06)
CREATE TABLE tasks (
    task_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
    task_code VARCHAR(20) NOT NULL,
    task_name VARCHAR(200) NOT NULL,
    priority VARCHAR(10) NOT NULL DEFAULT 'medium' CHECK (priority IN ('high','medium','low')),
    assignee_user_id BIGINT REFERENCES users(user_id) ON DELETE RESTRICT,
    planned_start_date DATE NOT NULL,
    planned_due_date DATE NOT NULL CHECK (planned_due_date >= planned_start_date),
    planned_duration_days INTEGER GENERATED ALWAYS AS (planned_due_date - planned_start_date + 1) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, task_code)
);

-- TBL-07 baseline_tasks (FR-02, FR-10)
CREATE TABLE baseline_tasks (
    baseline_id BIGINT REFERENCES baselines(baseline_id) ON DELETE CASCADE,
    task_id BIGINT REFERENCES tasks(task_id) ON DELETE CASCADE,
    planned_start_date DATE NOT NULL,
    planned_due_date DATE NOT NULL CHECK (planned_due_date >= planned_start_date),
    priority VARCHAR(10) NOT NULL CHECK (priority IN ('high','medium','low')),
    PRIMARY KEY (baseline_id, task_id)
);

-- TBL-08 task_snapshots (FR-03, FR-06, FR-07, NFR-04)
CREATE TABLE task_snapshots (
    snapshot_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES tasks(task_id) ON DELETE RESTRICT,
    baseline_id BIGINT NOT NULL REFERENCES baselines(baseline_id) ON DELETE RESTRICT,
    snapshot_date DATE NOT NULL CHECK (snapshot_date <= (snapshot_timestamp AT TIME ZONE 'UTC')::date + 1),
    snapshot_timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    update_source VARCHAR(20) NOT NULL CHECK (update_source IN ('manual','import','system')),
    progress_pct NUMERIC(5,2) NOT NULL CHECK (progress_pct BETWEEN 0 AND 100),
    status_at_snapshot VARCHAR(20) NOT NULL CHECK (status_at_snapshot IN ('not_started','in_progress','blocked','completed','cancelled') AND (status_at_snapshot <> 'completed' OR progress_pct = 100)),
    remaining_estimate_days NUMERIC(6,1) CHECK (remaining_estimate_days >= 0),
    blocker_note VARCHAR(500),
    recorded_by BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT
);

-- TBL-09 task_outcomes (D-02, NFR-07)
CREATE TABLE task_outcomes (
    task_id BIGINT REFERENCES tasks(task_id) ON DELETE RESTRICT,
    actual_start_date DATE,
    actual_end_date DATE CHECK (actual_end_date >= actual_start_date),
    final_status VARCHAR(20) NOT NULL CHECK (final_status IN ('completed','cancelled')),
    recorded_by BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (task_id)
);

-- TBL-10 project_outcomes (D-02)
CREATE TABLE project_outcomes (
    project_id BIGINT REFERENCES projects(project_id) ON DELETE RESTRICT,
    actual_end_date DATE,
    status_final VARCHAR(20) NOT NULL CHECK (status_final IN ('completed','cancelled','suspended')),
    recorded_by BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (project_id)
);

-- TBL-11 dependencies (FR-04, FR-08)
CREATE TABLE dependencies (
    dependency_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    predecessor_task_id BIGINT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    successor_task_id BIGINT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE CHECK (successor_task_id <> predecessor_task_id),
    dependency_type CHAR(2) NOT NULL DEFAULT 'FS' CHECK (dependency_type = 'FS'),
    lag_days SMALLINT NOT NULL DEFAULT 0,
    created_by BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- TBL-12 resources (FR-05, NFR-01)
CREATE TABLE resources (
    resource_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    resource_code VARCHAR(20) NOT NULL UNIQUE,
    resource_type VARCHAR(20) NOT NULL CHECK (resource_type IN ('human','equipment','facility','other')),
    linked_user_id BIGINT UNIQUE REFERENCES users(user_id) ON DELETE RESTRICT,
    default_capacity_hours NUMERIC(5,2) NOT NULL CHECK (default_capacity_hours > 0 AND default_capacity_hours <= 24),
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- TBL-13 resource_snapshots (FR-05, FR-06, FR-07)
CREATE TABLE resource_snapshots (
    resource_snapshot_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    resource_id BIGINT NOT NULL REFERENCES resources(resource_id) ON DELETE RESTRICT,
    snapshot_date DATE NOT NULL,
    capacity_hours NUMERIC(6,2) NOT NULL CHECK (capacity_hours >= 0),
    availability_pct NUMERIC(5,2) NOT NULL CHECK (availability_pct BETWEEN 0 AND 100),
    note VARCHAR(255),
    recorded_by BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (resource_id, snapshot_date)
);

-- TBL-14 task_allocations (FR-05, FR-07, FR-09)
CREATE TABLE task_allocations (
    allocation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id BIGINT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
    resource_id BIGINT NOT NULL REFERENCES resources(resource_id) ON DELETE RESTRICT,
    allocated_hours NUMERIC(7,2) NOT NULL CHECK (allocated_hours > 0),
    UNIQUE (task_id, resource_id)
);

-- TBL-15 scenarios (FR-09, FR-10, T-01)
CREATE TABLE scenarios (
    scenario_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(project_id) ON DELETE RESTRICT,
    baseline_id BIGINT NOT NULL REFERENCES baselines(baseline_id) ON DELETE RESTRICT,
    as_of_date DATE NOT NULL,
    scenario_type VARCHAR(30) NOT NULL CHECK (scenario_type IN ('member_absence','resource_outage','predecessor_delay')),
    title VARCHAR(150) NOT NULL,
    assumptions TEXT NOT NULL,
    expected_finish_date DATE,
    status VARCHAR(20) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','computed','stale','failed','archived')),
    created_by BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- TBL-16 treatment_options (FR-10)
CREATE TABLE treatment_options (
    option_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario_id BIGINT NOT NULL REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
    option_label VARCHAR(100) NOT NULL,
    description VARCHAR(500),
    cost_estimate NUMERIC(12,2) CHECK (cost_estimate >= 0),
    cost_source VARCHAR(255),
    quality_note VARCHAR(255),
    created_by BIGINT NOT NULL REFERENCES users(user_id) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- TBL-17 scenario_changes (FR-09, FR-10)
CREATE TABLE scenario_changes (
    change_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario_id BIGINT NOT NULL REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
    option_id BIGINT REFERENCES treatment_options(option_id) ON DELETE CASCADE,
    change_kind VARCHAR(30) NOT NULL CHECK (change_kind IN ('delay_task','absence_member','outage_resource','reassign_task','change_duration','shift_start')),
    target_task_id BIGINT REFERENCES tasks(task_id) ON DELETE RESTRICT,
    target_user_id BIGINT REFERENCES users(user_id) ON DELETE RESTRICT,
    target_resource_id BIGINT REFERENCES resources(resource_id) ON DELETE RESTRICT,
    replacement_resource_id BIGINT REFERENCES resources(resource_id) ON DELETE RESTRICT,
    change_amount_days NUMERIC(6,1),
    availability_pct NUMERIC(5,2) CHECK (availability_pct BETWEEN 0 AND 100),
    period_start DATE,
    period_end DATE CHECK (period_end >= period_start)
);

-- TBL-18 scenario_results (FR-09, FR-10)
CREATE TABLE scenario_results (
    result_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    scenario_id BIGINT NOT NULL REFERENCES scenarios(scenario_id) ON DELETE CASCADE,
    option_id BIGINT REFERENCES treatment_options(option_id) ON DELETE CASCADE,
    computed_finish_date DATE NOT NULL,
    finish_delta_days INTEGER NOT NULL,
    affected_task_count INTEGER NOT NULL CHECK (affected_task_count >= 0),
    required_resource_hours NUMERIC(9,2),
    computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE NULLS NOT DISTINCT (scenario_id, option_id)
);

-- TBL-19 rule_parameters (FR-07, NFR-03)
CREATE TABLE rule_parameters (
    param_key VARCHAR(40),
    param_value NUMERIC(6,2) NOT NULL,
    unit VARCHAR(20) NOT NULL,
    approval_status VARCHAR(10) NOT NULL DEFAULT 'draft' CHECK (approval_status IN ('draft','approved')),
    updated_by BIGINT REFERENCES users(user_id) ON DELETE RESTRICT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (param_key)
);

-- TBL-20 audit_log (NFR-02)
CREATE TABLE audit_log (
    audit_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    user_id BIGINT REFERENCES users(user_id) ON DELETE RESTRICT,
    action VARCHAR(30) NOT NULL CHECK (action IN ('create','update','delete','login_success','login_failed','access_denied','role_change','settings_change')),
    entity_type VARCHAR(40),
    entity_id VARCHAR(40),
    old_value JSONB,
    new_value JSONB
);

-- Indexes (see the index table in section 4.5.3)
CREATE INDEX ix_task_snapshots_01 ON task_snapshots (task_id, snapshot_timestamp DESC);
CREATE INDEX ix_tasks_02 ON tasks (project_id);
CREATE INDEX ix_tasks_03 ON tasks (assignee_user_id);
CREATE INDEX ix_dependencies_04 ON dependencies (predecessor_task_id);
CREATE INDEX ix_dependencies_05 ON dependencies (successor_task_id);
CREATE INDEX ix_resource_snapshots_06 ON resource_snapshots (resource_id, snapshot_date DESC);
CREATE INDEX ix_task_allocations_07 ON task_allocations (resource_id);
CREATE INDEX ix_audit_log_08 ON audit_log (occurred_at);

-- Derived views used to export the Dataset template (no stored derived values)
CREATE VIEW v_task_outcomes AS
SELECT o.task_id, o.actual_start_date, o.actual_end_date, o.final_status,
       CASE WHEN o.actual_end_date > t.planned_due_date THEN 1 ELSE 0 END AS delay_flag,
       GREATEST(o.actual_end_date - t.planned_due_date, 0)            AS delay_days
FROM task_outcomes o JOIN tasks t ON t.task_id = o.task_id;

CREATE VIEW v_latest_task_snapshot AS
SELECT DISTINCT ON (s.task_id) s.*
FROM task_snapshots s
ORDER BY s.task_id, s.snapshot_timestamp DESC;

-- Default risk-rule thresholds from Chapter 3 (draft status)
INSERT INTO rule_parameters (param_key, param_value, unit) VALUES
 ('stale_after_days', 7, 'يوم'), ('high_availability_below', 50, '%'),
 ('medium_availability_below', 80, '%'), ('progress_gap_points', 10, 'نقطة مئوية');
INSERT INTO roles (role_code, role_name_ar) VALUES
 ('PROJECT_MANAGER','مدير المشروع'), ('TEAM_MEMBER','عضو الفريق'),
 ('SYSTEM_ADMIN','مسؤول النظام'), ('PLANNER','مسؤول التخطيط أو الموارد');

-- Snapshots are append-only for the application account (ARC-03, SEC-08)
-- REVOKE UPDATE, DELETE ON task_snapshots FROM mehwar_app;
COMMIT;