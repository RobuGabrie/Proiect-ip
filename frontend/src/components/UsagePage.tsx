"use client";

import { useState } from "react";
import { apiFetch, withQuery, type TeamUsage } from "@/lib/api";
import { addDays, localDay } from "@/lib/format";
import { useLoad } from "@/lib/useLoad";
import { Empty, ErrorNote, Loading, PageHeader } from "./ui";

export function UsagePage() {
  const today = localDay(new Date());
  const [from, setFrom] = useState(addDays(today, -30));
  const [to, setTo] = useState(addDays(today, 30));
  const { data, error, loading } = useLoad(
    () => apiFetch<TeamUsage[]>(withQuery("/approvals/usage", { from, to })),
    `${from}/${to}`,
  );

  return (
    <>
      <PageHeader
        title="Utilizare pe echipe"
        subtitle="Rezervările aprobate la resursele tale. Sistemul nu impune limite; decizia îți aparține."
      />
      <div className="toolbar">
        <label className="field">
          De la
          <input type="date" value={from} onChange={(event) => setFrom(event.target.value)} />
        </label>
        <label className="field">
          Până la
          <input type="date" value={to} onChange={(event) => setTo(event.target.value)} />
        </label>
      </div>
      <ErrorNote message={error} />
      {loading && !data ? (
        <Loading />
      ) : data && data.length > 0 ? (
        <div className="glass table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Echipa</th>
                <th scope="col">Rezervări</th>
                <th scope="col">Ore rezervate</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.teamId}>
                  <td>{row.echipa}</td>
                  <td>{row.numarRezervari}</td>
                  <td>{row.oreRezervate}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        !error && <Empty>Nu există rezervări aprobate în acest interval.</Empty>
      )}
    </>
  );
}
