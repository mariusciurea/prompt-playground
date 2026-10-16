import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import { ErrorBanner, Spinner } from "@/components/ui";
import { AuthLayout } from "@/pages/authLayout";

export function VerifyEmail() {
  const [state, setState] = useState<"working" | "done" | "error">("working");
  const [error, setError] = useState<unknown>(null);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
    if (!token) {
      setState("error");
      setError(new Error("This link is missing its token."));
      return;
    }
    api("/auth/verify-email", { method: "POST", body: { token } })
      .then(() => setState("done"))
      .catch((err) => {
        setError(err);
        setState("error");
      });
  }, []);

  return (
    <AuthLayout title="Confirm your e-mail">
      {state === "working" && <Spinner label="Confirming…" />}
      {state === "done" && (
        <>
          <p className="text-sm text-ok">Your e-mail is confirmed.</p>
          <Link to="/login" className="btn-primary mt-4 w-full">
            Sign in
          </Link>
        </>
      )}
      {state === "error" && (
        <>
          <ErrorBanner error={error} />
          <Link to="/register" className="btn-ghost mt-4 w-full">
            Register again
          </Link>
        </>
      )}
    </AuthLayout>
  );
}
