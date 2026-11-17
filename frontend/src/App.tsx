import { useCallback, useEffect, useState } from "react";
import { ApiError, apiGet, clearSession, getSession, setUnauthorizedHandler, type CurrentUser } from "./api";
import Layout, { type ScreenName } from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import PlanPage from "./pages/PlanPage";
import ProjectsPage from "./pages/ProjectsPage";
import type { Project } from "./types";

// Simple screen state instead of a routing library (project technology list).
const AVAILABLE: ScreenName[] = ["projects", "plan"];

export default function App() {
  const [user, setUser] = useState<CurrentUser | null>(() => getSession());
  const [screen, setScreen] = useState<ScreenName>("projects");
  const [activeProjectId, setActiveProjectId] = useState<number | null>(null);
  const [projects, setProjects] = useState<Project[] | null>(null);
  const [projectsError, setProjectsError] = useState<string | null>(null);

  const logout = useCallback(() => {
    clearSession();
    setUser(null);
    setScreen("projects");
    setActiveProjectId(null);
    setProjects(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout); // expired or invalid token -> back to SCR-01
    return () => setUnauthorizedHandler(null);
  }, [logout]);

  const loadProjects = useCallback(() => {
    setProjectsError(null);
    apiGet<Project[]>("/projects")
      .then(setProjects)
      .catch((e) => setProjectsError(e instanceof ApiError ? e.message : "تعذر تحميل المشروعات"));
  }, []);

  useEffect(() => {
    if (user) loadProjects();
  }, [user, loadProjects]);

  function openProject(projectId: number) {
    setActiveProjectId(projectId);
    setScreen("plan");
  }

  if (user === null) {
    return <LoginPage onLogin={setUser} />;
  }

  return (
    <Layout
      user={user}
      screen={screen}
      available={AVAILABLE}
      projects={projects ?? []}
      activeProjectId={activeProjectId}
      onSelectProject={openProject}
      onNavigate={setScreen}
      onLogout={logout}
    >
      {screen === "projects" && (
        <ProjectsPage
          user={user}
          projects={projects}
          error={projectsError}
          onReload={loadProjects}
          onOpen={openProject}
          onCreated={(p) => {
            loadProjects();
            openProject(p.project_id);
          }}
        />
      )}
      {screen === "plan" && activeProjectId !== null && (
        <PlanPage
          key={activeProjectId}
          projectId={activeProjectId}
          onBack={() => setScreen("projects")}
          onProjectChanged={loadProjects}
        />
      )}
      {screen === "plan" && activeProjectId === null && (
        <p className="empty">اختر مشروعًا من «المشروع النشط» أعلى الصفحة أو من قائمة المشروعات.</p>
      )}
    </Layout>
  );
}
