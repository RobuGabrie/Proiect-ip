"use client";

import { useState } from "react";
import { apiSend, errorMessage, type User } from "@/lib/api";
import { fullName, ROLE_LABELS } from "@/lib/format";
import { useAuth } from "./AuthProvider";
import { Detail, ErrorNote, PageHeader, SuccessNote } from "./ui";

export function ProfilePage() {
  const { user, setUser } = useAuth();
  const [nume, setNume] = useState(user?.nume ?? "");
  const [prenume, setPrenume] = useState(user?.prenume ?? "");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  if (!user) return null;

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      setUser(await apiSend<User>("PATCH", "/users/me", { nume, prenume }));
      setMessage("Profilul a fost actualizat.");
    } catch (cause) {
      setError(errorMessage(cause));
    }
  }

  return (
    <>
      <PageHeader title="Profil" subtitle="Gestionează datele contului." />
      <section className="glass section profile-card">
        <div className="profile-head">
          <div className="profile-name">{fullName(user)}</div>
          <div className="row-subtitle">{user.email}</div>
        </div>
        <SuccessNote message={message} />
        <ErrorNote message={error} />
        <form className="form" onSubmit={save}>
          <div className="form-grid">
            <label className="field">
              Nume
              <input required maxLength={100} value={nume} onChange={(event) => setNume(event.target.value)} />
            </label>
            <label className="field">
              Prenume
              <input required maxLength={100} value={prenume} onChange={(event) => setPrenume(event.target.value)} />
            </label>
            <Detail label="Rol">{ROLE_LABELS[user.role]}</Detail>
            <Detail label="Autentificare">Cont Google instituțional</Detail>
          </div>
          <div className="dialog-actions">
            <button type="submit" className="btn btn-primary">
              Salvează
            </button>
          </div>
        </form>
      </section>
    </>
  );
}
