import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Pagina nu există" };

export default function NotFound() {
  return (
    <main className="center-page">
      <section className="glass center-card">
        <h1>Pagina nu există</h1>
        <p>Adresa este greșită sau pagina a fost mutată.</p>
        <Link className="btn btn-primary" href="/">
          Înapoi la aplicație
        </Link>
      </section>
    </main>
  );
}
