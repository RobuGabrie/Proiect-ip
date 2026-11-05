"use client";

import Link from "next/link";
import { useState } from "react";
import { apiFetch, apiSend, errorMessage, type Resource, type WaitlistEntry } from "@/lib/api";
import { formatDate, formatRange } from "@/lib/format";
import { useLoad } from "@/lib/useLoad";
import { Badge, Empty, ErrorNote, Icon, Loading, PageHeader } from "./ui";

export function WaitlistPage() {
  const [actionError, setActionError] = useState("");
  const { data, error, loading, reload } = useLoad(async () => {
    const entries = await apiFetch<WaitlistEntry[]>("/waitlist");
    const ids = [...new Set(entries.map((entry) => entry.resourceId))];
    const resources = await Promise.all(ids.map((id) => apiFetch<Resource>(`/resources/${id}`)));
    return { entries, names: new Map(resources.map((resource) => [resource.id, resource.nume])) };
  }, "waitlist");

  async function leave(entry: WaitlistEntry) {
    setActionError("");
    try {
      await apiSend("DELETE", `/waitlist/${entry.id}`);
      reload();
    } catch (cause) {
      setActionError(errorMessage(cause));
    }
  }

  return (
    <>
      <PageHeader
        title="Listă de așteptare"
        subtitle="Primești un email când se eliberează un interval dorit."
        count={data ? `${data.entries.length} înscrieri` : undefined}
      />
      <ErrorNote message={error || actionError} />
      {loading && !data ? (
        <Loading />
      ) : data && data.entries.length > 0 ? (
        <div className="list">
          {data.entries.map((entry) => (
            <article className="card row" key={entry.id}>
              <div className="tile">
                <Icon name="clock" size={20} />
              </div>
              <div className="row-main">
                <div className="row-title">{data.names.get(entry.resourceId)}</div>
                <div className="row-subtitle">
                  {formatDate(entry.start)}, {formatRange(entry.start, entry.end)}
                </div>
              </div>
              {entry.notificat ? <Badge tone="green">Interval eliberat</Badge> : <Badge tone="orange">În așteptare</Badge>}
              <div className="row-actions">
                {entry.notificat && (
                  <Link className="btn btn-primary" href={`/resurse/${entry.resourceId}`}>
                    Rezervă
                  </Link>
                )}
                <button type="button" className="btn btn-danger" onClick={() => leave(entry)}>
                  Renunță
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        !error && <Empty>Nu ești înscris pe nicio listă. Te poți înscrie din calendarul unei resurse ocupate.</Empty>
      )}
    </>
  );
}
