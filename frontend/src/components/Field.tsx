import type { ReactNode } from "react";
import Icon from "./Icon";

interface FieldProps {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  children: ReactNode;
}

/** Label + control + Arabic error message under the field (Design guide: error messages, NFR-06). */
export default function Field({ id, label, error, hint, children }: FieldProps) {
  return (
    <div className={error ? "field has-error" : "field"}>
      <label htmlFor={id}>{label}</label>
      {children}
      {hint && !error && <small className="hint">{hint}</small>}
      {error && (
        <small className="field-error" id={`${id}-error`} role="alert">
          <Icon name="alert-circle" size={14} />
          {error}
        </small>
      )}
    </div>
  );
}
