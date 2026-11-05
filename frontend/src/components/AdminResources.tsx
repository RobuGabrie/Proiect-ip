"use client";

import Link from "next/link";
import { useState } from "react";
import {
  apiFetch,
  apiSend,
  errorMessage,
  withQuery,
  type Category,
  type Page,
  type Resource,
  type ResourceInput,
  type ResourceType,
  type User,
} from "@/lib/api";
import { fullName, resourceSummary } from "@/lib/format";
import { useLoad } from "@/lib/useLoad";
import { useAuth } from "./AuthProvider";
import { ResourceStatusBadge } from "./ResourceCatalog";
import { Dialog, Empty, ErrorNote, Icon, Loading, PageHeader, SearchBox } from "./ui";

const COPY: Record<ResourceType, { title: string; subtitle: string; add: string; unit: [string, string] }> = {
  SALA: {
    title: "Săli",
    subtitle: "Gestionează sălile disponibile pentru rezervare.",
    add: "Adaugă sală",
    unit: ["sală", "săli"],
  },
  ECHIPAMENT: {
    title: "Echipamente",
    subtitle: "Gestionează echipamentele de cercetare.",
    add: "Adaugă echipament",
    unit: ["echipament", "echipamente"],
  },
};

function numberOrNull(value: string): number | null {
  return value === "" ? null : Number(value);
}

function ResourceForm({
  tip,
  resource,
  onClose,
  onSaved,
}: {
  tip: ResourceType;
  resource: Resource | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { user } = useAuth();
  const categories = useLoad(() => apiFetch<Category[]>("/categories"), "categories");
  const admins = useLoad(() => apiFetch<Page<User>>(withQuery("/users", { role: "ADMIN", pageSize: 100 })), "admins");

  const [categoryId, setCategoryId] = useState(resource ? String(resource.category.id) : "");
  const [nume, setNume] = useState(resource?.nume ?? "");
  const [descriere, setDescriere] = useState(resource?.descriere ?? "");
  const [locatie, setLocatie] = useState(resource?.locatie ?? "");
  const [etaj, setEtaj] = useState(resource?.etaj?.toString() ?? "");
  const [locuri, setLocuri] = useState(resource?.locuri?.toString() ?? "");
  const [echipare, setEchipare] = useState(resource?.echipare ?? "");
  const [model, setModel] = useState(resource?.model ?? "");
  const [maxEchipe, setMaxEchipe] = useState(String(resource?.maxEchipeSimultane ?? 1));
  const [durata, setDurata] = useState(resource?.durataMaximaMin?.toString() ?? "");
  const [instruire, setInstruire] = useState(resource?.necesitaInstruire ?? false);
  const [activa, setActiva] = useState(resource ? resource.status !== "INACTIVE" : true);
  const [adminIds, setAdminIds] = useState<number[]>(
    resource ? resource.administratori.map((admin) => admin.id) : user ? [user.id] : [],
  );
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    const payload: ResourceInput = {
      categoryId: Number(categoryId),
      tip,
      nume,
      descriere: descriere || null,
      locatie: locatie || null,
      etaj: numberOrNull(etaj),
      locuri: numberOrNull(locuri),
      echipare: echipare || null,
      model: model || null,
      maxEchipeSimultane: Number(maxEchipe),
      durataMaximaMin: numberOrNull(durata),
      necesitaInstruire: instruire,
      status: activa ? "ACTIVE" : "INACTIVE",
      adminIds,
    };
    try {
      if (resource) {
        await apiSend("PUT", `/resources/${resource.id}`, payload);
      } else {
        await apiSend("POST", "/resources", payload);
      }
      onSaved();
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  return (
    <Dialog title={resource ? `Editează ${resource.nume}` : COPY[tip].add} onClose={onClose} wide>
      <form className="form" onSubmit={submit}>
        <ErrorNote message={error} />
        <div className="form-grid">
          <label className="field">
            Nume
            <input required maxLength={150} value={nume} onChange={(event) => setNume(event.target.value)} />
          </label>
          <label className="field">
            Categorie
            <select required value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
              <option value="">Alege…</option>
              {categories.data?.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.nume}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            Descriere
            <input value={descriere} onChange={(event) => setDescriere(event.target.value)} />
          </label>
          <label className="field">
            Locație
            <input maxLength={150} value={locatie} onChange={(event) => setLocatie(event.target.value)} />
          </label>
          {tip === "SALA" ? (
            <>
              <label className="field">
                Etaj
                <input type="number" value={etaj} onChange={(event) => setEtaj(event.target.value)} />
              </label>
              <label className="field">
                Locuri
                <input type="number" min={1} value={locuri} onChange={(event) => setLocuri(event.target.value)} />
              </label>
              <label className="field">
                Echipare
                <input value={echipare} onChange={(event) => setEchipare(event.target.value)} />
              </label>
            </>
          ) : (
            <label className="field">
              Model
              <input maxLength={150} value={model} onChange={(event) => setModel(event.target.value)} />
            </label>
          )}
          <label className="field">
            Echipe simultan
            <select value={maxEchipe} onChange={(event) => setMaxEchipe(event.target.value)}>
              <option value="1">1</option>
              <option value="2">2</option>
            </select>
          </label>
          <label className="field">
            Durată maximă (minute)
            <input
              type="number"
              min={30}
              step={30}
              placeholder="Fără limită"
              value={durata}
              onChange={(event) => setDurata(event.target.value)}
            />
          </label>
          <fieldset className="field" style={{ border: 0, padding: 0, margin: 0 }}>
            <legend style={{ marginBottom: 5 }}>Administratori</legend>
            {admins.data?.items.map((admin) => (
              <label className="checkbox" key={admin.id}>
                <input
                  type="checkbox"
                  checked={adminIds.includes(admin.id)}
                  onChange={(event) =>
                    setAdminIds((current) =>
                      event.target.checked ? [...current, admin.id] : current.filter((id) => id !== admin.id),
                    )
                  }
                />
                {fullName(admin)}
              </label>
            ))}
          </fieldset>
        </div>
        <label className="checkbox">
          <input type="checkbox" checked={instruire} onChange={(event) => setInstruire(event.target.checked)} />
          Necesită instruire înainte de folosire
        </label>
        <label className="checkbox">
          <input type="checkbox" checked={activa} onChange={(event) => setActiva(event.target.checked)} />
          Activă (poate fi rezervată)
        </label>
        <div className="dialog-actions">
          <button type="button" className="btn" onClick={onClose}>
            Renunță
          </button>
          <button type="submit" className="btn btn-primary" disabled={adminIds.length === 0}>
            Salvează
          </button>
        </div>
      </form>
    </Dialog>
  );
}

export function AdminResources({ tip }: { tip: ResourceType }) {
  const copy = COPY[tip];
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [editing, setEditing] = useState<Resource | "new" | null>(null);
  const [removing, setRemoving] = useState<Resource | null>(null);
  const [actionError, setActionError] = useState("");

  const { data, error, loading, reload } = useLoad(
    () => apiFetch<Page<Resource>>(withQuery("/resources", { tip, q, pageSize: 100 })),
    `${tip}/${q}`,
  );

  async function deactivate(resource: Resource) {
    setActionError("");
    try {
      await apiSend("DELETE", `/resources/${resource.id}`);
      setRemoving(null);
      reload();
    } catch (cause) {
      setRemoving(null);
      setActionError(errorMessage(cause));
    }
  }

  const total = data?.total ?? 0;

  return (
    <>
      <PageHeader
        title={copy.title}
        subtitle={copy.subtitle}
        count={data ? `${total} ${total === 1 ? copy.unit[0] : copy.unit[1]}` : undefined}
        action={
          <button type="button" className="btn btn-primary" onClick={() => setEditing("new")}>
            {copy.add}
          </button>
        }
      />
      <div className="toolbar">
        <SearchBox value={q} onChange={setQ} placeholder="Caută după nume, categorie sau locație…" />
      </div>
      <ErrorNote message={error || actionError} />
      {loading && !data ? (
        <Loading />
      ) : data && data.items.length > 0 ? (
        <div className="list">
          {data.items.map((resource) => {
            const mine = resource.administratori.some((admin) => admin.id === user?.id);
            return (
              <article className="card row" key={resource.id}>
                <div className="tile">
                  <Icon name={tip === "SALA" ? "room" : "chip"} size={20} />
                </div>
                <div className="row-main">
                  <div className="row-title">{resource.nume}</div>
                  <div className="row-subtitle">{resourceSummary(resource)}</div>
                </div>
                <ResourceStatusBadge resource={resource} />
                <div className="row-actions">
                  <Link className="btn" href={`/resurse/${resource.id}`}>
                    Calendar
                  </Link>
                  {mine ? (
                    <>
                      <Link className="btn" href={`/admin/resurse/${resource.id}`}>
                        Program și mentenanță
                      </Link>
                      <button type="button" className="btn" onClick={() => setEditing(resource)}>
                        Editează
                      </button>
                      {resource.status !== "INACTIVE" && (
                        <button type="button" className="btn btn-danger" onClick={() => setRemoving(resource)}>
                          Dezactivează
                        </button>
                      )}
                    </>
                  ) : (
                    <span className="row-subtitle">Administrată de alt responsabil</span>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        !error && <Empty>Nu există resurse pentru căutarea aleasă.</Empty>
      )}
      {editing && (
        <ResourceForm
          tip={tip}
          resource={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
        />
      )}
      {removing && (
        <Dialog title={`Dezactivezi ${removing.nume}?`} onClose={() => setRemoving(null)}>
          <div className="form">
            <p>Resursa nu va mai putea fi rezervată, iar istoricul rezervărilor rămâne păstrat.</p>
            <div className="dialog-actions">
              <button type="button" className="btn" onClick={() => setRemoving(null)}>
                Renunță
              </button>
              <button type="button" className="btn btn-danger" onClick={() => deactivate(removing)}>
                Dezactivează
              </button>
            </div>
          </div>
        </Dialog>
      )}
    </>
  );
}
