import type { ReactNode } from "react";
import type { CurrentUser } from "../api";

interface LayoutProps {
  user: CurrentUser;
  title: string;
  onLogout: () => void;
  onProjects: () => void;
  children: ReactNode;
}

// Navigation items of later releases are shown disabled until they are implemented.
const LATER = [
  { label: "الموارد", release: 2 },
  { label: "لوحة المتابعة", release: 3 },
  { label: "السيناريوهات", release: 5 },
  { label: "الملخص", release: 5 },
];

/** Shared frame of SCR-02..SCR-11: top bar, side navigation and content. */
export default function Layout({ user, title, onLogout, onProjects, children }: LayoutProps) {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <img src="/logo.png" alt="" className="logo" />
          <span>محور</span>
        </div>
        <h1 className="screen-title">{title}</h1>
        <div className="who">
          <span title={user.username}>
            {user.display_alias} · {user.role_name_ar}
          </span>
          <button type="button" className="btn btn-link" onClick={onLogout}>
            تسجيل الخروج
          </button>
        </div>
      </header>
      <div className="body">
        <nav className="sidenav" aria-label="القائمة الرئيسة">
          <button type="button" className="nav-item active" onClick={onProjects}>
            المشروعات
          </button>
          {LATER.map((item) => (
            <button
              key={item.label}
              type="button"
              className="nav-item"
              disabled
              title={`يُضاف في الإصدار ${item.release}`}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
