"use client";

import { useState } from "react";
import {
  apiFetch,
  apiSend,
  errorMessage,
  withQuery,
  type ApprovalStats,
  type Page,
  type Reservation,
  type ReservationStatus,
} from "@/lib/api";
import { formatDate, formatRange, fullName, isActiveReservation, localDay, localTime, toInstant } from "@/lib/format";
import { useLoad } from "@/lib/useLoad";
import { ReservationBadge } from "./ReservationBadge";
import { Badge, DateLeaf, Detail, Dialog, Empty, ErrorNote, Loading, PageHeader, SearchBox, Tabs } from "./ui";

type Filter = "" | ReservationStatus;

function canDecide(reservation: Reservation): boolean {
  return reservation.status === "PENDING" || reservation.status === "AWAITING_TRAINING";
}

function trainingMissing(reservation: Reservation): boolean {
  return reservation.status === "AWAITING_TRAINING" && !reservation.instruireFinalizata;
}

function RejectDialog({
  reservation,
  onClose,
  onDone,
}: {
  reservation: Reservation;
  onClose: () => void;
  onDone: () => void;
}) {
  const [motiv, setMotiv] = useState("");
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await apiSend("POST", `/approvals/${reservation.id}/reject`, { motiv });
      onDone();
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  return (
    <Dialog title={`Respinge cererea pentru ${reservation.resource.nume}`} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <ErrorNote message={error} />
        <label className="field">
          Motiv
          <textarea required rows={3} value={motiv} onChange={(event) => setMotiv(event.target.value)} />
        </label>
        <div className="dialog-actions">
          <button type="button" className="btn" onClick={onClose}>
            Renunță
          </button>
          <button type="submit" className="btn btn-danger">
            Respinge
          </button>
        </div>
      </form>
    </Dialog>
  );
}

function RescheduleDialog({
  reservation,
  onClose,
  onDone,
}: {
  reservation: Reservation;
  onClose: () => void;
  onDone: () => void;
}) {
  const [day, setDay] = useState(localDay(reservation.start));
  const [start, setStart] = useState(localTime(reservation.start));
  const [end, setEnd] = useState(localTime(reservation.end));
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    try {
      await apiSend("POST", `/reservations/${reservation.id}/reschedule`, {
        start: toInstant(day, start),
        end: toInstant(day, end),
      });
      onDone();
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  return (
    <Dialog title={`Reprogramează ${reservation.resource.nume}`} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <ErrorNote message={error} />
        <label className="field">
          Data
          <input type="date" required value={day} onChange={(event) => setDay(event.target.value)} />
        </label>
        <div className="form-grid">
          <label className="field">
            De la
            <input type="time" step={1800} required value={start} onChange={(event) => setStart(event.target.value)} />
          </label>
          <label className="field">
            Până la
            <input type="time" step={1800} required value={end} onChange={(event) => setEnd(event.target.value)} />
          </label>
        </div>
        <div className="dialog-actions">
          <button type="button" className="btn" onClick={onClose}>
            Renunță
          </button>
          <button type="submit" className="btn btn-primary">
            Reprogramează
          </button>
        </div>
      </form>
    </Dialog>
  );
}

function DetailsDialog({
  reservation,
  onClose,
  onChanged,
  onReschedule,
}: {
  reservation: Reservation;
  onClose: () => void;
  onChanged: () => void;
  onReschedule: () => void;
}) {
  const [error, setError] = useState("");

  async function act(path: string) {
    try {
      await apiSend("POST", path);
      onChanged();
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  return (
    <Dialog title={reservation.resource.nume} onClose={onClose} wide>
      <div className="form">
        <ErrorNote message={error} />
        <div className="form-grid">
          <Detail label="Solicitant">{fullName(reservation.solicitant)}</Detail>
          <Detail label="Echipa">{reservation.echipa}</Detail>
          <Detail label="Data">{formatDate(reservation.start)}</Detail>
          <Detail label="Interval">{formatRange(reservation.start, reservation.end)}</Detail>
          <Detail label="Status">
            <ReservationBadge status={reservation.status} />
          </Detail>
          <Detail label="Istoric">
            {reservation.primaRezervare ? "Prima rezervare a acestei resurse" : "A mai folosit resursa"}
          </Detail>
          <Detail label="Instruire">
            {reservation.instruireFinalizata ? "Finalizată" : reservation.necesitaInstruire ? "Necesară" : "Neînregistrată"}
          </Detail>
        </div>
        {reservation.scop && <Detail label="Scop">{reservation.scop}</Detail>}
        {reservation.motivRespingere && <Detail label="Motivul respingerii">{reservation.motivRespingere}</Detail>}
        {reservation.necesitaReanalizare && isActiveReservation(reservation.status) && (
          <p className="info-note">Intervalul se suprapune cu o mentenanță. Reprogramează sau anulează rezervarea.</p>
        )}
        <div className="dialog-actions">
          <button type="button" className="btn" onClick={onClose}>
            Închide
          </button>
          {reservation.status === "PENDING" && (
            <button type="button" className="btn" onClick={() => act(`/approvals/${reservation.id}/require-training`)}>
              Necesită instruire
            </button>
          )}
          {trainingMissing(reservation) && (
            <button type="button" className="btn" onClick={() => act(`/approvals/${reservation.id}/complete-training`)}>
              Confirmă instruirea
            </button>
          )}
          {isActiveReservation(reservation.status) && (
            <>
              <button type="button" className="btn" onClick={onReschedule}>
                Reprogramează
              </button>
              <button type="button" className="btn btn-danger" onClick={() => act(`/reservations/${reservation.id}/cancel`)}>
                Anulează rezervarea
              </button>
            </>
          )}
        </div>
      </div>
    </Dialog>
  );
}

export function ApprovalsPage() {
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<Filter>("");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [rejecting, setRejecting] = useState<Reservation | null>(null);
  const [rescheduling, setRescheduling] = useState<Reservation | null>(null);
  const [actionError, setActionError] = useState("");

  const stats = useLoad(() => apiFetch<ApprovalStats>("/approvals/stats"), "stats");
  const { data, error, loading, reload } = useLoad(
    () => apiFetch<Page<Reservation>>(withQuery("/approvals", { q, status: filter, pageSize: 100 })),
    `${q}/${filter}`,
  );
  const selected = data?.items.find((reservation) => reservation.id === selectedId) ?? null;

  function refresh() {
    reload();
    stats.reload();
  }

  async function approve(reservation: Reservation) {
    setActionError("");
    try {
      await apiSend("POST", `/approvals/${reservation.id}/approve`);
      refresh();
    } catch (cause) {
      setActionError(errorMessage(cause));
      refresh();
    }
  }

  return (
    <>
      <PageHeader
        title="Aprobări"
        subtitle="Revizuiește cererile de rezervare primite."
      />
      <dl className="stats">
        <div className="stat">
          <dd>{stats.data?.inAsteptare ?? "–"}</dd>
          <dt>în așteptare</dt>
        </div>
        <div className="stat">
          <dd>{stats.data?.aprobateLunaAceasta ?? "–"}</dd>
          <dt>aprobate luna aceasta</dt>
        </div>
        <div className="stat">
          <dd>{stats.data?.resurseRezervateAzi ?? "–"}</dd>
          <dt>resurse rezervate azi</dt>
        </div>
      </dl>
      <div className="toolbar">
        <SearchBox value={q} onChange={setQ} placeholder="Caută după solicitant sau resursă…" />
        <Tabs
          label="Status"
          value={filter}
          onChange={setFilter}
          options={[
            { value: "", label: "Toate" },
            { value: "PENDING", label: "În așteptare" },
            { value: "AWAITING_TRAINING", label: "Instruire" },
            { value: "APPROVED", label: "Aprobate" },
            { value: "REJECTED", label: "Respinse" },
          ]}
        />
      </div>
      <ErrorNote message={error || actionError} />
      {loading && !data ? (
        <Loading />
      ) : data && data.items.length > 0 ? (
        <div className="list">
          {data.items.map((reservation) => (
            <article className="card row" key={reservation.id}>
              <DateLeaf date={reservation.start} />
              <div className="row-main">
                <div className="row-title row-title-large">
                  {reservation.resource.nume}
                  {reservation.resource.locatie &&
                    reservation.resource.locatie !== reservation.resource.nume &&
                    `, ${reservation.resource.locatie}`}
                </div>
                <div className="row-subtitle">
                  {formatRange(reservation.start, reservation.end)}, {fullName(reservation.solicitant)},{" "}
                  {reservation.echipa}
                </div>
              </div>
              <div className="row-badges">
                {reservation.primaRezervare && canDecide(reservation) && <Badge tone="blue">Prima rezervare</Badge>}
                {reservation.necesitaReanalizare && isActiveReservation(reservation.status) && (
                  <Badge tone="red">De reanalizat</Badge>
                )}
                <ReservationBadge status={reservation.status} />
              </div>
              <div className="row-actions">
                <button type="button" className="btn" onClick={() => setSelectedId(reservation.id)}>
                  Detalii
                </button>
                {canDecide(reservation) && (
                  <>
                    <button type="button" className="btn btn-danger" onClick={() => setRejecting(reservation)}>
                      Respinge
                    </button>
                    <button
                      type="button"
                      className="btn btn-primary"
                      disabled={trainingMissing(reservation)}
                      title={trainingMissing(reservation) ? "Confirmă mai întâi instruirea, din Detalii" : undefined}
                      onClick={() => approve(reservation)}
                    >
                      Aprobă
                    </button>
                  </>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        !error && <Empty>Nu există cereri pentru filtrele alese.</Empty>
      )}
      {selected && (
        <DetailsDialog
          reservation={selected}
          onClose={() => setSelectedId(null)}
          onChanged={refresh}
          onReschedule={() => {
            setSelectedId(null);
            setRescheduling(selected);
          }}
        />
      )}
      {rejecting && (
        <RejectDialog
          reservation={rejecting}
          onClose={() => setRejecting(null)}
          onDone={() => {
            setRejecting(null);
            refresh();
          }}
        />
      )}
      {rescheduling && (
        <RescheduleDialog
          reservation={rescheduling}
          onClose={() => setRescheduling(null)}
          onDone={() => {
            setRescheduling(null);
            refresh();
          }}
        />
      )}
    </>
  );
}
