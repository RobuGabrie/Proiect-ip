"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { homePath, useAuth } from "./AuthProvider";
import { Loading } from "./ui";

export function HomeRedirect() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading) {
      router.replace(user ? homePath(user) : "/login");
    }
  }, [loading, user, router]);

  return (
    <main className="shell-loading">
      <Loading />
    </main>
  );
}
