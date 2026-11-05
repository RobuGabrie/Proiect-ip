import { defineConfig, devices } from "@playwright/test";

const API_PORT = 8100;
const WEB_PORT = 3100;

// Autentificarea Google nu poate fi automatizată: testele folosesc token-uri create de backend/scripts/e2e_setup.py.
const backendEnv = {
  DATABASE_URL: process.env.E2E_DATABASE_URL ?? "postgresql+psycopg://rrm:rrm_dev@localhost:5432/rrm_test",
  CORS_ORIGINS: `http://localhost:${WEB_PORT}`,
  GOOGLE_CLIENT_ID: "57335626323-6lac5g6c3r0d029midppknls33lv0hmi.apps.googleusercontent.com",
  JWT_SECRET: "e2e-only-secret-with-at-least-32-characters",
};

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  globalSetup: "./e2e/global-setup.ts",
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    trace: "retain-on-failure",
    ...devices["Desktop Chrome"],
  },
  webServer: [
    {
      command: `.venv/bin/uvicorn app.main:app --port ${API_PORT}`,
      cwd: "../backend",
      env: backendEnv,
      url: `http://localhost:${API_PORT}/health`,
      reuseExistingServer: false,
    },
    {
      command: `npx next dev -p ${WEB_PORT}`,
      env: {
        NEXT_PUBLIC_API_URL: `http://localhost:${API_PORT}`,
        NEXT_PUBLIC_GOOGLE_CLIENT_ID: backendEnv.GOOGLE_CLIENT_ID,
      },
      url: `http://localhost:${WEB_PORT}/login`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
