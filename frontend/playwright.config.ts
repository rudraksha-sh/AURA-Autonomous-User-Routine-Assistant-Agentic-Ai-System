import { defineConfig } from "@playwright/test";

const frontend = "http://127.0.0.1:3100";
const backend = "http://127.0.0.1:8100";

export default defineConfig({
  testDir: "./e2e",
  workers: 1,
  use: {
    baseURL: frontend,
    channel: process.env.PLAYWRIGHT_CHROMIUM_CHANNEL || undefined,
  },
  webServer: [
    {
      command: process.env.AURA_E2E_PYTHON_COMMAND || "python e2e/backend.py",
      url: backend,
      reuseExistingServer: false,
    },
    {
      command: "npm run build && npm run start -- --hostname 127.0.0.1 --port 3100",
      env: { AURA_E2E_BUILD: "1", AURA_API_SERVER_URL: backend, NEXT_TELEMETRY_DISABLED: "1" },
      url: frontend,
      timeout: 180_000,
      reuseExistingServer: false,
    },
  ],
});
