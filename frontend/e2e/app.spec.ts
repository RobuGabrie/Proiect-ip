import { expect, test } from "@playwright/test";
import { nextWeek, openResource, reserve, signIn, slot } from "./helpers";

test.describe("acces", () => {
  test("vizitatorul este trimis la conectare, cu butonul Google", async ({ page }) => {
    await page.goto("/sali");
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("heading", { name: "Research Resource Manager" })).toBeVisible();
    // Google ascunde butonul pe originile neautorizate, iar portul de test nu este autorizat.
    await expect(page.locator('iframe[src*="accounts.google.com"]')).toHaveCount(1);
    await expect(page.getByLabel(/parol/i)).toHaveCount(0);
  });

  test("un token invalid duce la conectare", async ({ page }) => {
    await page.goto("/status");
    await page.evaluate(() => window.localStorage.setItem("rrm.accessToken", "invalid"));
    await page.goto("/rezervari");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("studentul nu vede paginile de administrare", async ({ page }) => {
    await signIn(page, "student");
    await page.goto("/admin/aprobari");
    await expect(page.getByText("Nu ai acces la această pagină")).toBeVisible();
    await expect(page.getByRole("link", { name: "Aprobări" })).toHaveCount(0);
  });

  test("fiecare rol ajunge pe pagina lui, iar deconectarea funcționează", async ({ page }) => {
    await signIn(page, "student");
    await page.goto("/");
    await expect(page).toHaveURL(/\/sali$/);
    await page.getByRole("button", { name: "Deconectare" }).click();
    await expect(page).toHaveURL(/\/login$/);

    await signIn(page, "roomAdmin");
    await page.goto("/");
    await expect(page).toHaveURL(/\/admin\/aprobari$/);
  });
});

test.describe("catalog", () => {
  test("filtrează și afișează detaliile", async ({ page }) => {
    await signIn(page, "student");
    await page.goto("/sali");
    await expect(page.getByText("5 săli")).toBeVisible();

    await page.getByLabel(/^Caută/).fill("C202");
    await expect(page.getByText("1 sală")).toBeVisible();
    await page.getByRole("button", { name: "Detalii C202" }).click();
    await expect(page.getByText("Luni – Vineri, 08:00 – 22:00")).toBeVisible();
    await expect(page.getByText("Maria Ionescu")).toBeVisible();

    await page.goto("/echipamente");
    await page.getByLabel("Categorie", { exact: true }).selectOption({ label: "Roboți" });
    await expect(page.getByText("1 echipament")).toBeVisible();
    await expect(page.getByText("Robot colaborativ")).toBeVisible();
  });
});

test.describe("fluxul principal", () => {
  test("cerere, aprobare și anulare", async ({ browser }) => {
    const student = await (await browser.newContext()).newPage();
    await signIn(student, "student");
    await openResource(student, "/sali", "B204");
    await nextWeek(student);
    await reserve(student, "Marți", "10:00", "11:30", "Echipa Demo");

    await student.goto("/rezervari");
    const card = student.locator("article", { hasText: "B204" });
    await expect(card.getByText("În așteptare")).toBeVisible();

    const admin = await (await browser.newContext()).newPage();
    await signIn(admin, "roomAdmin");
    await admin.goto("/admin/aprobari");
    const request = admin.locator("article", { hasText: "B204" });
    await expect(request.getByText("Prima rezervare")).toBeVisible();
    await expect(request).toContainText("Echipa Demo");
    await expect(request).toContainText("10:00 – 12:00");
    await request.getByRole("button", { name: "Aprobă" }).click();
    await expect(request.getByText("Aprobată")).toBeVisible();

    await student.reload();
    await expect(card.getByText("Aprobată")).toBeVisible();
    await card.getByRole("button", { name: "Anulează" }).click();
    await student.getByRole("button", { name: "Anulează rezervarea" }).click();
    await expect(card.getByText("Anulată")).toBeVisible();
    await expect(card.getByRole("button", { name: "Anulează" })).toHaveCount(0);
  });

  test("respingerea cere un motiv, iar solicitantul îl vede", async ({ browser }) => {
    const student = await (await browser.newContext()).newPage();
    await signIn(student, "student");
    await openResource(student, "/sali", "D205");
    await nextWeek(student, 2);
    await reserve(student, "Miercuri", "09:00", "09:30", "Echipa Demo");

    const admin = await (await browser.newContext()).newPage();
    await signIn(admin, "roomAdmin");
    await admin.goto("/admin/aprobari");
    await admin.getByLabel(/^Caută/).fill("D205");
    const request = admin.locator("article", { hasText: "D205" }).filter({ hasText: "În așteptare" });
    await request.getByRole("button", { name: "Respinge" }).click();
    await admin.getByLabel("Motiv").fill("Sala este în examen.");
    await admin.getByRole("dialog").getByRole("button", { name: "Respinge" }).click();
    await expect(admin.getByRole("dialog")).toHaveCount(0);

    await student.goto("/rezervari");
    await student.getByRole("button", { name: "Respinse" }).click();
    const card = student.locator("article", { hasText: "D205" }).first();
    await card.getByRole("button", { name: "Detalii" }).click();
    await expect(student.getByText("Sala este în examen.")).toBeVisible();
  });

  test("condiționarea de instruire", async ({ browser }) => {
    const student = await (await browser.newContext()).newPage();
    await signIn(student, "student");
    await openResource(student, "/echipamente", "Osciloscop");
    await nextWeek(student, 3);
    await reserve(student, "Joi", "08:00", "09:00", "Echipa Instruire");

    const admin = await (await browser.newContext()).newPage();
    await signIn(admin, "equipmentAdmin");
    await admin.goto("/admin/aprobari");
    const request = admin.locator("article", { hasText: "Echipa Instruire" });
    await request.getByRole("button", { name: "Detalii" }).click();
    await admin.getByRole("button", { name: "Necesită instruire" }).click();
    await expect(admin.getByRole("button", { name: "Confirmă instruirea" })).toBeVisible();
    await admin.getByRole("button", { name: "Închide" }).click();
    await expect(request.getByRole("button", { name: "Aprobă" })).toBeDisabled();

    await request.getByRole("button", { name: "Detalii" }).click();
    await admin.getByRole("button", { name: "Confirmă instruirea" }).click();
    await expect(admin.getByRole("button", { name: "Confirmă instruirea" })).toHaveCount(0);
    await admin.getByRole("button", { name: "Închide" }).click();
    await request.getByRole("button", { name: "Aprobă" }).click();
    await expect(request.getByText("Aprobată")).toBeVisible();
  });

  test("slotul ocupat oferă lista de așteptare, iar anularea anunță", async ({ browser }) => {
    const first = await (await browser.newContext()).newPage();
    await signIn(first, "student");
    await openResource(first, "/sali", "C102");
    await nextWeek(first, 4);
    await reserve(first, "Vineri", "12:00", "13:00", "Prima Echipă");

    const second = await (await browser.newContext()).newPage();
    await signIn(second, "researcher");
    await openResource(second, "/sali", "C102");
    await nextWeek(second, 4);
    await slot(second, "Vineri", "12:00").click();
    await second.getByRole("button", { name: "Înscrie-mă pe lista de așteptare" }).click();
    await expect(second.getByText("Te-ai înscris pe lista de așteptare")).toBeVisible();

    await second.goto("/lista-asteptare");
    const entry = second.locator("article", { hasText: "C102" });
    await expect(entry.getByText("În așteptare")).toBeVisible();

    await first.goto("/rezervari");
    const card = first.locator("article", { has: first.getByText("C102", { exact: true }) });
    await card.getByRole("button", { name: "Anulează" }).click();
    await first.getByRole("button", { name: "Anulează rezervarea" }).click();
    await expect(card.getByText("Anulată")).toBeVisible();

    await second.reload();
    await expect(entry.getByText("Interval eliberat")).toBeVisible();
    await expect(entry.getByRole("link", { name: "Rezervă" })).toBeVisible();
  });
});

test.describe("administrare", () => {
  test("mentenanța blochează calendarul și marchează rezervările", async ({ browser }) => {
    const student = await (await browser.newContext()).newPage();
    await signIn(student, "student");
    await openResource(student, "/echipamente", "Imprimantă 3D");
    await nextWeek(student, 5);
    await reserve(student, "Luni", "10:00", "11:00", "Echipa Mentenanță");
    const mondayCell = await slot(student, "Luni", "14:00").getAttribute("aria-label");
    expect(mondayCell).toContain("liber");

    const admin = await (await browser.newContext()).newPage();
    await signIn(admin, "equipmentAdmin");
    await admin.goto("/admin/echipamente");
    await admin
      .locator("article", { hasText: "Imprimantă 3D" })
      .getByRole("link", { name: "Program și mentenanță" })
      .click();
    await expect(admin.getByRole("heading", { name: "Mentenanță" })).toBeVisible();

    const monday = await student.evaluate(() => {
      const now = new Date();
      const weekday = (now.getUTCDay() + 6) % 7;
      const date = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate() - weekday + 35));
      return date.toISOString().slice(0, 10);
    });
    await admin.getByLabel("Început, data").fill(monday);
    await admin.getByLabel("Început, ora").fill("10:00");
    await admin.getByLabel("Sfârșit, data").fill(monday);
    await admin.getByLabel("Sfârșit, ora").fill("15:00");
    await admin.getByLabel("Motiv").fill("Schimbare filament");
    await admin.getByRole("button", { name: "Marchează mentenanța" }).click();
    await expect(admin.getByText("1 rezervări sunt marcate pentru reanalizare")).toBeVisible();
    await expect(admin.getByText("Schimbare filament")).toBeVisible();

    await student.reload();
    await nextWeek(student, 5);
    await expect(slot(student, "Luni", "14:00")).toBeDisabled();

    await admin.goto("/admin/aprobari");
    const flagged = admin.locator("article", { hasText: "Echipa Mentenanță" });
    await expect(flagged.getByText("De reanalizat")).toBeVisible();
    await flagged.getByRole("button", { name: "Detalii" }).click();
    await admin.getByRole("button", { name: "Reprogramează" }).click();
    await admin.getByLabel("De la").fill("16:00");
    await admin.getByLabel("Până la").fill("17:00");
    await admin.getByRole("dialog").getByRole("button", { name: "Reprogramează" }).click();
    await expect(admin.getByRole("dialog")).toHaveCount(0);
    await expect(flagged).toContainText("16:00 – 17:00");
    await expect(flagged.getByText("De reanalizat")).toHaveCount(0);
  });

  test("programul modificat apare în calendar", async ({ page }) => {
    await signIn(page, "roomAdmin");
    await page.goto("/admin/sali");
    await page.locator("article", { hasText: "B110" }).getByRole("link", { name: "Program și mentenanță" }).click();
    await page.getByLabel("Ziua intervalului 1").waitFor();
    await page.getByLabel("Închidere interval 1").selectOption("18:00");
    await page.getByRole("button", { name: "Salvează programul" }).click();
    await expect(page.getByText("Programul a fost salvat.")).toBeVisible();

    await page.goto("/admin/sali");
    await page.locator("article", { hasText: "B110" }).getByRole("link", { name: "Calendar" }).click();
    await expect(page.getByText("Luni, 08:00 – 18:00")).toBeVisible();
  });

  test("categorii și resurse noi", async ({ page }) => {
    await signIn(page, "roomAdmin");
    await page.goto("/admin/categorii");
    await page.getByRole("button", { name: "Adaugă categorie" }).click();
    await page.getByLabel("Nume").fill("Plottere");
    await page.getByRole("dialog").getByRole("button", { name: "Salvează" }).click();
    const category = page.locator("article", { hasText: "Plottere" });
    await expect(category).toBeVisible();

    const used = page.locator("article", { hasText: "Roboți" });
    await used.getByRole("button", { name: "Șterge" }).click();
    await expect(page.getByText("Categoria are resurse asociate")).toBeVisible();

    await page.goto("/admin/echipamente");
    await page.getByRole("button", { name: "Adaugă echipament" }).click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Nume").fill("Plotter A0");
    await dialog.getByLabel("Categorie").selectOption({ label: "Plottere" });
    await dialog.getByLabel("Descriere").fill("Printare format mare");
    await dialog.getByRole("button", { name: "Salvează" }).click();
    const created = page.locator("article", { hasText: "Plotter A0" });
    await expect(created).toBeVisible();
    await expect(created.getByRole("button", { name: "Editează" })).toBeVisible();

    await created.getByRole("button", { name: "Dezactivează" }).click();
    await page.getByRole("dialog").getByRole("button", { name: "Dezactivează" }).click();
    await expect(created.getByText("Inactivă")).toBeVisible();
  });

  test("utilizatorii și utilizarea pe echipe", async ({ page }) => {
    await signIn(page, "roomAdmin");
    await page.goto("/admin/utilizatori");
    await page.getByLabel("Rol pentru Radu Tudor").selectOption("CERCETATOR");
    await page.reload();
    await expect(page.getByLabel("Rol pentru Radu Tudor")).toHaveValue("CERCETATOR");

    await page.getByLabel("Rol pentru Maria Ionescu").selectOption("STUDENT");
    await expect(page.getByText("Utilizatorul administrează resurse")).toBeVisible();

    await page.goto("/admin/utilizare");
    await expect(page.getByRole("cell", { name: "Echipa Robotică" })).toBeVisible();
  });

  test("profilul se poate modifica, dar nu și rolul", async ({ page }) => {
    await signIn(page, "researcher");
    await page.goto("/profil");
    await expect(page.getByText("dan.constantin@example.ro")).toBeVisible();
    await expect(page.getByLabel(/parol/i)).toHaveCount(0);
    await page.getByLabel("Prenume").fill("Daniel");
    await page.getByRole("button", { name: "Salvează" }).click();
    await expect(page.getByText("Profilul a fost actualizat.")).toBeVisible();
    await expect(page.getByText("Daniel Constantin")).toBeVisible();
  });
});

test.describe("ecran mic", () => {
  test.use({ viewport: { width: 390, height: 800 } });

  for (const [account, pathname] of [
    ["student", "/sali"],
    ["student", "/rezervari"],
    ["roomAdmin", "/admin/aprobari"],
    ["roomAdmin", "/admin/utilizatori"],
  ] as const) {
    test(`${pathname} nu depășește lățimea ecranului`, async ({ page }) => {
      await signIn(page, account);
      await page.goto(pathname);
      await page.getByRole("heading", { level: 1 }).waitFor();
      await page.waitForTimeout(500);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      expect(overflow).toBeLessThanOrEqual(0);
    });
  }

  test("meniul se deschide", async ({ page }) => {
    await signIn(page, "student");
    await page.goto("/sali");
    await expect(page.getByRole("link", { name: "Rezervări" })).toBeHidden();
    await page.getByRole("button", { name: "Meniu" }).click();
    await page.getByRole("link", { name: "Rezervări" }).click();
    await expect(page).toHaveURL(/\/rezervari$/);
  });
});
