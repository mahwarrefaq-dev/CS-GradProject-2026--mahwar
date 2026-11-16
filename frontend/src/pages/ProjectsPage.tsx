import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet, type CurrentUser } from "../api";
import ProjectForm from "../components/ProjectForm";
import { DATA_MODE_AR, STATUS_AR, type Project } from "../types";

interface ProjectsPageProps {
  user: CurrentUser;
  onOpen: (projectId: number) => void;
}

/** SCR-02 – project list (UC-01, FR-02, API-03). */
export default function ProjectsPage({ user, onOpen }: ProjectsPageProps) {
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const load = useCallback(() => {
    setError(null);
    apiGet<Project[]>("/projects")
      .then(setProjects)
      .catch((e) => setError(e instanceof ApiError ? e.message : "تعذر تحميل المشروعات"));
  }, []);

  useEffect(load, [load]);

  const canCreate = user.role_code === "PROJECT_MANAGER";

  return (
    <section>
      <div className="section-head">
        <h2>المشروعات</h2>
        {canCreate && !creating && (
          <button type="button" className="btn btn-primary" onClick={() => setCreating(true)}>
            مشروع جديد
          </button>
        )}
      </div>

      {creating && (
        <ProjectForm
          onCancel={() => setCreating(false)}
          onSaved={(p) => {
            setCreating(false);
            onOpen(p.project_id);
          }}
        />
      )}

      {error && (
        <p className="alert" role="alert">
          {error}{" "}
          <button type="button" className="btn btn-link" onClick={load}>
            إعادة المحاولة
          </button>
        </p>
      )}

      {projects === null && !error && <p className="muted">جارٍ التحميل…</p>}

      {projects !== null && projects.length === 0 && (
        <p className="empty">لا توجد مشروعات أنت مديرها أو عضو فيها.</p>
      )}

      {projects !== null && projects.length > 0 && (
        <table className="tb data">
          <thead>
            <tr>
              <th>الرمز</th>
              <th>اسم المشروع</th>
              <th>البدء المخطط</th>
              <th>الانتهاء المخطط</th>
              <th>الحالة</th>
              <th>نوع البيانات</th>
              <th>المهام</th>
            </tr>
          </thead>
          <tbody>
            {projects.map((p) => (
              <tr key={p.project_id}>
                <td className="code">
                  <button type="button" className="btn btn-link" onClick={() => onOpen(p.project_id)}>
                    {p.project_code}
                  </button>
                </td>
                <td>{p.project_name}</td>
                <td className="date">{p.planned_start_date}</td>
                <td className="date">{p.planned_end_date}</td>
                <td>{STATUS_AR[p.status]}</td>
                <td>{DATA_MODE_AR[p.data_mode]}</td>
                <td>{p.task_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
