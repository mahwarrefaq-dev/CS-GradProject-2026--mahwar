import { useState, type FormEvent } from "react";
import { ApiError, apiPatch, apiPost } from "../api";
import { DATA_MODE_AR, STATUS_AR, type DataMode, type Project, type ProjectStatus } from "../types";
import Field from "./Field";

interface ProjectFormProps {
  project?: Project; // edit when given, create otherwise
  onSaved: (project: Project) => void;
  onCancel: () => void;
}

function splitUsernames(text: string): string[] {
  return text
    .split(/[\s,،]+/)
    .map((s) => s.trim())
    .filter(Boolean);
}

/** Create (POST) or edit (PATCH) a project – API-03, FR-02, NFR-01. */
export default function ProjectForm({ project, onSaved, onCancel }: ProjectFormProps) {
  const editing = project !== undefined;
  const [form, setForm] = useState({
    project_code: project?.project_code ?? "",
    project_name: project?.project_name ?? "",
    project_type: project?.project_type ?? "",
    planned_start_date: project?.planned_start_date ?? "",
    planned_end_date: project?.planned_end_date ?? "",
    team_size: project?.team_size?.toString() ?? "",
    status: (project?.status ?? "planned") as ProjectStatus,
    data_mode: (project?.data_mode ?? "synthetic") as DataMode,
    consent_ref: project?.consent_ref ?? "",
    consent_date: project?.consent_date ?? "",
    members: (project?.members ?? [])
      .filter((m) => m.user_id !== project?.manager.user_id)
      .map((m) => m.username)
      .join("، "),
  });
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  const set = (key: keyof typeof form) => (value: string) => setForm((f) => ({ ...f, [key]: value }));
  const err = (field: string) => error?.fieldMessage(field);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const body: Record<string, unknown> = {
      project_name: form.project_name.trim(),
      project_type: form.project_type.trim() || null,
      planned_start_date: form.planned_start_date,
      planned_end_date: form.planned_end_date,
      team_size: form.team_size === "" ? null : Number(form.team_size),
      status: form.status,
      data_mode: form.data_mode,
      consent_ref: form.consent_ref.trim() || null,
      consent_date: form.consent_date || null,
      member_usernames: splitUsernames(form.members),
    };
    try {
      const saved = editing
        ? await apiPatch<Project>(`/projects/${project.project_id}`, body)
        : await apiPost<Project>("/projects", { ...body, project_code: form.project_code.trim() });
      onSaved(saved);
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, "UNKNOWN", "حدث خطأ غير متوقع"));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card form-card" onSubmit={submit} noValidate>
      <h2>{editing ? "تعديل بيانات المشروع" : "مشروع جديد"}</h2>
      {error && error.fields.length === 0 && (
        <p className="alert" role="alert">
          {error.message}
        </p>
      )}
      <div className="grid">
        <Field id="project_code" label="رمز المشروع" error={err("project_code")} hint="معرف مستعار مثل PRJ-001">
          <input
            id="project_code"
            dir="ltr"
            value={form.project_code}
            onChange={(e) => set("project_code")(e.target.value)}
            disabled={editing}
            maxLength={20}
          />
        </Field>
        <Field id="project_name" label="اسم المشروع" error={err("project_name")}>
          <input
            id="project_name"
            value={form.project_name}
            onChange={(e) => set("project_name")(e.target.value)}
            maxLength={150}
          />
        </Field>
        <Field id="project_type" label="نوع المشروع (اختياري)" error={err("project_type")}>
          <input
            id="project_type"
            value={form.project_type}
            onChange={(e) => set("project_type")(e.target.value)}
            maxLength={50}
          />
        </Field>
        <Field id="team_size" label="حجم الفريق (اختياري)" error={err("team_size")}>
          <input
            id="team_size"
            type="number"
            min={1}
            value={form.team_size}
            onChange={(e) => set("team_size")(e.target.value)}
          />
        </Field>
        <Field id="planned_start_date" label="البدء المخطط" error={err("planned_start_date")}>
          <input
            id="planned_start_date"
            type="date"
            value={form.planned_start_date}
            onChange={(e) => set("planned_start_date")(e.target.value)}
          />
        </Field>
        <Field id="planned_end_date" label="الانتهاء المخطط" error={err("planned_end_date")}>
          <input
            id="planned_end_date"
            type="date"
            value={form.planned_end_date}
            onChange={(e) => set("planned_end_date")(e.target.value)}
          />
        </Field>
        <Field id="status" label="الحالة" error={err("status")}>
          <select id="status" value={form.status} onChange={(e) => set("status")(e.target.value)}>
            {Object.entries(STATUS_AR).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field id="data_mode" label="نوع البيانات" error={err("data_mode")}>
          <select id="data_mode" value={form.data_mode} onChange={(e) => set("data_mode")(e.target.value)}>
            {Object.entries(DATA_MODE_AR).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        {form.data_mode === "real" && (
          <>
            <Field id="consent_ref" label="مرجع موافقة مالك البيانات" error={err("consent_ref")}>
              <input
                id="consent_ref"
                value={form.consent_ref}
                onChange={(e) => set("consent_ref")(e.target.value)}
                maxLength={255}
              />
            </Field>
            <Field id="consent_date" label="تاريخ الموافقة" error={err("consent_date")}>
              <input
                id="consent_date"
                type="date"
                value={form.consent_date}
                onChange={(e) => set("consent_date")(e.target.value)}
              />
            </Field>
          </>
        )}
      </div>
      <Field
        id="members"
        label="أعضاء المشروع (أسماء المستخدمين)"
        error={err("member_usernames")}
        hint="افصل بين الأسماء بفاصلة أو مسافة، مثل: member.a، member.b. مدير المشروع عضو تلقائيًا."
      >
        <input id="members" dir="ltr" value={form.members} onChange={(e) => set("members")(e.target.value)} />
      </Field>
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
