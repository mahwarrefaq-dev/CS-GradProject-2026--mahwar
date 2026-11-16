import { useEffect, useState } from "react";
import { apiGet } from "../api";

type Status = "checking" | "ok" | "error";

const LABELS: Record<Status, string> = {
  checking: "جارٍ الفحص…",
  ok: "متصل",
  error: "غير متصل",
};

/** Development environment check (backend + database), kept from the project skeleton. */
export default function EnvStatus() {
  const [api, setApi] = useState<Status>("checking");
  const [db, setDb] = useState<Status>("checking");

  useEffect(() => {
    apiGet("/health").then(() => setApi("ok")).catch(() => setApi("error"));
    apiGet("/health/db").then(() => setDb("ok")).catch(() => setDb("error"));
  }, []);

  return (
    <table className="tb env-status">
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
  );
}
