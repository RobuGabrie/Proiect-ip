"use client";

import { useState } from "react";
import { apiFetch, apiSend, errorMessage, type Category } from "@/lib/api";
import { useLoad } from "@/lib/useLoad";
import { Dialog, Empty, ErrorNote, Icon, Loading, PageHeader } from "./ui";

function CategoryDialog({
  category,
  onClose,
  onSaved,
}: {
  category: Category | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [nume, setNume] = useState(category?.nume ?? "");
  const [descriere, setDescriere] = useState(category?.descriere ?? "");
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const payload = { nume, descriere: descriere || null };
    try {
      if (category) {
        await apiSend("PUT", `/categories/${category.id}`, payload);
      } else {
        await apiSend("POST", "/categories", payload);
      }
      onSaved();
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  return (
    <Dialog title={category ? `Editează ${category.nume}` : "Adaugă categorie"} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <ErrorNote message={error} />
        <label className="field">
          Nume
          <input required maxLength={100} value={nume} onChange={(event) => setNume(event.target.value)} />
        </label>
        <label className="field">
          Descriere
          <textarea rows={3} value={descriere} onChange={(event) => setDescriere(event.target.value)} />
        </label>
        <div className="dialog-actions">
          <button type="button" className="btn" onClick={onClose}>
            Renunță
          </button>
          <button type="submit" className="btn btn-primary">
            Salvează
          </button>
        </div>
      </form>
    </Dialog>
  );
}

export function CategoriesPage() {
  const { data, error, loading, reload } = useLoad(() => apiFetch<Category[]>("/categories"), "categories");
  const [editing, setEditing] = useState<Category | "new" | null>(null);
  const [actionError, setActionError] = useState("");

  async function remove(category: Category) {
    setActionError("");
    try {
      await apiSend("DELETE", `/categories/${category.id}`);
      reload();
    } catch (cause) {
      setActionError(errorMessage(cause));
    }
  }

  return (
    <>
      <PageHeader
        title="Categorii"
        subtitle="Organizează resursele pe categorii."
        count={data ? `${data.length} categorii` : undefined}
        action={
          <button type="button" className="btn btn-primary" onClick={() => setEditing("new")}>
            Adaugă categorie
          </button>
        }
      />
      <ErrorNote message={error || actionError} />
      {loading && !data ? (
        <Loading />
      ) : data && data.length > 0 ? (
        <div className="list">
          {data.map((category) => (
            <article className="card row" key={category.id}>
              <div className="tile">
                <Icon name="tag" size={20} />
              </div>
              <div className="row-main">
                <div className="row-title">{category.nume}</div>
                {category.descriere && <div className="row-subtitle">{category.descriere}</div>}
              </div>
              <div className="row-actions">
                <button type="button" className="btn" onClick={() => setEditing(category)}>
                  Editează
                </button>
                <button type="button" className="btn btn-danger" onClick={() => remove(category)}>
                  Șterge
                </button>
              </div>
            </article>
          ))}
        </div>
      ) : (
        !error && <Empty>Nu există categorii. Adaugă prima categorie.</Empty>
      )}
      {editing && (
        <CategoryDialog
          category={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            reload();
          }}
        />
      )}
    </>
  );
}
