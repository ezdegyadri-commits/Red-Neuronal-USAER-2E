const { chromium } = require(process.env.USAER_PLAYWRIGHT);
const assert = require('node:assert/strict');
const { readFile } = require('node:fs/promises');

async function probar() {
  const [, , url, fase] = process.argv;
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const page = await browser.newPage({ acceptDownloads: true });
    page.setDefaultTimeout(15000);
    await page.goto(url);
    await page.locator('input[type=text]').first().fill('dir');
    await page.locator('input[type=password]').fill(process.env.USAER_TEST_PASSWORD);
    await page.getByRole('button', { name: /Entrar al Sistema/ }).click();
    await page.getByRole('button', { name: /Actas y Oficios/ }).click();
    await page.getByRole('button', { name: /Oficios de Comisi/ }).click();
    if (fase === 'crear') {
      await page.getByRole('button', { name: 'Nuevo oficio de comisión' }).click();
      await page.getByLabel('Fecha de emisión').fill('2026-10-01');
      await page.getByLabel('Fecha de comisión').fill('2026-10-02');
      await page.getByLabel('Escuela destinataria').fill('Escuela ficticia');
      await page.getByLabel('Dirección destinataria').fill('Dirección ficticia');
      await page.getByLabel('Personal comisionado').fill('Docente ficticio');
      await page.getByLabel('Asunto').fill('Comisión sintética');
      await page.getByLabel('Destino o actividad').fill('Taller pedagógico sintético');
      await page.getByLabel('Horario').fill('08:00 a 10:00');
      await page.getByRole('button', { name: 'Guardar oficio' }).click();
      await page.getByText('Oficio guardado.', { exact: true }).waitFor();
      await page.getByLabel('Horario').fill('09:00 a 11:00');
      const actualizado = page.waitForResponse(r => r.request().method() === 'PUT' && r.url().includes('/api/oficios/'));
      await page.getByRole('button', { name: 'Guardar oficio' }).click();
      assert.equal((await actualizado).status(), 200);
      await page.getByText('Oficio guardado.', { exact: true }).waitFor();
    } else {
      await page.getByRole('button', { name: /^Abrir oficio / }).click();
      assert.equal(await page.getByLabel('Horario').inputValue(), '09:00 a 11:00');
    }
    const descarga = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Exportar oficio PDF' }).click();
    const pdf = await descarga;
    assert.equal(pdf.suggestedFilename(), 'Oficio-Comision.pdf');
    assert.equal((await readFile(await pdf.path())).subarray(0, 4).toString(), '%PDF');
    console.log('Edge / oficio: ' + fase + ' y PDF verificados');
  } finally {
    await browser.close();
  }
}

probar().catch(error => { console.error(error); process.exitCode = 1; });
