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
  await page.waitForURL("**/dashboard/maps");

  await page.goto("/dashboard/maps/new");
  await page.locator("select").first().selectOption({ label: "الواجهة الشمالية" });
  await page.setInputFiles('input[type="file"]', WALL_PHOTO);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(/\/dashboard\/maps\/[0-9a-f-]{36}$/, { timeout: 60_000 });
  await expect(page.getByRole("heading", { name: "خريطة الإجراءات" })).toBeVisible();
  await expect(page.getByRole("application", { name: /عناصر التلف/ })).toBeVisible();

  await page.getByLabel("نوع التلف من المسرد").selectOption("crack");
  await page.getByRole("button", { name: /ارسم/ }).click();
  const canvas = page.getByRole("application");
  await canvas.evaluate((element) => element.scrollIntoView({ block: "center" }));
  const box = await canvas.boundingBox();
  if (!box) throw new Error("canvas has no size");
  for (const [x, y] of [[0.2, 0.2], [0.22, 0.45], [0.2, 0.7]]) {
    await page.mouse.click(box.x + x * box.width, box.y + y * box.height);
  }
  await page.keyboard.press("Enter");
  await page.getByRole("button", { name: /احفظ التعديلات/ }).click();
  await expect(page.getByText(/^سجل التصحيحات/)).toBeVisible();

  const approve = page.getByRole("button", { name: "اعتمد المخطط والمعالجات" });
  await expect(approve).toBeDisabled();
  await page.getByLabel("ملاحظات الفحص الميداني").fill("فحص من الأرض");
  await page.getByRole("button", { name: "سجّل أني فحصت الجدار ميدانيًا" }).click();
  await approve.click();
  await page.getByRole("button", { name: "اعتمد", exact: true }).click();
  await expect(approve).toHaveCount(0);

  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "حمّل التقرير PDF" }).click(),
  ]);
  expect(download.suggestedFilename()).toMatch(/^athar-wall-report-\d{4}-\d{2}-\d{2}-[0-9a-f]{8}\.pdf$/);
  const pdf = await readFile(await download.path());
  expect(pdf.subarray(0, 5).toString()).toBe("%PDF-");
});

test("an expert screens a Riyadh site from space and asks for a ground check", async ({ page }) => {
  test.skip(!EXPERT_PASSWORD, "set E2E_EXPERT_PASSWORD to run the dashboard flow");

  await page.goto("/dashboard/login");
  await page.getByLabel("البريد الإلكتروني").fill(EXPERT_EMAIL);
  await page.getByLabel("كلمة المرور").fill(EXPERT_PASSWORD);
  await page.locator("form button").click();
  await page.waitForURL("**/dashboard/maps");

  await page.goto("/dashboard/watch");
  await expect(page.getByRole("heading", { name: "رصد محيط المواقع من الفضاء" })).toBeVisible();
  await page.getByRole("link", { name: "قرية أشيقر التراثية" }).first().click();
  await page.getByRole("button", { name: "افحص الآن" }).click();
  await expect(page.getByText("مياه راكدة").first()).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText("بيانات تجريبية", { exact: true })).toBeVisible();

  await page.getByRole("button", { name: "خريطة التغيّر" }).click();
  await expect(page.getByRole("img", { name: /المناطق المتغيرة/ })).toBeVisible();

  await page.getByRole("button", { name: "اطلب تحققًا ميدانيًا" }).click();
  await expect(page.getByRole("status")).toContainText("زيارة مفتش");
  await page.getByRole("button", { name: "أكّد أنك راجعت التنبيه" }).click();
  await expect(page.getByRole("button", { name: "أكّد أنك راجعت التنبيه" })).toHaveCount(0);
});
