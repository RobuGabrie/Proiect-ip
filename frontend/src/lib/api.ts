import { clearToken, getToken } from "./session";

export type Role = "STUDENT" | "CADRU_DIDACTIC" | "CERCETATOR" | "ADMIN";
export type ResourceType = "SALA" | "ECHIPAMENT";
export type ResourceStatus = "ACTIVE" | "MAINTENANCE" | "INACTIVE";
export type ReservationStatus =
  | "PENDING"
  | "AWAITING_TRAINING"
  | "APPROVED"
  | "REJECTED"
  | "CANCELLED"
  | "COMPLETED";
export type SlotStatus = "LIBER" | "PARTIAL" | "OCUPAT" | "MENTENANTA";

export type User = {
  id: number;
  email: string;
  nume: string;
  prenume: string;
  role: Role;
};

export type Page<T> = { items: T[]; page: number; pageSize: number; total: number };
export type AuthResponse = { accessToken: string; tokenType: string; expiresIn: number; user: User };
export type Person = { id: number; nume: string; prenume: string };
export type Category = { id: number; nume: string; descriere: string | null };

export type Resource = {
  id: number;
  category: Category;
  tip: ResourceType;
  nume: string;
  descriere: string | null;
  locatie: string | null;
  etaj: number | null;
  locuri: number | null;
  echipare: string | null;
  model: string | null;
  maxEchipeSimultane: number;
  durataMaximaMin: number | null;
  necesitaInstruire: boolean;
  status: ResourceStatus;
  administratori: Person[];
  disponibilitateCurenta: "LIBERA" | "REZERVATA";
};

export type ResourceInput = {
  categoryId: number;
  tip: ResourceType;
  nume: string;
  descriere: string | null;
  locatie: string | null;
  etaj: number | null;
  locuri: number | null;
  echipare: string | null;
  model: string | null;
  maxEchipeSimultane: number;
  durataMaximaMin: number | null;
  necesitaInstruire: boolean;
  status: ResourceStatus;
  adminIds: number[];
};

export type ScheduleInterval = { ziSaptamana: number; oraDeschidere: string; oraInchidere: string };

export type Slot = {
  start: string;
  end: string;
  status: SlotStatus;
  locuriOcupate: number;
  locuriTotale: number;
};

export type MaintenanceWindow = {
  id: number;
  resourceId: number;
  dataInceput: string;
  dataSfarsit: string;
  motiv: string;
};

export type Reservation = {
  id: number;
  resource: { id: number; nume: string; tip: ResourceType; locatie: string | null };
  solicitant: Person;
  echipa: string;
  start: string;
  end: string;
  scop: string | null;
  status: ReservationStatus;
  primaRezervare: boolean;
  necesitaInstruire: boolean;
  instruireFinalizata: boolean;
  necesitaReanalizare: boolean;
  motivRespingere: string | null;
  dataCreare: string;
  dataDecizie: string | null;
};

export type ApprovalStats = { inAsteptare: number; aprobateLunaAceasta: number; resurseRezervateAzi: number };
export type TeamUsage = { teamId: number; echipa: string; numarRezervari: number; oreRezervate: number };
export type WaitlistEntry = {
  id: number;
  resourceId: number;
  start: string;
  end: string;
  dataInscriere: string;
  notificat: boolean;
};

export const SIGNED_OUT_EVENT = "rrm:signed-out";

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

export function errorMessage(error: unknown): string {
  return error instanceof ApiError ? error.message : "Serverul nu răspunde. Încearcă din nou.";
}

type QueryValue = string | number | boolean | null | undefined;

export function withQuery(path: string, query: Record<string, QueryValue>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== null && value !== undefined && value !== "") {
      params.set(key, String(value));
    }
  }
  const text = params.toString();
  return text ? `${path}?${text}` : path;
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
    if (response.status === 401 && token) {
      clearToken();
      window.dispatchEvent(new Event(SIGNED_OUT_EVENT));
    }
    const error = await response.json().catch(() => null);
    throw new ApiError(
      response.status,
      error?.code ?? "EROARE",
      error?.message ?? "A apărut o eroare. Încearcă din nou.",
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}

export function apiSend<T>(method: "POST" | "PUT" | "PATCH" | "DELETE", path: string, body?: unknown): Promise<T> {
  return apiFetch<T>(path, { method, body: body === undefined ? undefined : JSON.stringify(body) });
}
