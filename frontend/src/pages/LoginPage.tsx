import { useState, type FormEvent } from "react";
import { ApiError, apiPost, saveSession, type CurrentUser } from "../api";
import EnvStatus from "../components/EnvStatus";
import Field from "../components/Field";

interface LoginResponse {
  access_token: string;
  user: CurrentUser;
}

/** SCR-01 – login (FR-01, API-01). */
export default function LoginPage({ onLogin }: { onLogin: (user: CurrentUser) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await apiPost<LoginResponse>("/auth/login", {
        username: username.trim(),
        password,
      });
      saveSession(result.access_token, result.user);
      onLogin(result.user);
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, "UNKNOWN", "حدث خطأ غير متوقع"));
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login-page">
      <header className="topbar">
        <div className="brand">
          <img src="/logo.png" alt="" className="logo" />
          <span>محور</span>
        </div>
        <h1 className="screen-title">تسجيل الدخول</h1>
        <div />
      </header>

      <form className="card login-card" onSubmit={submit} noValidate>
        <h2>تسجيل الدخول إلى محور</h2>
        <Field id="username" label="اسم المستخدم" error={error?.fieldMessage("username")}>
          <input
            id="username"
            autoComplete="username"
            dir="ltr"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            autoFocus
          />
        </Field>
        <Field
          id="password"
          label="كلمة المرور"
          error={error?.fieldMessage("password") ?? (error && error.fields.length === 0 ? error.message : undefined)}
        >
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            dir="ltr"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </Field>
        <div className="actions">
          <button type="submit" className="btn btn-primary" disabled={busy || !username || !password}>
            {busy ? "جارٍ الدخول…" : "دخول"}
          </button>
        </div>
      </form>

      <section className="card login-card">
        <h2>فحص بيئة التطوير</h2>
        <EnvStatus />
      </section>
    </div>
  );
}
