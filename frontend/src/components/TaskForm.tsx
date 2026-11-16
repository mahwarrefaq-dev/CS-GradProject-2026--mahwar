import { useState, type FormEvent } from "react";
import { ApiError, apiPatch, apiPost } from "../api";
import { PRIORITY_AR, type Priority, type Project, type Task } from "../types";
import Field from "./Field";

interface TaskFormProps {
  project: Project;
  task?: Task; // edit when given, create otherwise
  onSaved: (task: Task) => void;
  onCancel: () => void;
}

/** Create (POST) or edit (PATCH) a task – API-04, FR-02, NFR-04. */
export default function TaskForm({ project, task, onSaved, onCancel }: TaskFormProps) {
  const editing = task !== undefined;
  const [form, setForm] = useState({
    task_code: task?.task_code ?? "",
    task_name: task?.task_name ?? "",
    priority: (task?.priority ?? "medium") as Priority,
    assignee_user_id: task?.assignee?.user_id?.toString() ?? "",
    planned_start_date: task?.planned_start_date ?? "",
    planned_due_date: task?.planned_due_date ?? "",
  });
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  const set = (key: keyof typeof form) => (value: string) => setForm((f) => ({ ...f, [key]: value }));
  const err = (field: string) => error?.fieldMessage(field);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const body = {
      task_code: form.task_code.trim(),
      task_name: form.task_name.trim(),
      priority: form.priority,
      assignee_user_id: form.assignee_user_id === "" ? null : Number(form.assignee_user_id),
      planned_start_date: form.planned_start_date,
      planned_due_date: form.planned_due_date,
    };
    const base = `/projects/${project.project_id}/tasks`;
    try {
      const saved = editing
        ? await apiPatch<Task>(`${base}/${task.task_id}`, body)
        : await apiPost<Task>(base, body);
      onSaved(saved);
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, "UNKNOWN", "حدث خطأ غير متوقع"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form-card" onSubmit={submit} noValidate>
      <h2>{editing ? `تعديل المهمة ${task.task_code}` : "إضافة مهمة"}</h2>
      {error && error.fields.length === 0 && (
        <p className="alert" role="alert">
          {error.message}
        </p>
      )}
      <div className="grid">
        <Field id="task_code" label="رمز المهمة" error={err("task_code")} hint="معرف مستعار مثل T-001">
          <input
            id="task_code"
            dir="ltr"
            value={form.task_code}
            onChange={(e) => set("task_code")(e.target.value)}
            maxLength={20}
          />
        </Field>
        <Field id="task_name" label="المهمة" error={err("task_name")}>
          <input
            id="task_name"
            value={form.task_name}
            onChange={(e) => set("task_name")(e.target.value)}
            maxLength={200}
          />
        </Field>
        <Field id="assignee_user_id" label="المسند إليه" error={err("assignee_user_id")}>
          <select
            id="assignee_user_id"
            value={form.assignee_user_id}
            onChange={(e) => set("assignee_user_id")(e.target.value)}
          >
            <option value="">— غير مسندة —</option>
            {project.members.map((m) => (
              <option key={m.user_id} value={m.user_id}>
                {m.username} ({m.display_alias})
              </option>
            ))}
          </select>
        </Field>
        <Field id="priority" label="الأولوية" error={err("priority")}>
          <select id="priority" value={form.priority} onChange={(e) => set("priority")(e.target.value)}>
            {Object.entries(PRIORITY_AR).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field id="planned_start_date" label="البدء" error={err("planned_start_date")}>
          <input
            id="planned_start_date"
            type="date"
            value={form.planned_start_date}
            onChange={(e) => set("planned_start_date")(e.target.value)}
          />
        </Field>
        <Field id="planned_due_date" label="الاستحقاق" error={err("planned_due_date")}>
          <input
            id="planned_due_date"
            type="date"
            value={form.planned_due_date}
            onChange={(e) => set("planned_due_date")(e.target.value)}
          />
        </Field>
      </div>
      <div className="actions">
        <button type="submit" className="btn btn-primary" disabled={busy}>
          {busy ? "جارٍ الحفظ…" : "حفظ"}
        </button>
        <button type="button" className="btn" onClick={onCancel} disabled={busy}>
          إلغاء
        </button>
      </div>
    </form>
  );
}
