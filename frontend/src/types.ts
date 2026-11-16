// Shapes returned by API-03..API-05 (backend/app/schemas).

export interface UserRef {
  user_id: number;
  username: string;
  display_alias: string;
}

export type ProjectStatus = "planned" | "active" | "on_hold" | "closed";
export type DataMode = "synthetic" | "real";
export type Priority = "high" | "medium" | "low";

export interface Project {
  project_id: number;
  project_code: string;
  project_name: string;
  project_type: string | null;
  planned_start_date: string;
  planned_end_date: string;
  team_size: number | null;
  status: ProjectStatus;
  data_mode: DataMode;
  consent_ref: string | null;
  consent_date: string | null;
  manager: UserRef;
  members: UserRef[];
  task_count: number;
  current_baseline: { baseline_id: number; version_no: number; created_at: string; note: string | null } | null;
  can_edit: boolean;
}

export interface Task {
  task_id: number;
  project_id: number;
  task_code: string;
  task_name: string;
  priority: Priority;
  assignee: UserRef | null;
  planned_start_date: string;
  planned_due_date: string;
  planned_duration_days: number;
  has_snapshots: boolean;
}

export interface Baseline {
  baseline_id: number;
  version_no: number;
  task_count: number;
  created_at: string;
  note: string | null;
}

export const STATUS_AR: Record<ProjectStatus, string> = {
  planned: "مخطط",
  active: "نشط",
  on_hold: "متوقف مؤقتًا",
  closed: "مغلق",
};

export const DATA_MODE_AR: Record<DataMode, string> = {
  synthetic: "اصطناعية",
  real: "فعلية",
};

export const PRIORITY_AR: Record<Priority, string> = {
  high: "عالية",
  medium: "متوسطة",
  low: "منخفضة",
};

/** Formats an ISO timestamp as YYYY-MM-DD (local date). */
export function isoDate(timestamp: string): string {
  const d = new Date(timestamp);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}
