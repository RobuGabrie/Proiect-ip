import { BackendStatus } from "@/components/BackendStatus";
import { CurrentUser } from "@/components/CurrentUser";
import styles from "./page.module.css";

export default function Home() {
  return (
    <main className={styles.main}>
      <h1>Research Resource Manager</h1>
      <BackendStatus />
      <CurrentUser />
    </main>
  );
}
