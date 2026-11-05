import { readFileSync } from "node:fs";
import path from "node:path";
import { expect, type Page } from "@playwright/test";

type Account = "student" | "researcher" | "roomAdmin" | "equipmentAdmin";

export async function signIn(page: Page, account: Account) {
  const tokens = JSON.parse(readFileSync(path.resolve(__dirname, ".state.json"), "utf-8"));
  await page.goto("/status");
  await page.evaluate((token) => window.localStorage.setItem("rrm.accessToken", token), tokens[account]);
}

export async function openResource(page: Page, section: "/sali" | "/echipamente", name: string) {
  await page.goto(section);
  const row = page.locator("article", { has: page.getByText(name, { exact: true }) });
  await row.getByRole("link", { name: /Rezervă|Vezi orar/ }).click();
  await expect(page.getByRole("heading", { level: 1, name })).toBeVisible();
}

/** Săptămâna următoare este liberă în datele de test doar acolo unde testul o rezervă explicit. */
export async function nextWeek(page: Page, weeks = 1) {
  for (let index = 0; index < weeks; index += 1) {
    await page.getByRole("button", { name: "Săptămâna următoare" }).click();
  }
  await expect(page.locator("table.calendar")).toBeVisible();
}

export function slot(page: Page, day: string, time: string) {
  return page.getByRole("button", { name: new RegExp(`^${day} ${time}, `) });
}

export async function reserve(page: Page, day: string, from: string, to: string, team: string) {
  await slot(page, day, from).click();
  await slot(page, day, to).click();
  await page.getByRole("button", { name: "Continuă" }).click();
  await page.getByLabel("Echipa").fill(team);
  await page.getByRole("button", { name: "Trimite cererea" }).click();
  await expect(page.getByText("Cererea a fost trimisă spre aprobare.")).toBeVisible();
}
