"use client";

import { useState } from "react";
import { apiFetch, apiSend, errorMessage, withQuery, type Page, type Reservation, type ReservationStatus } from "@/lib/api";
import { formatDate, formatRange, isActiveReservation } from "@/lib/format";
import { useLoad } from "@/lib/useLoad";
import { ReservationBadge } from "./ReservationBadge";
import { DateLeaf, Detail, Dialog, Empty, ErrorNote, Loading, PageHeader, SearchBox, Tabs } from "./ui";

type Filter = "" | ReservationStatus;

function cancellable(reservation: Reservation): boolean {
  return isActiveReservation(reservation.status) && new Date(reservation.start).getTime() > Date.now();
}

function DetailsDialog({ reservation, onClose }: { reservation: Reservation; onClose: () => void }) {
  return (
    <Dialog title={reservation.resource.nume} onClose={onClose}>
      <div className="form">
        <div className="form-grid">
          <Detail label="Data">{formatDate(reservation.start)}</Detail>
          <Detail label="Interval">{formatRange(reservation.start, reservation.end)}</Detail>
          <Detail label="Echipa">{reservation.echipa}</Detail>
          <Detail label="Status">
            <ReservationBadge status={reservation.status} />
          </Detail>
        </div>
        {reservation.scop && <Detail label="Scop">{reservation.scop}</Detail>}
        {reservation.motivRespingere && <Detail label="Motivul respingerii">{reservation.motivRespingere}</Detail>}
        {reservation.status === "AWAITING_TRAINING" && (
          <p className="info-note">
            {reservation.instruireFinalizata
              ? "Instruirea a fost confirmată. Cererea așteaptă aprobarea."
              : "Contactează administratorul resursei pentru instruire."}
          </p>
        )}
        {reservation.necesitaReanalizare && (
          <p className="info-note">Rezervarea este afectată de o mentenanță și va fi reanalizată.</p>
        )}
        <div className="dialog-actions">
          <button type="button" className="btn" onClick={onClose}>
            Închide
          </button>
        </div>
      </div>
    </Dialog>
  );
}

function CancelDialog({
  reservation,
  onClose,
  onCancelled,
}: {
  reservation: Reservation;
  onClose: () => void;
  onCancelled: () => void;
}) {
  const [error, setError] = useState("");

  async function confirm() {
    try {
      await apiSend("POST", `/reservations/${reservation.id}/cancel`);
      onCancelled();
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  return (
    <Dialog title="Anulezi rezervarea?" onClose={onClose}>
      <div className="form">
        <ErrorNote message={error} />
        <p>
          {reservation.resource.nume}, {formatDate(reservation.start)},{" "}
          {formatRange(reservation.start, reservation.end)}.
        </p>
        <div className="dialog-actions">
          <button type="button" className="btn" onClick={onClose}>
            Păstrează
          </button>
          <button type="button" className="btn btn-danger" onClick={confirm}>
            Anulează rezervarea
          </button>
        </div>
      </div>
    </Dialog>
  );
}

export function MyReservations() {
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<Filter>("");
  const [details, setDetails] = useState<Reservation | null>(null);
  const [cancelling, setCancelling] = useState<Reservation | null>(null);

  const { data, error, loading, reload } = useLoad(
    () => apiFetch<Page<Reservation>>(withQuery("/reservations", { q, status: filter, pageSize: 100 })),
    `${q}/${filter}`,
  );

  return (
    <>
      <PageHeader
        title="Rezervările mele"
        subtitle="Urmărește statusul și gestionează rezervările tale."
        count={data ? `${data.total} ${data.total === 1 ? "rezervare" : "rezervări"}` : undefined}
      />
      <div className="toolbar">
        <SearchBox value={q} onChange={setQ} placeholder="Caută după resursă sau dată (ZZ.LL.AAAA)…" />
        <Tabs
          label="Status"
          value={filter}
          onChange={setFilter}
          options={[
            { value: "", label: "Toate" },
            { value: "APPROVED", label: "Aprobate" },
            { value: "PENDING", label: "În așteptare" },
            { value: "REJECTED", label: "Respinse" },
          ]}
        />
      </div>
      <ErrorNote message={error} />
      {loading && !data ? (
        <Loading />
      ) : data && data.items.length > 0 ? (
        <div className="list">
          {data.items.map((reservation) => (
            <article className="card row" key={reservation.id}>
              <DateLeaf date={reservation.start} />
              <div className="row-main">
                <div className="row-title row-title-large">{reservation.resource.nume}</div>
                <div className="row-subtitle">
                  {formatRange(reservation.start, reservation.end)}, {reservation.echipa}
                </div>
              </div>
              <ReservationBadge status={reservation.status} />
              <div className="row-actions">
                <button type="button" className="btn" onClick={() => setDetails(reservation)}>
                  Detalii
                </button>
                {cancellable(reservation) && (
                  <button type="button" className="btn btn-danger" onClick={() => setCancelling(reservation)}>
                    Anulează
                  </button>
                )}
              </div>
            </article>
          ))}
        </div>
      ) : (
        !error && <Empty>Nu ai rezervări pentru filtrele alese. Alege o resursă din catalog ca să începi.</Empty>
      )}
      {details && <DetailsDialog reservation={details} onClose={() => setDetails(null)} />}
      {cancelling && (
        <CancelDialog
          reservation={cancelling}
          onClose={() => setCancelling(null)}
          onCancelled={() => {
            setCancelling(null);
            reload();
          }}
        />
      )}
    </>
  );
}
