"use client";

import { useEffect } from "react";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error); // hook up to your error tracker (Sentry/OTel) here
  }, [error]);

  return (
    <main>
      <h1>Something went wrong</h1>
      <p>Reference: {error.digest ?? "n/a"}</p>
      <button type="button" onClick={reset}>
        Try again
      </button>
    </main>
  );
}
