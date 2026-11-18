import { expect, test } from "@playwright/test";

const AT_TURAIF = { lat: 24.734133, lon: 46.572467 };

test("a visitor opens At-Turaif and gets walking and driving directions", async ({ page, request }) => {
  const nearby = await request.get(`/api/v1/sites/nearby?lat=${AT_TURAIF.lat}&lon=${AT_TURAIF.lon}`);
  expect(nearby.ok()).toBeTruthy();
  const [turaif] = (await nearby.json()) as { id: string; slug: string }[];
  expect(turaif.slug).toBe("at-turaif");

  await page.goto(`/sites/${turaif.id}`);
  await expect(page.getByRole("heading", { level: 1, name: "حي الطريف" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "نموذج الواجهات" })).toHaveCount(0);

  const directions = page.getByRole("link", { name: "افتح الاتجاهات في Google Maps" });
  await expect(directions).toHaveAttribute("href", /destination=24\.734133%2C46\.572467&travelmode=walking/);
  await page.getByText("بالسيارة").click();
  await expect(directions).toHaveAttribute("href", /travelmode=driving/);
  await expect(page.getByText("24.73413, 46.57247")).toBeVisible();
});

test("the home page invites the visitor to photograph a facade", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("صوّر الواجهة");
  await expect(page.getByRole("link", { name: "ابدأ التصوير" })).toBeVisible();
});
