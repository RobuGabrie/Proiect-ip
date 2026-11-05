import type { ReservationStatus, Resource, Role, ScheduleInterval } from "./api";

const TIME_ZONE = "Europe/Bucharest";

const dateParts = new Intl.DateTimeFormat("en-CA", {
  timeZone: TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});
const timeFormat = new Intl.DateTimeFormat("ro-RO", {
  timeZone: TIME_ZONE,
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});
const longDate = new Intl.DateTimeFormat("ro-RO", {
  timeZone: TIME_ZONE,
  day: "numeric",
  month: "long",
  year: "numeric",
});

/** Data calendaristică din România, ca „AAAA-LL-ZZ”. */
export function localDay(value: string | Date): string {
  return dateParts.format(new Date(value));
}

export function localTime(value: string | Date): string {
  return timeFormat.format(new Date(value));
}

export function formatDate(value: string | Date): string {
  return longDate.format(new Date(value));
}

export function dayOfMonth(value: string | Date): string {
  return String(Number(localDay(value).slice(8, 10)));
}

const monthFormat = new Intl.DateTimeFormat("ro-RO", { timeZone: TIME_ZONE, month: "long" });

export function monthName(value: string | Date): string {
  return monthFormat.format(new Date(value));
}

export function formatRange(start: string, end: string): string {
  return `${localTime(start)} – ${localTime(end)}`;
}

export function addDays(day: string, amount: number): string {
  const date = new Date(`${day}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + amount);
  return date.toISOString().slice(0, 10);
}

/** Lunea săptămânii din care face parte ziua. */
export function weekStart(day: string): string {
  const weekday = new Date(`${day}T12:00:00Z`).getUTCDay();
  return addDays(day, weekday === 0 ? -6 : 1 - weekday);
}

/** Transformă o dată și o oră din România într-un moment cu fus orar, potrivit pentru API. */
export function toInstant(day: string, time: string): string {
  const guess = new Date(`${day}T${time}:00Z`);
  const shown = new Date(`${localDay(guess)}T${localTime(guess)}:00Z`);
  return new Date(guess.getTime() - (shown.getTime() - guess.getTime())).toISOString();
}

const DAY_NAMES = ["Luni", "Marți", "Miercuri", "Joi", "Vineri", "Sâmbătă", "Duminică"];

export function dayName(weekday: number): string {
  return DAY_NAMES[weekday - 1];
}

export function formatSchedule(intervals: ScheduleInterval[]): string {
  if (intervals.length === 0) {
    return "Nedefinit";
  }
  const groups: { from: number; to: number; hours: string }[] = [];
  for (const interval of intervals) {
    const hours = `${interval.oraDeschidere} – ${interval.oraInchidere}`;
    const last = groups.at(-1);
    if (last && last.hours === hours && last.to === interval.ziSaptamana - 1) {
      last.to = interval.ziSaptamana;
    } else {
      groups.push({ from: interval.ziSaptamana, to: interval.ziSaptamana, hours });
    }
  }
  return groups
    .map(({ from, to, hours }) =>
      from === to ? `${dayName(from)}, ${hours}` : `${dayName(from)} – ${dayName(to)}, ${hours}`,
    )
    .join("; ");
}

export const ROLE_LABELS: Record<Role, string> = {
  STUDENT: "Student",
  CADRU_DIDACTIC: "Cadru didactic",
  CERCETATOR: "Cercetător",
  ADMIN: "Administrator",
};

export const STATUS_LABELS: Record<ReservationStatus, string> = {
  PENDING: "În așteptare",
  AWAITING_TRAINING: "Necesită instruire",
  APPROVED: "Aprobată",
  REJECTED: "Respinsă",
  CANCELLED: "Anulată",
  COMPLETED: "Finalizată",
};

export function fullName(person: { prenume: string; nume: string }): string {
  return `${person.prenume} ${person.nume}`;
}

export function initials(person: { prenume: string; nume: string }): string {
  return `${person.prenume[0] ?? ""}${person.nume[0] ?? ""}`.toUpperCase();
}

export function resourceSummary(resource: Resource): string {
  const parts = [resource.descriere];
  if (resource.tip === "SALA") {
    if (resource.etaj !== null) parts.push(`Etaj ${resource.etaj}`);
    if (resource.locuri !== null) parts.push(`${resource.locuri} locuri`);
  } else if (resource.locatie) {
    parts.push(resource.locatie);
  }
  return parts.filter(Boolean).join(", ");
}

export function isActiveReservation(status: ReservationStatus): boolean {
  return status === "PENDING" || status === "AWAITING_TRAINING" || status === "APPROVED";
}
