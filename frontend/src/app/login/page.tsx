import type { Metadata } from "next";
import { GoogleSignIn } from "@/components/GoogleSignIn";
import styles from "./page.module.css";

export const metadata: Metadata = {
  title: "Conectare | Research Resource Manager",
};

export default function LoginPage() {
  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <div className={styles.logo} aria-hidden="true">
          R
        </div>
        <h1 className={styles.title}>Conectare</h1>
        <p className={styles.subtitle}>Accesează platforma Research Resource Manager.</p>
        <GoogleSignIn />
      </section>
    </main>
  );
}
