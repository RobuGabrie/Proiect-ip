"use client";

import Link from "next/link";
import { useState } from "react";
import {
  apiFetch,
  withQuery,
  type Category,
  type Page,
  type Resource,
  type ResourceType,
  type ScheduleInterval,
  type Slot,
} from "@/lib/api";
import { formatSchedule, fullName, localDay, localTime, resourceSummary } from "@/lib/format";
import { useLoad } from "@/lib/useLoad";
import { Badge, Detail, Empty, ErrorNote, Icon, Loading, PageHeader, SearchBox, Tabs } from "./ui";

type AvailabilityFilter = "" | "LIBERA" | "REZERVATA";

const COPY: Record<ResourceType, { title: string; subtitle: string; placeholder: string; unit: [string, string] }> = {
  SALA: {
    title: "Săli",
    subtitle: "Alege o sală și rezervă un interval disponibil.",
    placeholder: "Caută după nume, tip sau locație…",
    unit: ["sală", "săli"],
  },
  ECHIPAMENT: {
    title: "Echipamente",
    subtitle: "Rezervă echipamente de cercetare pentru experimentele tale.",
    placeholder: "Caută după nume, categorie sau locație…",
    unit: ["echipament", "echipamente"],
  },
};

export function ResourceStatusBadge({ resource }: { resource: Resource }) {
  if (resource.status === "INACTIVE") return <Badge tone="gray">Inactivă</Badge>;
  if (resource.status === "MAINTENANCE") return <Badge tone="gray">În mentenanță</Badge>;
  return resource.disponibilitateCurenta === "LIBERA" ? (
    <Badge tone="green">Liberă</Badge>
  ) : (
    <Badge tone="orange">Rezervată</Badge>
  );
}

function freeIntervals(slots: Slot[]): { start: string; end: string }[] {
  const now = Date.now();
  const intervals: { start: string; end: string }[] = [];
  for (const slot of slots) {
    const free = (slot.status === "LIBER" || slot.status === "PARTIAL") && new Date(slot.start).getTime() > now;
    if (!free) continue;
    const last = intervals.at(-1);
    if (last && last.end === slot.start) {
      last.end = slot.end;
    } else {
      intervals.push({ start: slot.start, end: slot.end });
    }
  }
  return intervals;
}

function ResourceDetails({ resource }: { resource: Resource }) {
  const today = localDay(new Date());
  const { data, error, loading } = useLoad(
    async () => {
      const [schedule, slots] = await Promise.all([
        apiFetch<ScheduleInterval[]>(`/resources/${resource.id}/schedule`),
        apiFetch<Slot[]>(withQuery(`/resources/${resource.id}/availability`, { from: today, to: today })),
      ]);
      return { schedule, intervals: freeIntervals(slots) };
    },
    `${resource.id}/${today}`,
  );

  return (
    <div className="row-details">
      <div className="detail-grid">
        <Detail label="Categorie">{resource.category.nume}</Detail>
        <Detail label="Locație">
          {[resource.locatie, resource.etaj !== null ? `Etaj ${resource.etaj}` : null].filter(Boolean).join(", ") || "—"}
        </Detail>
        <Detail label="Responsabil">{resource.administratori.map(fullName).join(", ") || "—"}</Detail>
        {resource.locuri !== null && <Detail label="Capacitate">{resource.locuri} locuri</Detail>}
        {resource.echipare && <Detail label="Echipare">{resource.echipare}</Detail>}
        {resource.model && <Detail label="Model">{resource.model}</Detail>}
        <Detail label="Echipe simultan">{resource.maxEchipeSimultane}</Detail>
        {resource.durataMaximaMin && (
          <Detail label="Durată maximă">{resource.durataMaximaMin / 60} ore / rezervare</Detail>
        )}
        <Detail label="Instruire">{resource.necesitaInstruire ? "Necesară" : "Nu este necesară"}</Detail>
        <Detail label="Program">{data ? formatSchedule(data.schedule) : "…"}</Detail>
      </div>
      <ErrorNote message={error} />
      {loading && !data ? null : (
        <>
          <span className="section-label">Intervale disponibile azi</span>
          {data && data.intervals.length > 0 ? (
            <div className="chips">
              {data.intervals.map((interval) => (
                <span className="chip" key={interval.start}>
                  <Icon name="clock" size={14} />
                  {localTime(interval.start)} – {localTime(interval.end)}
                </span>
              ))}
            </div>
          ) : (
            <p className="row-subtitle">Niciun interval liber azi.</p>
          )}
        </>
      )}
    </div>
  );
}

function ResourceRow({ resource }: { resource: Resource }) {
  const [expanded, setExpanded] = useState(false);
  const bookable = resource.status === "ACTIVE" && resource.disponibilitateCurenta === "LIBERA";

  return (
    <article className="card">
      <div className="row">
        <div className="tile">
          <Icon name={resource.tip === "SALA" ? "room" : "chip"} size={20} />
        </div>
        <div className="row-main">
          <div className="row-title">{resource.nume}</div>
          <div className="row-subtitle">{resourceSummary(resource)}</div>
        </div>
        <ResourceStatusBadge resource={resource} />
        <Link className={bookable ? "btn btn-primary" : "btn"} href={`/resurse/${resource.id}`}>
          {bookable ? "Rezervă" : "Vezi orar"}
        </Link>
        <button
          type="button"
          className="icon-button"
          aria-expanded={expanded}
          aria-label={`Detalii ${resource.nume}`}
          onClick={() => setExpanded((value) => !value)}
        >
          <span className={expanded ? "icon-rotated" : undefined} style={{ display: "flex" }}>
            <Icon name="chevron" />
          </span>
        </button>
      </div>
      {expanded && <ResourceDetails resource={resource} />}
    </article>
  );
}

export function ResourceCatalog({ tip }: { tip: ResourceType }) {
  const copy = COPY[tip];
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<AvailabilityFilter>("");
  const [categoryId, setCategoryId] = useState("");

  const categories = useLoad(() => apiFetch<Category[]>("/categories"), "categories");
  const { data, error, loading } = useLoad(
    () =>
      apiFetch<Page<Resource>>(
        withQuery("/resources", { tip, q, disponibilitate: filter, categoryId, pageSize: 100 }),
      ),
    `${tip}/${q}/${filter}/${categoryId}`,
  );

  const total = data?.total ?? 0;

  return (
    <>
      <PageHeader
        title={copy.title}
        subtitle={copy.subtitle}
        count={data ? `${total} ${total === 1 ? copy.unit[0] : copy.unit[1]}` : undefined}
      />
      <div className="toolbar">
        <SearchBox value={q} onChange={setQ} placeholder={copy.placeholder} />
        <select
          className="select"
          aria-label="Categorie"
          value={categoryId}
          onChange={(event) => setCategoryId(event.target.value)}
        >
          <option value="">Toate categoriile</option>
          {categories.data?.map((category) => (
            <option key={category.id} value={category.id}>
              {category.nume}
            </option>
          ))}
        </select>
        <Tabs
          label="Disponibilitate"
          value={filter}
          onChange={setFilter}
          options={[
            { value: "", label: "Toate" },
            { value: "LIBERA", label: "Libere" },
            { value: "REZERVATA", label: "Rezervate" },
          ]}
        />
      </div>
      <ErrorNote message={error} />
      {loading && !data ? (
        <Loading />
      ) : data && data.items.length > 0 ? (
        <div className="list">
          {data.items.map((resource) => (
            <ResourceRow key={resource.id} resource={resource} />
          ))}
        </div>
      ) : (
        !error && <Empty>Nu am găsit rezultate pentru filtrele alese.</Empty>
      )}
    </>
  );
}
