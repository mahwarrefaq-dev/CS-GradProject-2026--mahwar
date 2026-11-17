import { useState, type FormEvent } from "react";
import { ApiError, apiPost, saveSession, type CurrentUser } from "../api";
import EnvStatus from "../components/EnvStatus";
import Field from "../components/Field";
import Icon from "../components/Icon";
import Logo from "../components/Logo";

interface LoginResponse {
  access_token: string;
  user: CurrentUser;
}

/** SCR-01 – login (FR-01, API-01), laid out after the student's GUI design.
 *  Texts describe only what the system implements (rule-based indicator, not prediction – NFR-07);
 *  no demo accounts with real-looking names (NFR-01). */
export default function LoginPage({ onLogin }: { onLogin: (user: CurrentUser) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await apiPost<LoginResponse>("/auth/login", { username: username.trim(), password });
      saveSession(result.access_token, result.user);
      onLogin(result.user);
    } catch (e) {
      setError(e instanceof ApiError ? e : new ApiError(0, "UNKNOWN", "حدث خطأ غير متوقع"));
      setPassword("");
    } finally {
      setBusy(false);
    }
  }

  const generalError = error && error.fields.length === 0 ? error.message : null;

  return (
    <div className="login">
      <section className="login-brand" aria-label="عن المنصة">
        <div>
          <span className="pill">
            <span className="pulse" />
            نموذج أولي لمشروع التخرج • الإصدار 2
          </span>

          <div className="logo-card">
            <Logo size={112} />
            <h1>محور</h1>
            <div className="latin">Mahwar</div>
            <div className="tagline">
              <span className="bar" />
              <p>منصة متابعة المشروعات ودعم القرار</p>
              <span className="bar" />
            </div>
          </div>

          <div className="login-pitch">
            <h2>من خطة متفرقة إلى قرار مدروس</h2>
            <p>
              نظام ويب يربط المهام والاعتماديات والموارد، ويسجل التقدم بلقطات مؤرخة، ويعرض مؤشرًا مساعدًا لخطر التأخير
              قائمًا على قواعد معلنة، ويحاكي أثر الاضطرابات على الخطة قبل اعتماد أي قرار.
            </p>
          </div>
        </div>

        <div className="login-features">
          <div>
            <strong style={{ color: "#38BDF8" }}>قواعد</strong>
            <span>مؤشر خطر معلن</span>
          </div>
          <div>
            <strong style={{ color: "#818CF8" }}>What-If</strong>
            <span>محاكاة الاضطرابات</span>
          </div>
          <div>
            <strong style={{ color: "#C084FC" }}>Graph</strong>
            <span>شبكة الاعتماد</span>
          </div>
        </div>
      </section>

      <section className="login-form-side">
        <form className="login-box" onSubmit={submit} noValidate>
          <h2>تسجيل الدخول إلى المنصة</h2>
          <p>أدخل اسم المستخدم وكلمة المرور؛ يحدد النظام صلاحياتك تلقائيًا حسب دورك.</p>

          {generalError && (
            <div className="alert" role="alert">
              <Icon name="alert-circle" size={16} />
              <span>{generalError}</span>
            </div>
          )}

          <Field id="username" label="اسم المستخدم (Username)" error={error?.fieldMessage("username")}>
            <div className="input-icon">
              <Icon name="user" size={16} />
              <input
                id="username"
                autoComplete="username"
                dir="ltr"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="pm.s1"
                required
                autoFocus
              />
            </div>
          </Field>

          <Field id="password" label="كلمة المرور (Password)" error={error?.fieldMessage("password")}>
            <div className="input-icon has-toggle">
              <Icon name="lock" size={16} />
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                dir="ltr"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
              />
              <button
                type="button"
                className="icon-btn"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? "إخفاء كلمة المرور" : "إظهار كلمة المرور"}
              >
                <Icon name={showPassword ? "eye-off" : "eye"} size={16} />
              </button>
            </div>
          </Field>

          <button type="submit" className="btn btn-primary btn-block" disabled={busy || !username || !password}>
            {busy ? "جارٍ الدخول…" : "دخول إلى مساحة العمل"}
            {!busy && <Icon name="arrow-left" size={16} />}
          </button>
        </form>

        <details className="env-box" open>
          <summary>فحص بيئة التطوير</summary>
          <EnvStatus />
        </details>
      </section>
    </div>
  );
}
