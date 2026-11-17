import { useEffect, useState } from "react";
import { apiGet } from "../api";

export type Status = "checking" | "ok" | "error";

const LABELS: Record<Status, string> = {
  checking: "جارٍ الفحص…",
  ok: "متصل",
  error: "غير متصل",
};

/** Checks /api/health and /api/health/db once (development environment check from the skeleton). */
export function useEnvStatus(): { api: Status; db: Status } {
  const [api, setApi] = useState<Status>("checking");
  const [db, setDb] = useState<Status>("checking");
  useEffect(() => {
    apiGet("/health").then(() => setApi("ok")).catch(() => setApi("error"));
    apiGet("/health/db").then(() => setDb("ok")).catch(() => setDb("error"));
  }, []);
  return { api, db };
}

/** Full table, shown on SCR-01. */
export default function EnvStatus() {
  const { api, db } = useEnvStatus();
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

const DOT: Record<Status, string> = { checking: "wait-dot", ok: "ok-dot", error: "err-dot" };

/** Compact indicator for the top bar. */
export function ConnectionIndicator() {
  const { api, db } = useEnvStatus();
  return (
    <span className="conn" aria-live="polite">
      <span>
        <i className={DOT[api]} /> الخادم: {LABELS[api]}
      </span>
      <span>
        <i className={DOT[db]} /> قاعدة البيانات: {LABELS[db]}
      </span>
    </span>
  );
}
