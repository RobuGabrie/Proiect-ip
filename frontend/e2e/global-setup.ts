import { execFileSync } from "node:child_process";
import path from "node:path";

export default function globalSetup() {
  const backend = path.resolve(__dirname, "../../backend");
  execFileSync(".venv/bin/python", ["scripts/e2e_setup.py", path.resolve(__dirname, ".state.json")], {
    cwd: backend,
    stdio: "inherit",
    env: {
      ...process.env,
      DATABASE_URL: process.env.E2E_DATABASE_URL ?? "postgresql+psycopg://rrm:rrm_dev@localhost:5432/rrm_test",
      GOOGLE_CLIENT_ID: "e2e",
      JWT_SECRET: "e2e-only-secret-with-at-least-32-characters",
    },
  });
}
