import { clearToken, getToken } from "./session";

export type Role = "STUDENT" | "CADRU_DIDACTIC" | "CERCETATOR" | "ADMIN";

export type User = {
  id: number;
  email: string;
  nume: string;
  prenume: string;
  role: Role;
};

export type AuthResponse = {
  accessToken: string;
  tokenType: string;
  expiresIn: number;
  user: User;
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (init.body) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1${path}`, { ...init, headers });

  if (!response.ok) {
    if (response.status === 401) {
      clearToken();
    }
    const error = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      error?.code ?? "EROARE",
      error?.message ?? "A apărut o eroare. Încearcă din nou.",
    );
  }
  return response.json();
}
