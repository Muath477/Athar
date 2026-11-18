import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    locale: "ar-SA",
    trace: "retain-on-failure",
    launchOptions: { executablePath: process.env.E2E_CHROME_PATH },
  },
  projects: [
    { name: "phone", use: { ...devices["Pixel 7"] }, testMatch: /visitor\.spec\.ts/ },
    { name: "desktop", use: { ...devices["Desktop Chrome"] }, testMatch: /dashboard\.spec\.ts/ },
  ],
});
