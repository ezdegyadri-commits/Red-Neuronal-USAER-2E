const { chromium } = require("playwright");

async function probar() {
  const url = new URL(process.argv[2]);
  if (url.hostname !== "127.0.0.1") throw new Error("El ensayo solo admite loopback");
  const fase = process.argv[3];
  const browser = await chromium.launch({ channel: "msedge", headless: true });
  try {
    const page = await browser.newPage({ acceptDownloads: true });
    page.setDefaultTimeout(12000);
    await page.route("**/*", route => new URL(route.request().url()).origin === url.origin
      ? route.continue() : route.abort());
    await page.goto(url.href);
    await page.locator("input[type=text]").first().fill("maestra.historia");
    await page.locator("input[type=password]").fill(process.env.USAER_DOCUMENTAL_PASSWORD);
    await page.getByRole("button", { name: /Entrar al Sistema/ }).click();
    const editado = "Plan histórico editado desde React";
    await page.getByText(fase === "editar" ? "Plan histórico individual" : editado, { exact: true }).first().click();
    const titulo = page.getByPlaceholder("Título del Plan de Intervención");
    await titulo.waitFor();
    if (fase === "editar") {
      await titulo.fill(editado);
      await page.getByText("Guardado confirmado", { exact: true }).waitFor();
    } else if (await titulo.inputValue() !== editado) {
      throw new Error("La edición de React no sobrevivió al reinicio del servidor");
    }
    console.log("React sobre PostgreSQL: " + fase + " de la planeación histórica confirmado.");
  } finally {
    await browser.close();
  }
}

probar().catch(error => { console.error(error); process.exitCode = 1; });
