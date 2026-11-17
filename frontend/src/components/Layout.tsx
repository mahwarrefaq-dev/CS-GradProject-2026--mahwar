import { useState, type ReactNode } from "react";
import type { CurrentUser, RoleCode } from "../api";
import type { Project } from "../types";
import { ConnectionIndicator } from "./EnvStatus";
import Icon, { type IconName } from "./Icon";
import Logo from "./Logo";

export type ScreenName = "projects" | "plan" | "mytasks" | "resources";

interface NavEntry {
  screen?: ScreenName; // undefined = not implemented yet
  label: string;
  icon: IconName;
  roles?: RoleCode[]; // undefined = every role
  later?: string; // shown on disabled items
}

// Navigation by role (SEC-02). Items of later releases stay visible but disabled.
const NAV: NavEntry[] = [
  { screen: "projects", label: "المشروعات وخططها", icon: "folder" },
  { screen: "mytasks", label: "مهامي وتحديث التقدم", icon: "list-checks" },
  { screen: "resources", label: "الموارد والتوفر", icon: "cpu", roles: ["PROJECT_MANAGER", "PLANNER"] },
];
const LATER: NavEntry[] = [
  { label: "لوحة المتابعة", icon: "dashboard", later: "الإصدار 3" },
  { label: "الإنذارات والمهام المتأثرة", icon: "alert-triangle", later: "الإصدار 4" },
  { label: "السيناريوهات والمقارنة", icon: "sliders", later: "الإصدار 5" },
  { label: "الملخص", icon: "file-text", later: "الإصدار 5" },
  { label: "المستخدمون والإعدادات", icon: "shield-check", roles: ["SYSTEM_ADMIN"], later: "لاحقًا" },
];

const ROLE_TEXT: Record<RoleCode, string> = {
  PROJECT_MANAGER: "صلاحيات مدير المشروع: إنشاء المشروعات وإدارة مهامها وخط الأساس والاعتماديات وتخصيص الموارد.",
  TEAM_MEMBER: "صلاحيات عضو الفريق: عرض مشروعاتك وتسجيل تقدم المهام المسندة إليك.",
  PLANNER: "صلاحيات مسؤول التخطيط: إدارة الموارد وتوفرها، والاعتماديات وتخصيص الموارد في المشروعات التي أنت عضو فيها.",
  SYSTEM_ADMIN: "صلاحيات مسؤول النظام: إدارة المستخدمين والأدوار.",
};

interface LayoutProps {
  user: CurrentUser;
  screen: ScreenName;
  available: ScreenName[]; // screens implemented so far
  projects: Project[];
  activeProjectId: number | null;
  onSelectProject: (projectId: number) => void;
  onNavigate: (screen: ScreenName) => void;
  onLogout: () => void;
  children: ReactNode;
}

/** Application frame from the student's design: dark sidebar, top bar with the active project. */
export default function Layout(props: LayoutProps) {
  const { user, screen, available, projects, activeProjectId, onSelectProject, onNavigate, onLogout, children } = props;
  const [navOpen, setNavOpen] = useState(false);
  const allowed = (e: NavEntry) => !e.roles || e.roles.includes(user.role_code);
  const activeScreen: ScreenName = screen === "plan" ? "projects" : screen;

  function go(target: ScreenName) {
    setNavOpen(false);
    onNavigate(target);
  }

  return (
    <div className={navOpen ? "shell nav-open" : "shell"}>
      <aside className="sidebar" aria-label="القائمة الرئيسة">
        <div>
          <div className="sidebar-brand">
            <div className="logo-tile">
              <Logo size={38} />
            </div>
            <div style={{ flex: 1 }}>
              <div className="brand-name">
                <strong>مِحور</strong>
                <span>MAHWAR</span>
              </div>
              <p className="brand-sub">متابعة المشروعات ودعم القرار</p>
            </div>
            <button type="button" className="icon-btn sidebar-close" onClick={() => setNavOpen(false)} aria-label="إغلاق القائمة">
              <Icon name="x" />
            </button>
          </div>

          <div className="user-card">
            <div className="avatar" aria-hidden="true">
              {user.display_alias.trim().charAt(0) || "؟"}
            </div>
            <div>
              <div className="name">{user.display_alias}</div>
              <span className="role-pill">{user.role_name_ar}</span>
            </div>
          </div>

          <nav className="nav">
            {NAV.filter(allowed).map((e) => {
              const ready = e.screen !== undefined && available.includes(e.screen);
              return (
                <button
                  key={e.label}
                  type="button"
                  className={e.screen === activeScreen ? "nav-item active" : "nav-item"}
                  onClick={() => e.screen && go(e.screen)}
                  disabled={!ready}
                  aria-current={e.screen === activeScreen ? "page" : undefined}
                >
                  <span>
                    <Icon name={e.icon} size={20} />
                    {e.label}
                  </span>
                  {!ready && <span className="nav-tag">قريبًا</span>}
                </button>
              );
            })}
            <div className="nav-section">إصدارات لاحقة</div>
            {LATER.filter(allowed).map((e) => (
              <button key={e.label} type="button" className="nav-item" disabled title={`يُضاف في ${e.later}`}>
                <span>
                  <Icon name={e.icon} size={20} />
                  {e.label}
                </span>
                <span className="nav-tag">{e.later}</span>
              </button>
            ))}
          </nav>
        </div>

        <div className="sidebar-foot">
          <button type="button" className="logout-btn" onClick={onLogout}>
            <Icon name="log-out" size={16} />
            تسجيل الخروج / تبديل الحساب
          </button>
        </div>
      </aside>
      <div className="scrim" onClick={() => setNavOpen(false)} />

      <div className="main">
        <header className="topbar">
          <div className="topbar-row">
            <div className="topbar-title">
              <button type="button" className="icon-btn menu-toggle" onClick={() => setNavOpen(true)} aria-label="فتح القائمة">
                <Icon name="menu" size={20} />
              </button>
              <div>
                <div className="project-picker">
                  <span className="badge badge-blue">المشروع النشط</span>
                  <label htmlFor="project-picker" className="visually-hidden">
                    المشروع النشط
                  </label>
                  <select
                    id="project-picker"
                    value={activeProjectId ?? ""}
                    onChange={(e) => e.target.value && onSelectProject(Number(e.target.value))}
                    disabled={projects.length === 0}
                  >
                    <option value="">{projects.length ? "— اختر مشروعًا —" : "لا توجد مشروعات"}</option>
                    {projects.map((p) => (
                      <option key={p.project_id} value={p.project_id}>
                        {p.project_code} — {p.project_name}
                      </option>
                    ))}
                  </select>
                </div>
                <p className="topbar-sub">مِحور MAHWAR • تطبيق الويب</p>
              </div>
            </div>
            <div className="user-chip">
              <span className="dot" />
              {user.display_alias} ({user.role_name_ar})
              <button type="button" className="icon-btn" onClick={onLogout} title="تسجيل الخروج" aria-label="تسجيل الخروج">
                <Icon name="log-out" size={16} />
              </button>
            </div>
          </div>
          <div className="role-banner">
            <span>
              <Icon name="shield-check" size={16} />
              {ROLE_TEXT[user.role_code]}
            </span>
            <ConnectionIndicator />
          </div>
        </header>

        <main className="content">{children}</main>
      </div>
    </div>
  );
}
