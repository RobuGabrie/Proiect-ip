import type { Metadata } from "next";
import { GoogleSignIn } from "@/components/GoogleSignIn";
import styles from "./login.module.css";

export const metadata: Metadata = { title: "Conectare" };

export default function LoginPage() {
  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <h1 className={styles.title}>Research Resource Manager</h1>
        <GoogleSignIn />
      </section>
    </main>
  );
}
