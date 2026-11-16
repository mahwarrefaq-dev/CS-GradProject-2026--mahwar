import { useCallback, useEffect, useState } from "react";
import { ApiError, apiDelete, apiGet, apiPost } from "../api";
import ProjectForm from "../components/ProjectForm";
import TaskForm from "../components/TaskForm";
import { DATA_MODE_AR, PRIORITY_AR, STATUS_AR, isoDate, type Baseline, type Project, type Task } from "../types";

interface PlanPageProps {
  projectId: number;
  onBack: () => void;
}

type Editor = { kind: "none" } | { kind: "project" } | { kind: "task"; task?: Task };

/** SCR-03 – project plan: tasks and baseline (UC-01, FR-02, API-03..API-05).
 *  The dependencies part of SCR-03 (FR-04, API-07) is added in Release 2. */
export default function PlanPage({ projectId, onBack }: PlanPageProps) {
  const [project, setProject] = useState<Project | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [editor, setEditor] = useState<Editor>({ kind: "none" });
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [p, t] = await Promise.all([
        apiGet<Project>(`/projects/${projectId}`),
        apiGet<Task[]>(`/projects/${projectId}/tasks`),
      ]);
      setProject(p);
      setTasks(t);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر تحميل خطة المشروع");
    }
  }, [projectId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function saveBaseline() {
    if (!window.confirm("حفظ نسخة جديدة من خط الأساس بمواعيد المهام الحالية؟")) return;
    setBusy(true);
    setNotice(null);
    setError(null);
    try {
      const b = await apiPost<Baseline>(`/projects/${projectId}/baselines`, {});
      setNotice(`حُفظ خط الأساس: النسخة ${b.version_no} (${b.task_count} مهام)`);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر حفظ خط الأساس");
    } finally {
      setBusy(false);
    }
  }

  async function deleteTask(task: Task) {
    if (!window.confirm(`حذف المهمة ${task.task_code}؟`)) return;
    setBusy(true);
    setNotice(null);
    setError(null);
    try {
      await apiDelete(`/projects/${projectId}/tasks/${task.task_id}`);
      setNotice(`حُذفت المهمة ${task.task_code}`);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "تعذر حذف المهمة");
    } finally {
      setBusy(false);
    }
  }

  if (project === null) {
    return error ? (
      <p className="alert" role="alert">
        {error}{" "}
        <button type="button" className="btn btn-link" onClick={onBack}>
          العودة إلى المشروعات
        </button>
      </p>
    ) : (
      <p className="muted">جارٍ التحميل…</p>
    );
  }

  const canEdit = project.can_edit;
  const baseline = project.current_baseline;

  return (
    <section>
      <div className="section-head">
        <h2>
          <span className="code">{project.project_code}</span> {project.project_name}
        </h2>
        <button type="button" className="btn btn-link" onClick={onBack}>
          → المشروعات
        </button>
      </div>

      <div className="summary">
        <div>
          <span className="label">مدير المشروع</span>
          <span dir="ltr">{project.manager.username}</span>
        </div>
        <div>
          <span className="label">خط الأساس الحالي</span>
          <span>{baseline ? `النسخة ${baseline.version_no} — ${isoDate(baseline.created_at)}` : "لم يُحفظ بعد"}</span>
        </div>
        <div>
          <span className="label">الفترة المخططة</span>
          <span className="date">
            {project.planned_start_date} ← {project.planned_end_date}
          </span>
        </div>
        <div>
          <span className="label">الحالة / البيانات</span>
          <span>
            {STATUS_AR[project.status]} · {DATA_MODE_AR[project.data_mode]}
          </span>
        </div>
        <div className="wide">
          <span className="label">الأعضاء</span>
          <span dir="ltr">{project.members.map((m) => m.username).join("، ")}</span>
        </div>
      </div>

      {notice && (
        <p className="notice" role="status">
          {notice}
        </p>
      )}
      {error && (
        <p className="alert" role="alert">
          {error}
        </p>
      )}

      {canEdit && editor.kind === "none" && (
        <div className="actions">
          <button type="button" className="btn btn-primary" onClick={() => setEditor({ kind: "task" })} disabled={busy}>
            إضافة مهمة
          </button>
          <button type="button" className="btn" onClick={saveBaseline} disabled={busy || tasks.length === 0}>
            حفظ خط أساس جديد
          </button>
          <button type="button" className="btn" onClick={() => setEditor({ kind: "project" })} disabled={busy}>
            تعديل بيانات المشروع
          </button>
        </div>
      )}

      {editor.kind === "project" && (
        <ProjectForm
          project={project}
          onCancel={() => setEditor({ kind: "none" })}
          onSaved={(p) => {
            setProject(p);
            setEditor({ kind: "none" });
            setNotice("حُفظت بيانات المشروع");
          }}
        />
      )}

      {editor.kind === "task" && (
        <TaskForm
          project={project}
          task={editor.task}
          onCancel={() => setEditor({ kind: "none" })}
          onSaved={(t) => {
            setEditor({ kind: "none" });
            setNotice(`حُفظت المهمة ${t.task_code}`);
            void load();
          }}
        />
      )}

      {tasks.length === 0 ? (
        <p className="empty">لا توجد مهام في هذا المشروع بعد.</p>
      ) : (
        <table className="tb data">
          <thead>
            <tr>
              <th>الرمز</th>
              <th>المهمة</th>
              <th>المسند إليه</th>
              <th>الأولوية</th>
              <th>البدء</th>
              <th>الاستحقاق</th>
              <th>المدة (يوم)</th>
              {canEdit && <th>إجراءات</th>}
            </tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.task_id}>
                <td className="code">{t.task_code}</td>
                <td>{t.task_name}</td>
                <td dir="ltr">{t.assignee?.username ?? "—"}</td>
                <td>{PRIORITY_AR[t.priority]}</td>
                <td className="date">{t.planned_start_date}</td>
                <td className="date">{t.planned_due_date}</td>
                <td>{t.planned_duration_days}</td>
                {canEdit && (
                  <td className="row-actions">
                    <button
                      type="button"
                      className="btn btn-small"
                      onClick={() => setEditor({ kind: "task", task: t })}
                      disabled={busy || editor.kind !== "none"}
                    >
                      تعديل
                    </button>
                    <button
                      type="button"
                      className="btn btn-small btn-danger"
                      onClick={() => deleteTask(t)}
                      disabled={busy || editor.kind !== "none" || t.has_snapshots}
                      title={t.has_snapshots ? "لا يمكن حذف مهمة لها لقطات تقدم مسجلة" : undefined}
                    >
                      حذف
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
