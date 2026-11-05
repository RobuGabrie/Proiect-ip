"use client";

import { useEffect, useState } from "react";

type Status = "checking" | "ok" | "degraded" | "unreachable";

const MESSAGES: Record<Status, string> = {
  checking: "Se verifică conexiunea…",
  ok: "Backend conectat, baza de date disponibilă.",
  degraded: "Backend conectat, baza de date indisponibilă.",
  unreachable: "Backend-ul nu răspunde.",
};

export function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${process.env.NEXT_PUBLIC_API_URL}/health`, { signal: controller.signal })
      .then((response) => setStatus(response.ok ? "ok" : "degraded"))
      .catch(() => {
        if (!controller.signal.aborted) {
          setStatus("unreachable");
        }
      });

    return () => controller.abort();
  }, []);

  return <p role="status">{MESSAGES[status]}</p>;
}
