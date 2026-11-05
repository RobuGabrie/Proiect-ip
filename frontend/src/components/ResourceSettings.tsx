"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  apiFetch,
  apiSend,
  errorMessage,
  type MaintenanceWindow,
  type Resource,
  type ScheduleInterval,
} from "@/lib/api";
import { dayName, formatDate, localTime, toInstant } from "@/lib/format";
import { useLoad } from "@/lib/useLoad";
import { Empty, ErrorNote, Icon, Loading, SuccessNote } from "./ui";

const HALF_HOURS = Array.from({ length: 48 }, (_, index) => {
  const hours = String(Math.floor(index / 2)).padStart(2, "0");
  return `${hours}:${index % 2 ? "30" : "00"}`;
});
const DAYS = [1, 2, 3, 4, 5, 6, 7];

function TimeSelect({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <select aria-label={label} className="select" value={value} onChange={(event) => onChange(event.target.value)}>
      {HALF_HOURS.map((time) => (
        <option key={time} value={time}>
          {time}
        </option>
      ))}
    </select>
  );
}

function ScheduleEditor({ resourceId, initial }: { resourceId: string; initial: ScheduleInterval[] }) {
  const [intervals, setIntervals] = useState(initial);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(""), 4000);
    return () => clearTimeout(timer);
  }, [message]);

  function change(index: number, patch: Partial<ScheduleInterval>) {
    setIntervals((current) => current.map((item, position) => (position === index ? { ...item, ...patch } : item)));
  }

  async function save() {
    setError("");
    setMessage("");
    try {
      setIntervals(await apiSend<ScheduleInterval[]>("PUT", `/resources/${resourceId}/schedule`, intervals));
      setMessage("Programul a fost salvat.");
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  return (
    <section className="glass section">
      <h2>Program de funcționare</h2>
      <SuccessNote message={message} />
      <ErrorNote message={error} />
      {intervals.map((interval, index) => (
        <div className="schedule-row" key={index}>
          <select
            aria-label={`Ziua intervalului ${index + 1}`}
            className="select"
           
            value={interval.ziSaptamana}
            onChange={(event) => change(index, { ziSaptamana: Number(event.target.value) })}
          >
            {DAYS.map((day) => (
              <option key={day} value={day}>
                {dayName(day)}
              </option>
            ))}
          </select>
          <TimeSelect
            label={`Deschidere interval ${index + 1}`}
            value={interval.oraDeschidere}
            onChange={(oraDeschidere) => change(index, { oraDeschidere })}
          />
          <TimeSelect
            label={`Închidere interval ${index + 1}`}
            value={interval.oraInchidere}
            onChange={(oraInchidere) => change(index, { oraInchidere })}
          />
          <button
            type="button"
            className="icon-button"
            aria-label={`Șterge intervalul ${index + 1}`}
            onClick={() => setIntervals((current) => current.filter((_, position) => position !== index))}
          >
            ✕
          </button>
        </div>
      ))}
      <div className="dialog-actions">
        <button
          type="button"
          className="btn"
          onClick={() =>
            setIntervals((current) => [...current, { ziSaptamana: 1, oraDeschidere: "08:00", oraInchidere: "20:00" }])
          }
        >
          Adaugă interval
        </button>
        <button type="button" className="btn btn-primary" onClick={save}>
          Salvează programul
        </button>
      </div>
    </section>
  );
}

function MaintenanceEditor({ resourceId }: { resourceId: string }) {
  const { data, error, loading, reload } = useLoad(
    () => apiFetch<MaintenanceWindow[]>(`/resources/${resourceId}/maintenance-windows`),
    `maintenance/${resourceId}`,
  );
  const [startDay, setStartDay] = useState("");
  const [startTime, setStartTime] = useState("08:00");
  const [endDay, setEndDay] = useState("");
  const [endTime, setEndTime] = useState("18:00");
  const [motiv, setMotiv] = useState("");
  const [actionError, setActionError] = useState("");
  const [message, setMessage] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setActionError("");
    setMessage("");
    try {
      const created = await apiSend<{ rezervariDeReanalizat: number[] }>(
        "POST",
        `/resources/${resourceId}/maintenance-windows`,
        {
          dataInceput: toInstant(startDay, startTime),
          dataSfarsit: toInstant(endDay, endTime),
          motiv,
        },
      );
      const affected = created.rezervariDeReanalizat.length;
      setMessage(
        affected
          ? `Mentenanța a fost salvată. ${affected} rezervări sunt marcate pentru reanalizare în pagina Aprobări.`
          : "Mentenanța a fost salvată.",
      );
      setMotiv("");
      reload();
    } catch (cause) {
      setActionError(errorMessage(cause));
    }
  }

  async function cancel(window: MaintenanceWindow) {
    setActionError("");
    try {
      await apiSend("DELETE", `/maintenance-windows/${window.id}`);
      reload();
    } catch (cause) {
      setActionError(errorMessage(cause));
    }
  }

  return (
    <section className="glass section">
      <h2>Mentenanță</h2>
      <SuccessNote message={message} />
      <ErrorNote message={error || actionError} />
      <form className="form" onSubmit={submit}>
        <div className="form-grid">
          <label className="field">
            Început, data
            <input type="date" required value={startDay} onChange={(event) => setStartDay(event.target.value)} />
          </label>
          <label className="field">
            Început, ora
            <input type="time" step={1800} required value={startTime} onChange={(event) => setStartTime(event.target.value)} />
          </label>
          <label className="field">
            Sfârșit, data
            <input type="date" required value={endDay} onChange={(event) => setEndDay(event.target.value)} />
          </label>
          <label className="field">
            Sfârșit, ora
            <input type="time" step={1800} required value={endTime} onChange={(event) => setEndTime(event.target.value)} />
          </label>
        </div>
        <label className="field">
          Motiv
          <input required value={motiv} onChange={(event) => setMotiv(event.target.value)} />
        </label>
        <div className="dialog-actions">
          <button type="submit" className="btn btn-primary">
            Marchează mentenanța
          </button>
        </div>
      </form>
      <span className="section-label">Perioade programate</span>
      {loading && !data ? (
        <Loading />
      ) : data && data.length > 0 ? (
        <div className="list" style={{ marginTop: 8 }}>
          {data.map((window) => (
            <div className="card row" key={window.id}>
              <div className="row-main">
                <div className="row-title">{window.motiv}</div>
                <div className="row-subtitle">
                  {formatDate(window.dataInceput)} {localTime(window.dataInceput)} – {formatDate(window.dataSfarsit)}{" "}
                  {localTime(window.dataSfarsit)}
                </div>
              </div>
              <button type="button" className="btn btn-danger" onClick={() => cancel(window)}>
                Anulează
              </button>
            </div>
          ))}
        </div>
      ) : (
        <p className="row-subtitle">Nicio perioadă programată.</p>
      )}
    </section>
  );
}

export function ResourceSettings({ resourceId }: { resourceId: string }) {
  const { data, error, loading } = useLoad(
    async () => {
      const [resource, schedule] = await Promise.all([
        apiFetch<Resource>(`/resources/${resourceId}`),
        apiFetch<ScheduleInterval[]>(`/resources/${resourceId}/schedule`),
      ]);
      return { resource, schedule };
    },
    resourceId,
  );

  if (loading && !data) return <Loading />;
  if (!data) return error ? <ErrorNote message={error} /> : <Empty>Resursa nu există.</Empty>;
  const { resource, schedule } = data;

  return (
    <>
      <Link className="back-link" href={resource.tip === "SALA" ? "/admin/sali" : "/admin/echipamente"}>
        <Icon name="left" size={16} />
        Înapoi
      </Link>
      <header className="page-header">
        <div>
          <h1>{resource.nume}</h1>
          <p>Program de funcționare și perioade de mentenanță.</p>
        </div>
      </header>
      <ScheduleEditor resourceId={resourceId} initial={schedule} />
      <MaintenanceEditor resourceId={resourceId} />
    </>
  );
}
