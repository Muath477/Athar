import { readFile } from "node:fs/promises";
import path from "node:path";
import { expect, test } from "@playwright/test";

const EXPERT_EMAIL = process.env.E2E_EXPERT_EMAIL ?? "expert@example.org";
const EXPERT_PASSWORD = process.env.E2E_EXPERT_PASSWORD ?? "";
const WALL_PHOTO = path.resolve(__dirname, "../../region-packs/demo/test-photos/north-crack.jpg");

test("an expert maps a wall, approves it and downloads the PDF report", async ({ page }) => {
  test.skip(!EXPERT_PASSWORD, "set E2E_EXPERT_PASSWORD to run the dashboard flow");

  await page.goto("/dashboard/login");
  await page.getByLabel("البريد الإلكتروني").fill(EXPERT_EMAIL);
  await page.getByLabel("كلمة المرور").fill(EXPERT_PASSWORD);
  await page.locator("form button").click();
  await page.waitForURL("**/dashboard");

  await page.goto("/dashboard/maps/new");
  await page.locator("select").first().selectOption({ label: "الواجهة الشمالية" });
  await page.setInputFiles('input[type="file"]', WALL_PHOTO);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(/\/dashboard\/maps\/[0-9a-f-]{36}$/, { timeout: 60_000 });
  await expect(page.getByRole("application", { name: /شبكة التلف/ })).toBeVisible();

  await page.getByRole("button", { name: "اعتمد المخطط" }).click();
  await page.getByRole("button", { name: "اعتمد", exact: true }).click();
  await expect(page.getByRole("button", { name: "اعتمد المخطط" })).toHaveCount(0);

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "حمّل التقرير PDF" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/^athar-wall-report-\d{4}-\d{2}-\d{2}-[0-9a-f]{8}\.pdf$/);
  const pdf = await readFile(await download.path());
  expect(pdf.subarray(0, 5).toString()).toBe("%PDF-");
});
