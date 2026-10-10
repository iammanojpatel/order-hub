"use client";

import { useActionState, useId, useState } from "react";

import type { CreateProductState } from "../api/actions";
import styles from "./products.module.css";

type Action = (prev: CreateProductState, data: FormData) => Promise<CreateProductState>;

interface Props {
  action: Action;
}

const FIELDS = [
  { name: "sku", label: "SKU", placeholder: "MUG-001" },
  { name: "name", label: "Name", placeholder: "Coffee mug" },
  { name: "price_amount", label: "Price", placeholder: "249.00", inputMode: "decimal" as const },
  { name: "currency", label: "Currency", placeholder: "INR", defaultValue: "INR" },
] as const;

export function CreateProductForm({ action }: Props) {
  const [state, formAction, pending] = useActionState(action, { ok: false });
  const [idempotencyKey] = useState(() => crypto.randomUUID()); // one key per form instance
  const formId = useId();

  return (
    <form
      action={formAction}
      className={styles.form}
      aria-labelledby={`${formId}-title`}
      noValidate
    >
      <h2 id={`${formId}-title`}>New product</h2>
      <input type="hidden" name="idempotencyKey" value={idempotencyKey} />
      {FIELDS.map((f) => {
        const errors = state.fieldErrors?.[f.name];
        const inputId = `${formId}-${f.name}`;
        const errorId = `${inputId}-error`;
        return (
          <div key={f.name} className={styles.field}>
            <label htmlFor={inputId}>{f.label}</label>
            <input
              id={inputId}
              name={f.name}
              placeholder={f.placeholder}
              defaultValue={"defaultValue" in f ? f.defaultValue : undefined}
              inputMode={"inputMode" in f ? f.inputMode : undefined}
              aria-invalid={errors ? true : undefined}
              aria-describedby={errors ? errorId : undefined}
              required
            />
            {errors && (
              <span id={errorId} className={styles.error}>
                {errors.join(", ")}
              </span>
            )}
          </div>
        );
      })}
      <button type="submit" disabled={pending} aria-busy={pending}>
        {pending ? "Saving…" : "Create product"}
      </button>
      {state.message && (
        <p role={state.ok ? "status" : "alert"} className={state.ok ? styles.ok : styles.error}>
          {state.message}
        </p>
      )}
    </form>
  );
}
