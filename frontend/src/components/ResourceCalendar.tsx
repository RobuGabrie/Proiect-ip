"use client";

import Link from "next/link";
import { useState } from "react";
import {
  ApiError,
  apiFetch,
  apiSend,
  errorMessage,
  withQuery,
  type Reservation,
  type Resource,
  type ScheduleInterval,
  type Slot,
} from "@/lib/api";
import {
  addDays,
  dayName,
  formatDate,
  formatSchedule,
  fullName,
  localDay,
  localTime,
  resourceSummary,
  weekStart,
} from "@/lib/format";
import { useLoad } from "@/lib/useLoad";
import { useAuth } from "./AuthProvider";
import { ResourceStatusBadge } from "./ResourceCatalog";
import { Detail, Dialog, ErrorNote, Icon, Loading, SuccessNote } from "./ui";

const LEGEND = [
  { label: "Liber", className: "slot-LIBER" },
  { label: "Parțial ocupat", className: "slot-PARTIAL" },
  { label: "Ocupat", className: "slot-OCUPAT" },
  { label: "Mentenanță", className: "slot-MENTENANTA" },
];

const SLOT_LABELS: Record<Slot["status"], string> = {
  LIBER: "liber",
  PARTIAL: "parțial ocupat",
  OCUPAT: "ocupat",
  MENTENANTA: "în mentenanță",
};

type Selection = { day: string; first: number; last: number };

function ReservationDialog({
  resource,
  start,
  end,
  onClose,
  onCreated,
  onSlotTaken,
}: {
  resource: Resource;
  start: string;
  end: string;
  onClose: () => void;
  onCreated: (reservation: Reservation) => void;
  onSlotTaken: (message: string) => void;
}) {
  const [echipa, setEchipa] = useState("");
  const [scop, setScop] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      onCreated(
        await apiSend<Reservation>("POST", "/reservations", {
          resourceId: resource.id,
          start,
          end,
          echipa,
          scop: scop || null,
        }),
      );
    } catch (cause) {
      if (cause instanceof ApiError && cause.code === "SLOT_OCUPAT") {
        onSlotTaken(cause.message);
        return;
      }
      setError(errorMessage(cause));
      setSaving(false);
    }
  }

  return (
    <Dialog title={`Rezervă ${resource.nume}`} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <p className="info-note">
          {formatDate(start)}, {localTime(start)} – {localTime(end)}. Cererea trebuie aprobată de administratorul
          resursei.
        </p>
        <ErrorNote message={error} />
        <label className="field">
          Echipa
          <input required maxLength={150} value={echipa} onChange={(event) => setEchipa(event.target.value)} />
        </label>
        <label className="field">
          Scop (opțional)
          <textarea rows={3} value={scop} onChange={(event) => setScop(event.target.value)} />
        </label>
        <div className="dialog-actions">
          <button type="button" className="btn" onClick={onClose}>
            Renunță
          </button>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? "Se trimite…" : "Trimite cererea"}
          </button>
        </div>
      </form>
    </Dialog>
  );
}

export function ResourceCalendar({ resourceId }: { resourceId: string }) {
  const { user } = useAuth();
  const [monday, setMonday] = useState(() => weekStart(localDay(new Date())));
  const [selection, setSelection] = useState<Selection | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [canJoinWaitlist, setCanJoinWaitlist] = useState(false);
  const [now] = useState(() => Date.now());

  const resource = useLoad(
    async () => {
      const [details, schedule] = await Promise.all([
        apiFetch<Resource>(`/resources/${resourceId}`),
        apiFetch<ScheduleInterval[]>(`/resources/${resourceId}/schedule`),
      ]);
      return { details, schedule };
    },
    `resource/${resourceId}`,
  );
  const slots = useLoad(
    () => apiFetch<Slot[]>(withQuery(`/resources/${resourceId}/availability`, { from: monday, to: addDays(monday, 6) })),
    `${resourceId}/${monday}`,
  );

  const today = localDay(new Date());
  const days = Array.from({ length: 7 }, (_, index) => addDays(monday, index));
  const byDay = new Map<string, Map<string, Slot>>();
  const times = new Set<string>();
  for (const slot of slots.data ?? []) {
    const day = localDay(slot.start);
    const time = localTime(slot.start);
    times.add(time);
    if (!byDay.has(day)) byDay.set(day, new Map());
    byDay.get(day)?.set(time, slot);
  }
  const orderedTimes = [...times].sort();

  const selected = selection
    ? orderedTimes.slice(selection.first, selection.last + 1).map((time) => byDay.get(selection.day)?.get(time))
    : [];
  const selectedSlots = selected.filter((slot): slot is Slot => Boolean(slot));
  const selectionFull = selectedSlots.some((slot) => slot.status === "OCUPAT");
  const selectionStart = selectedSlots[0]?.start;
  const selectionEnd = selectedSlots.at(-1)?.end;

  function clickSlot(day: string, index: number) {
    setMessage("");
    setError("");
    setCanJoinWaitlist(false);
    if (selection && selection.day === day && index > selection.first && selection.last === selection.first) {
      const range = orderedTimes.slice(selection.first, index + 1).map((time) => byDay.get(day)?.get(time));
      const continuous = range.every(
        (slot, position) =>
          slot &&
          slot.status !== "MENTENANTA" &&
          (position === 0 || range[position - 1]?.end === slot.start),
      );
      if (continuous) {
        setSelection({ day, first: selection.first, last: index });
        return;
      }
    }
    setSelection({ day, first: index, last: index });
  }

  async function joinWaitlist() {
    setError("");
    try {
      await apiSend("POST", "/waitlist", { resourceId: Number(resourceId), start: selectionStart, end: selectionEnd });
      setMessage("Te-ai înscris pe lista de așteptare. Primești un email când se eliberează intervalul.");
      setSelection(null);
      setCanJoinWaitlist(false);
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  if (resource.loading && !resource.data) return <Loading />;
  if (!resource.data) return <ErrorNote message={resource.error} />;
  const { details, schedule } = resource.data;

  return (
    <>
      <Link className="back-link" href={details.tip === "SALA" ? "/sali" : "/echipamente"}>
        <Icon name="left" size={16} />
        Înapoi la {details.tip === "SALA" ? "săli" : "echipamente"}
      </Link>
      <header className="page-header">
        <div>
          <h1>{details.nume}</h1>
          <p>{resourceSummary(details)}</p>
        </div>
        <ResourceStatusBadge resource={details} />
      </header>

      <section className="glass section">
        <div className="detail-grid">
          <Detail label="Program">{formatSchedule(schedule)}</Detail>
          <Detail label="Responsabil">{details.administratori.map(fullName).join(", ") || "—"}</Detail>
          <Detail label="Echipe simultan">{details.maxEchipeSimultane}</Detail>
          {details.durataMaximaMin && (
            <Detail label="Durată maximă">{details.durataMaximaMin / 60} ore / rezervare</Detail>
          )}
          {details.necesitaInstruire && <Detail label="Instruire">Necesară înainte de folosire</Detail>}
        </div>
      </section>

      <SuccessNote message={message} />
      <ErrorNote message={error || slots.error} />

      <section className="glass section">
        <div className="calendar-toolbar">
          <div className="calendar-nav">
            <button
              type="button"
              className="btn"
              aria-label="Săptămâna anterioară"
              disabled={monday <= weekStart(localDay(new Date()))}
              onClick={() => {
                setSelection(null);
                setMonday(addDays(monday, -7));
              }}
            >
              <Icon name="left" size={16} />
            </button>
            <span>
              {formatDate(`${monday}T12:00:00Z`)} – {formatDate(`${addDays(monday, 6)}T12:00:00Z`)}
            </span>
            <button
              type="button"
              className="btn"
              aria-label="Săptămâna următoare"
              onClick={() => {
                setSelection(null);
                setMonday(addDays(monday, 7));
              }}
            >
              <Icon name="right" size={16} />
            </button>
          </div>
          <div className="legend">
            {LEGEND.map((item) => (
              <span key={item.label}>
                <i className={item.className} />
                {item.label}
              </span>
            ))}
          </div>
        </div>

        {slots.loading && !slots.data ? (
          <Loading />
        ) : orderedTimes.length === 0 ? (
          <p className="muted-note">Resursa nu are program în această săptămână.</p>
        ) : (
          <div className="calendar-scroll">
            <table className="calendar">
              <thead>
                <tr>
                  <th className="time-cell" aria-label="Ora" />
                  {days.map((day, index) => (
                    <th key={day} scope="col" className={day === today ? "day-today" : undefined}>
                      <span>{dayName(index + 1)}</span>
                      <strong>{Number(day.slice(8, 10))}</strong>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {orderedTimes.map((time, index) => (
                  <tr key={time}>
                    <th scope="row" className={time.endsWith(":00") ? "time-cell time-hour" : "time-cell"}>
                      {time}
                    </th>
                    {days.map((day) => {
                      const slot = byDay.get(day)?.get(time);
                      if (!slot) {
                        return (
                          <td key={day}>
                            <div className="slot-none" />
                          </td>
                        );
                      }
                      const past = new Date(slot.start).getTime() <= now;
                      const isSelected =
                        selection?.day === day && index >= selection.first && index <= selection.last;
                      const classes = ["slot", isSelected ? "slot-selected" : `slot-${slot.status}`];
                      if (isSelected && selection?.first === index) classes.push("slot-first");
                      if (isSelected && selection?.last === index) classes.push("slot-last");
                      if (past) classes.push("slot-past");
                      return (
                        <td key={day}>
                          <button
                            type="button"
                            className={classes.join(" ")}
                            disabled={past || slot.status === "MENTENANTA"}
                            aria-pressed={isSelected}
                            aria-label={`${dayName(days.indexOf(day) + 1)} ${time}, ${SLOT_LABELS[slot.status]}`}
                            title={`${time}, ${slot.locuriOcupate} din ${slot.locuriTotale} echipe`}
                            onClick={() => clickSlot(day, index)}
                          >
                            {isSelected && selection?.first === index ? time : null}
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {selectionStart && selectionEnd ? (
          <div className="selection-bar">
            <span>
              <strong>{formatDate(selectionStart)}</strong>, {localTime(selectionStart)} – {localTime(selectionEnd)}
              {selection?.first === selection?.last && " (alege și ora de sfârșit, dacă vrei un interval mai lung)"}
            </span>
            <span className="row-actions">
              <button type="button" className="btn" onClick={() => setSelection(null)}>
                Renunță
              </button>
              {selectionFull || canJoinWaitlist ? (
                <button type="button" className="btn btn-primary" onClick={joinWaitlist}>
                  Înscrie-mă pe lista de așteptare
                </button>
              ) : (
                <button type="button" className="btn btn-primary" onClick={() => setDialogOpen(true)}>
                  Continuă
                </button>
              )}
            </span>
          </div>
        ) : (
          orderedTimes.length > 0 && (
            <p className="muted-note">
              {user?.role === "ADMIN"
                ? "Alege un interval din calendar."
                : "Alege un slot; apasă apoi pe alt slot din aceeași zi pentru un interval mai lung."}
            </p>
          )
        )}
      </section>

      {dialogOpen && selectionStart && selectionEnd && (
        <ReservationDialog
          resource={details}
          start={selectionStart}
          end={selectionEnd}
          onClose={() => setDialogOpen(false)}
          onCreated={() => {
            setDialogOpen(false);
            setSelection(null);
            setMessage("Cererea a fost trimisă spre aprobare.");
            slots.reload();
          }}
          onSlotTaken={(text) => {
            setDialogOpen(false);
            setError(text);
            setCanJoinWaitlist(true);
            slots.reload();
          }}
        />
      )}
    </>
  );
}
