import { test } from "@playwright/test";
import path from "node:path";
import { signIn } from "./helpers";

const OUT = process.env.SCREENSHOT_DIR;

test.describe("capturi", () => {
  test.skip(!OUT, "SCREENSHOT_DIR lipsește");

  for (const [account, pathname, name] of [
    ["student", "/sali", "sali"],
    ["student", "/rezervari", "rezervari"],
    ["roomAdmin", "/admin/aprobari", "aprobari"],
    ["roomAdmin", "/admin/sali", "admin-sali"],
  ] as const) {
    test(name, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 1024 });
      await signIn(page, account);
      await page.goto(pathname);
      await page.getByRole("heading", { level: 1 }).waitFor();
      await page.waitForTimeout(800);
      await page.screenshot({ path: path.join(OUT!, `${name}.png`) });
    });
  }

  test("calendar", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1200 });
    await signIn(page, "student");
    await page.goto("/sali");
    await page.locator("article", { hasText: "C202" }).getByRole("link").click();
    await page.locator("table.calendar").waitFor();
    await page.getByRole("button", { name: "Săptămâna următoare" }).click();
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(OUT!, "calendar.png") });
  });

  test("selecție și dialog", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1100 });
    await signIn(page, "student");
    await page.goto("/sali");
    await page.locator("article", { hasText: "D205" }).getByRole("link").click();
    await page.getByRole("button", { name: "Săptămâna următoare" }).click();
    await page.getByRole("button", { name: /^Miercuri 10:00, / }).click();
    await page.getByRole("button", { name: /^Miercuri 12:00, / }).click();
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(OUT!, "selectie.png") });
    await page.getByRole("button", { name: "Continuă" }).click();
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(OUT!, "dialog.png") });
  });

  test("detalii în catalog", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await signIn(page, "student");
    await page.goto("/echipamente");
    await page.getByRole("button", { name: "Detalii Robot colaborativ" }).click();
    await page.waitForTimeout(600);
    await page.screenshot({ path: path.join(OUT!, "detalii.png") });
  });

  test("mobil", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 800 });
    await signIn(page, "roomAdmin");
    await page.goto("/admin/aprobari");
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(OUT!, "mobil.png") });
  });
});
