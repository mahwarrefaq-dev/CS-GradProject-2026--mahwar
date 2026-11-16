-- Q1 (FR-06, NFR-05): latest snapshot of every task in a project as of a date
SELECT DISTINCT ON (t.task_id)
       t.task_id, t.task_code, t.planned_due_date,
       s.snapshot_date, s.snapshot_timestamp, s.progress_pct, s.status_at_snapshot
FROM tasks t
LEFT JOIN task_snapshots s
       ON s.task_id = t.task_id AND s.snapshot_date <= :as_of
WHERE t.project_id = :project_id
ORDER BY t.task_id, s.snapshot_timestamp DESC NULLS LAST;

-- Q2 (FR-06): dashboard counters from Q1
WITH latest AS (
  SELECT DISTINCT ON (t.task_id) t.task_id, t.planned_due_date,
         s.snapshot_date, s.snapshot_timestamp, s.status_at_snapshot
  FROM tasks t
  LEFT JOIN task_snapshots s ON s.task_id = t.task_id AND s.snapshot_date <= :as_of
  WHERE t.project_id = :project_id
  ORDER BY t.task_id, s.snapshot_timestamp DESC NULLS LAST)
SELECT COUNT(*)                                                      AS total_tasks,
       COUNT(*) FILTER (WHERE status_at_snapshot = 'completed')      AS done_tasks,
       ROUND(100.0 * COUNT(*) FILTER (WHERE status_at_snapshot = 'completed')
             / NULLIF(COUNT(*), 0), 1)                               AS completion_pct,
       COUNT(*) FILTER (WHERE status_at_snapshot NOT IN ('completed','cancelled')
                          AND snapshot_date > planned_due_date)      AS overdue_tasks,
       MAX(snapshot_timestamp)                                       AS last_update
FROM latest;

-- Q3 (FR-08): all direct and indirect successors of a task (recursive CTE)
WITH RECURSIVE impact(task_id, distance, path) AS (
  SELECT d.successor_task_id, 1, ARRAY[d.predecessor_task_id, d.successor_task_id]
  FROM dependencies d WHERE d.predecessor_task_id = :task_id
  UNION
  SELECT d.successor_task_id, i.distance + 1, i.path || d.successor_task_id
  FROM dependencies d JOIN impact i ON d.predecessor_task_id = i.task_id
  WHERE NOT d.successor_task_id = ANY(i.path))
SELECT task_id, MIN(distance) AS distance FROM impact GROUP BY task_id ORDER BY distance;

-- Q4 (FR-07): lowest availability of the resources allocated to a task up to a date
SELECT MIN(rs.availability_pct) AS min_availability
FROM task_allocations a
JOIN LATERAL (SELECT availability_pct FROM resource_snapshots r
              WHERE r.resource_id = a.resource_id AND r.snapshot_date <= :snapshot_date
              ORDER BY r.snapshot_date DESC LIMIT 1) rs ON TRUE
WHERE a.task_id = :task_id;

-- Q5 (FR-10): comparison table sorted by the user-selected criterion (finish date here)
SELECT COALESCE(o.option_label, 'دون معالجة') AS option_label,
       r.computed_finish_date, r.finish_delta_days, r.affected_task_count,
       r.required_resource_hours, o.cost_estimate
FROM scenario_results r
LEFT JOIN treatment_options o ON o.option_id = r.option_id
WHERE r.scenario_id = :scenario_id
ORDER BY r.computed_finish_date ASC, o.option_id NULLS FIRST;
