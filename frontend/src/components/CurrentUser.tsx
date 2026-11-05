"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ApiError, apiFetch, type User } from "@/lib/api";
import { clearToken, getToken } from "@/lib/session";

type State =
  | { kind: "loading" }
  | { kind: "signedOut" }
  | { kind: "signedIn"; user: User }
  | { kind: "error"; message: string };

export function CurrentUser() {
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    let active = true;

    const load = getToken()
      ? apiFetch<User>("/users/me").then((user): State => ({ kind: "signedIn", user }))
      : Promise.resolve<State>({ kind: "signedOut" });

    load
      .catch((error): State => {
        if (error instanceof ApiError && error.status === 401) {
          return { kind: "signedOut" };
        }
        return { kind: "error", message: "Nu am putut încărca profilul." };
      })
      .then((next) => {
        if (active) {
          setState(next);
        }
      });

    return () => {
      active = false;
    };
  }, []);

  if (state.kind === "loading") {
    return null;
  }
  if (state.kind === "error") {
    return <p role="alert">{state.message}</p>;
  }
  if (state.kind === "signedOut") {
    return <Link href="/login">Conectează-te</Link>;
  }

  const { prenume, nume, email, role } = state.user;
  return (
    <div>
      <p>
        Autentificat ca <strong>{`${prenume} ${nume}`}</strong> ({email}), rol {role}.
      </p>
      <button
        type="button"
        onClick={() => {
          clearToken();
          setState({ kind: "signedOut" });
        }}
      >
        Deconectare
      </button>
    </div>
  );
}
