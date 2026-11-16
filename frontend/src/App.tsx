import { useEffect, useState } from "react";
import { clearSession, getSession, setUnauthorizedHandler, type CurrentUser } from "./api";
import Layout from "./components/Layout";
import LoginPage from "./pages/LoginPage";
import PlanPage from "./pages/PlanPage";
import ProjectsPage from "./pages/ProjectsPage";

// Simple screen state instead of a routing library (project technology list).
type Screen = { name: "projects" } | { name: "plan"; projectId: number };

const TITLES: Record<Screen["name"], string> = {
  projects: "قائمة المشروعات",
  plan: "خطة المشروع",
};

export default function App() {
  const [user, setUser] = useState<CurrentUser | null>(() => getSession());
  const [screen, setScreen] = useState<Screen>({ name: "projects" });

  function logout() {
    clearSession();
    setUser(null);
    setScreen({ name: "projects" });
  }

  useEffect(() => {
    setUnauthorizedHandler(logout); // expired or invalid token -> back to SCR-01
    return () => setUnauthorizedHandler(null);
  }, []);

  if (user === null) {
    return <LoginPage onLogin={setUser} />;
  }

  return (
    <Layout
      user={user}
      title={TITLES[screen.name]}
      onLogout={logout}
      onProjects={() => setScreen({ name: "projects" })}
    >
      {screen.name === "projects" && (
        <ProjectsPage user={user} onOpen={(projectId) => setScreen({ name: "plan", projectId })} />
      )}
      {screen.name === "plan" && (
        <PlanPage projectId={screen.projectId} onBack={() => setScreen({ name: "projects" })} />
      )}
    </Layout>
  );
}
