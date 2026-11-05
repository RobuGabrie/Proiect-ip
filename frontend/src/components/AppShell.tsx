"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { homePath, useAuth } from "./AuthProvider";
import { Empty, Icon, Loading } from "./ui";

const USER_MENU = [
  { href: "/sali", label: "Săli", icon: "room" },
  { href: "/echipamente", label: "Echipamente", icon: "chip" },
  { href: "/rezervari", label: "Rezervări", icon: "calendar" },
  { href: "/lista-asteptare", label: "Listă de așteptare", icon: "list" },
] as const;

const ADMIN_MENU = [
  { href: "/admin/aprobari", label: "Aprobări", icon: "check" },
  { href: "/admin/sali", label: "Săli", icon: "room" },
  { href: "/admin/echipamente", label: "Echipamente", icon: "chip" },
  { href: "/admin/categorii", label: "Categorii", icon: "tag" },
  { href: "/admin/utilizare", label: "Utilizare", icon: "chart" },
  { href: "/admin/utilizatori", label: "Utilizatori", icon: "users" },
] as const;

export function AppShell({ children }: { children: ReactNode }) {
  const { user, loading, signOut } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [loading, user, router]);

  if (loading || !user) {
    return (
      <main className="shell-loading">
        <Loading />
      </main>
    );
  }

  const isAdmin = user.role === "ADMIN";
  const menu = isAdmin ? ADMIN_MENU : USER_MENU;
  const adminPage = pathname.startsWith("/admin");
  const blocked = adminPage && !isAdmin;

  return (
    <div className="shell">
      <aside className={menuOpen ? "sidebar sidebar-open" : "sidebar"}>
        <div className="sidebar-top">
          <Link href={homePath(user)} className="brand">
            <span className="brand-logo">R</span>
            <span>
              <small>{isAdmin ? "ADMIN" : "RESEARCH"}</small>
              <strong>Resource Manager</strong>
            </span>
          </Link>
          <button
            type="button"
            className="menu-toggle"
            aria-expanded={menuOpen}
            aria-label="Meniu"
            onClick={() => setMenuOpen((open) => !open)}
          >
            <Icon name="list" />
          </button>
        </div>
        <nav className="sidebar-nav" aria-label="Meniu principal">
          <span className="sidebar-title">{isAdmin ? "ADMINISTRARE" : "MENIU"}</span>
          {menu.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={pathname.startsWith(item.href) ? "nav-link nav-link-active" : "nav-link"}
              aria-current={pathname.startsWith(item.href) ? "page" : undefined}
              onClick={() => setMenuOpen(false)}
            >
              <Icon name={item.icon} />
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <Link
            href="/profil"
            className={pathname.startsWith("/profil") ? "nav-link nav-link-active" : "nav-link"}
            onClick={() => setMenuOpen(false)}
          >
            <Icon name="user" />
            Profil
          </Link>
          <button type="button" className="nav-link" onClick={signOut}>
            <Icon name="logout" />
            Deconectare
          </button>
        </div>
      </aside>
      <main className="content">
        {blocked ? <Empty>Nu ai acces la această pagină. Este disponibilă doar administratorilor.</Empty> : children}
      </main>
    </div>
  );
}
