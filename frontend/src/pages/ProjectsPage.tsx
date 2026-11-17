import { useState } from "react";
import type { CurrentUser } from "../api";
import Icon from "../components/Icon";
import Modal from "../components/Modal";
import ProjectForm from "../components/ProjectForm";
import { DATA_MODE_AR, STATUS_AR, type DataMode, type Project, type ProjectStatus } from "../types";

interface ProjectsPageProps {
  user: CurrentUser;
  projects: Project[] | null; // null while loading
  error: string | null;
  onReload: () => void;
  onOpen: (projectId: number) => void;
  onCreated: (project: Project) => void;
}

export const STATUS_BADGE: Record<ProjectStatus, string> = {
  planned: "badge badge-blue",
  active: "badge badge-green",
  on_hold: "badge badge-amber",
  closed: "badge badge-gray",
};
const MODE_BADGE: Record<DataMode, string> = { synthetic: "badge badge-violet", real: "badge badge-blue" };

/** SCR-02 – project portfolio (UC-01, FR-02, API-03), styled after the student's design.
 *  No health score: the approved design has no weighted scores (FR-07, NFR-07). */
export default function ProjectsPage({ user, projects, error, onReload, onOpen, onCreated }: ProjectsPageProps) {
  const [creating, setCreating] = useState(false);
  const canCreate = user.role_code === "PROJECT_MANAGER";

  return (
    <section className="card">
      <div className="card-head">
        <div>
          <h2>محفظة المشاريع</h2>
          <p>المشروعات التي أنت مديرها أو عضو فيها</p>
        </div>
        {canCreate && (
          <button type="button" className="btn btn-dark" onClick={() => setCreating(true)}>
            <Icon name="plus" size={16} />
            مشروع جديد
          </button>
        )}
      </div>

      {creating && (
        <Modal title="تسجيل مشروع جديد" onClose={() => setCreating(false)}>
          <ProjectForm
            onCancel={() => setCreating(false)}
            onSaved={(p) => {
              setCreating(false);
              onCreated(p);
            }}
          />
        </Modal>
      )}

      {error && (
        <div className="alert" role="alert">
          <Icon name="alert-circle" size={16} />
          <span>{error}</span>
          <button type="button" className="btn btn-link" onClick={onReload}>
            إعادة المحاولة
          </button>
        </div>
      )}

      {projects === null && !error && <p className="muted">جارٍ التحميل…</p>}

      {projects !== null && projects.length === 0 && (
        <p className="empty">
          لا توجد مشروعات أنت مديرها أو عضو فيها.
          {canCreate && " ابدأ بزر «مشروع جديد»."}
        </p>
      )}

      {projects !== null && projects.length > 0 && (
        <div className="table-wrap">
          <table className="tb data">
            <thead>
              <tr>
                <th>الرمز</th>
                <th>اسم المشروع</th>
                <th>مدير المشروع</th>
                <th>الفترة المخططة</th>
                <th>الحالة</th>
                <th>نوع البيانات</th>
                <th>المهام</th>
                <th>الإجراء</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.project_id}>
                  <td className="code">{p.project_code}</td>
                  <td className="strong">{p.project_name}</td>
                  <td dir="ltr" style={{ textAlign: "right" }}>
                    {p.manager.username}
                  </td>
                  <td className="date">
                    {p.planned_start_date} → {p.planned_end_date}
                  </td>
                  <td>
                    <span className={STATUS_BADGE[p.status]}>{STATUS_AR[p.status]}</span>
                  </td>
                  <td>
                    <span className={MODE_BADGE[p.data_mode]}>{DATA_MODE_AR[p.data_mode]}</span>
                  </td>
                  <td>{p.task_count}</td>
                  <td>
                    <button type="button" className="btn btn-small" onClick={() => onOpen(p.project_id)}>
                      فتح الخطة
                      <Icon name="chevron-left" size={14} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
