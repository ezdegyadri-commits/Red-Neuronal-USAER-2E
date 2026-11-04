const { chromium } = require(process.env.USAER_PLAYWRIGHT);
const assert = require('node:assert/strict');
const { readFile } = require('node:fs/promises');

const [, , base, fase] = process.argv;
const titulo = 'Informe sintético desde expediente';
const avance = 'El alumno recupera información con apoyos visuales.';

async function comprobarInforme() {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const page = await browser.newPage({ acceptDownloads: true });
    page.setDefaultTimeout(15000);
    await page.goto(base);
    await page.locator('input[type=text]').first().fill('a');
    await page.locator('input[type=password]').fill(process.env.USAER_TEST_PASSWORD);
    await page.getByRole('button', { name: /Entrar al Sistema/ }).click();
    await page.getByRole('button', { name: /Alumnos y Expedientes/ }).click();
    await page.getByRole('heading', { name: 'Alumno ficticio A', exact: true }).waitFor();
    await page.getByRole('button', { name: 'Informes del expediente' }).click();
    await page.getByRole('heading', { name: 'Informes educativos' }).waitFor();
    await page.getByRole('combobox').locator('option[value="alu-A"]').waitFor({ state: 'attached' });
    assert.equal(await page.getByRole('combobox').inputValue(), 'alu-A');

    if (fase === 'crear') {
      await page.getByRole('button', { name: 'Nuevo informe' }).click();
      await page.getByLabel('Título').fill(titulo);
      await page.getByLabel('Avances').fill(avance);
      await page.getByRole('button', { name: 'Guardar informe' }).click();
      await page.getByText('Guardado confirmado', { exact: true }).waitFor();
    } else {
      assert.equal(fase, 'recuperar');
      await page.getByRole('button', { name: titulo + ' · 2026-2027', exact: true }).click();
      assert.equal(await page.getByLabel('Avances').inputValue(), avance);
    }

    const descarga = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Exportar PDF' }).click();
    const pdf = await descarga;
    assert.equal(pdf.suggestedFilename(), 'Informe-USAER-2E.pdf');
    assert.equal((await readFile(await pdf.path())).subarray(0, 4).toString(), '%PDF');
    console.log('Navegador Informes: ' + fase + ' y descarga PDF verificadas');
  } finally {
    await browser.close();
  }
}

comprobarInforme().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
