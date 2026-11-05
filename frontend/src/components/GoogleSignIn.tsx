"use client";

import Script from "next/script";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { ApiError, apiFetch, type AuthResponse } from "@/lib/api";
import { saveToken } from "@/lib/session";
import styles from "./GoogleSignIn.module.css";

type CredentialResponse = { credential: string };

type GoogleIdentity = {
  accounts: {
    id: {
      initialize(config: {
        client_id: string;
        hd: string;
        callback: (response: CredentialResponse) => void;
      }): void;
      renderButton(parent: HTMLElement, options: Record<string, string | number>): void;
    };
  };
};

declare global {
  interface Window {
    google?: GoogleIdentity;
  }
}

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;

export function GoogleSignIn() {
  const router = useRouter();
  const buttonRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState(CLIENT_ID ? "" : "Autentificarea Google nu este configurată.");

  async function handleCredential({ credential }: CredentialResponse) {
    setError("");
    try {
      const { accessToken } = await apiFetch<AuthResponse>("/auth/google", {
        method: "POST",
        body: JSON.stringify({ idToken: credential }),
      });
      saveToken(accessToken);
      router.replace("/");
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Serverul nu răspunde. Încearcă din nou.");
    }
  }

  function renderButton() {
    if (!CLIENT_ID || !window.google || !buttonRef.current) {
      return;
    }
    window.google.accounts.id.initialize({
      client_id: CLIENT_ID,
      hd: "student.usv.ro",
      callback: handleCredential,
    });
    window.google.accounts.id.renderButton(buttonRef.current, {
      theme: "outline",
      size: "large",
      text: "continue_with",
      locale: "ro",
      width: 358,
    });
  }

  return (
    <>
      <Script
        src="https://accounts.google.com/gsi/client"
        onReady={renderButton}
        onError={() => setError("Butonul Google nu s-a putut încărca. Verifică conexiunea la internet.")}
      />
      <div ref={buttonRef} className={styles.button} />
      {error && (
        <p role="alert" className={styles.error}>
          {error}
        </p>
      )}
    </>
  );
}
