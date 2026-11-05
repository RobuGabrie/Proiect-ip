"use client";

import { useState } from "react";
import { apiFetch, apiSend, errorMessage, withQuery, type Page, type Role, type User } from "@/lib/api";
import { fullName, ROLE_LABELS } from "@/lib/format";
import { useLoad } from "@/lib/useLoad";
import { useAuth } from "./AuthProvider";
import { Empty, ErrorNote, Loading, PageHeader, SearchBox } from "./ui";

export function UsersPage() {
  const { user: currentUser, refresh } = useAuth();
  const [q, setQ] = useState("");
  const [actionError, setActionError] = useState("");
  const { data, error, loading, reload } = useLoad(
    () => apiFetch<Page<User>>(withQuery("/users", { q, pageSize: 100 })),
    q,
  );

  async function changeRole(user: User, role: Role) {
    setActionError("");
    try {
      await apiSend("PUT", `/users/${user.id}/role`, { role });
      if (user.id === currentUser?.id) await refresh();
    } catch (cause) {
      setActionError(errorMessage(cause));
    }
    reload();
  }

  return (
    <>
      <PageHeader
        title="Utilizatori"
        subtitle="Conturile apar aici după prima conectare cu Google."
        count={data ? `${data.total} utilizatori` : undefined}
      />
      <div className="toolbar">
        <SearchBox value={q} onChange={setQ} placeholder="Caută după nume sau email…" />
      </div>
      <ErrorNote message={error || actionError} />
      {loading && !data ? (
        <Loading />
      ) : data && data.items.length > 0 ? (
        <div className="glass table-wrap">
          <table className="table">
            <thead>
              <tr>
                <th scope="col">Nume</th>
                <th scope="col">Email</th>
                <th scope="col">Rol</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((user) => (
                <tr key={user.id}>
                  <td>{fullName(user)}</td>
                  <td>{user.email}</td>
                  <td>
                    <select
                      className="select table-select"
                      aria-label={`Rol pentru ${fullName(user)}`}
                      value={user.role}
                      onChange={(event) => changeRole(user, event.target.value as Role)}
                    >
                      {(Object.keys(ROLE_LABELS) as Role[]).map((role) => (
                        <option key={role} value={role}>
                          {ROLE_LABELS[role]}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        !error && <Empty>Nu am găsit utilizatori.</Empty>
      )}
    </>
  );
}
