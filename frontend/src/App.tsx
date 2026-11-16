import { useEffect, useState } from "react";
import { apiGet } from "./api";

type Status = "checking" | "ok" | "error";

const LABELS: Record<Status, string> = {
  checking: "جارٍ الفحص…",
  ok: "متصل",
  error: "غير متصل",
};

export default function App() {
  const [api, setApi] = useState<Status>("checking");
  const [db, setDb] = useState<Status>("checking");

  useEffect(() => {
    apiGet("/health").then(() => setApi("ok")).catch(() => setApi("error"));
    apiGet("/health/db").then(() => setDb("ok")).catch(() => setDb("error"));
  }, []);

  return (
    <main className="page">
      <header className="top">
        <img src="/logo.png" alt="" className="logo" />
        <h1>محور</h1>
      </header>
      <section className="card">
        <h2>فحص بيئة التطوير</h2>
        <table className="tb">
          <tbody>
            <tr>
              <th>الخدمة الخلفية (FastAPI)</th>
              <td className={api}>{LABELS[api]}</td>
            </tr>
            <tr>
              <th>قاعدة البيانات (PostgreSQL)</th>
              <td className={db}>{LABELS[db]}</td>
            </tr>
          </tbody>
        </table>
      </section>
    </main>
  );
}
