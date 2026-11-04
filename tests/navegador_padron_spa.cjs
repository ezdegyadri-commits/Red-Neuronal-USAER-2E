const { chromium } = require(process.env.USAER_PLAYWRIGHT);
const assert = require('node:assert/strict');

async function verificar() {
  const [, , base, fase] = process.argv;
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const page = await browser.newPage({ acceptDownloads: true });
    page.on('pageerror', error => console.error('React:', error.message));
    page.on('response', response => {
      if (response.status() >= 400 && response.url().includes('/api/') &&
          !(response.status() === 401 && new URL(response.url()).pathname === '/api/me')) {
        console.error('Respuesta inesperada:', response.status(), new URL(response.url()).pathname);
      }
    });
    page.setDefaultTimeout(15000);
    await page.goto(base);
    await page.locator('input[type=text]').first().fill(fase === 'destino' ? 'b' : 'a');
    await page.locator('input[type=password]').fill(process.env.USAER_TEST_PASSWORD);
    await page.getByRole('button', { name: /Entrar al Sistema/ }).click();
    await page.getByRole('button', { name: /Alumnos y Expedientes/ }).click();
    await page.getByText('Alumno sintético de movimientos', { exact: true }).first().click();
    await page.getByRole('button', { name: 'Abrir ficha del padrón' }).click();
    const nombre = page.getByLabel('Nombre completo', { exact: true });
    await nombre.waitFor();
    if (fase === 'origen') {
      await page.getByLabel('Edad al 1 de septiembre').fill('11');
      await page.getByRole('button', { name: 'Guardar ficha nominal' }).click();
      await page.getByText('Cambios guardados en el padrón.').waitFor();
    } else {
      assert.equal(await page.getByLabel('Edad al 1 de septiembre').inputValue(), '11');
      await page.getByRole('button', { name: 'Ver historial del padrón' }).click();
      await page.getByText('traslado', { exact: true }).waitFor();
      const descarga = page.waitForEvent('download');
      await page.getByRole('button', { name: 'Exportar Padrón Excel' }).click();
      assert.equal((await descarga).suggestedFilename(), 'Padron_USAER_2E.xlsx');
    }
    await page.getByRole('button', { name: 'Evaluación Psicopedagógica (EPP)' }).click();
    await page.getByText('Anexo XVII · Evaluación interdisciplinaria', { exact: true }).click();
    await page.getByRole('button', { name: 'Abrir ciclo' }).click();
    await page.getByText('Aplicar instrumento digital', { exact: true }).click();
    await page.getByRole('combobox', { name: /^Protocolo/ }).selectOption('XIV');
    if (fase === 'origen') {
      await page.getByLabel('Fecha de aplicación del protocolo').fill('2026-10-20');
      await page.getByLabel('Observaciones 1', { exact: true }).fill('Observación sintética del protocolo.');
      await page.getByRole('button', { name: 'Guardar borrador de aplicación' }).click();
      await page.getByText(/Borrador confirmado/).waitFor();
      await page.getByText('Revisé las respuestas y corresponden a este expediente').click();
      await page.getByRole('button', { name: 'Incorporar resultados al informe' }).click();
      await page.getByText(/Resultados incorporados/).waitFor();
    } else {
      assert.equal(await page.getByLabel('Observaciones 1', { exact: true }).inputValue(), 'Observación sintética del protocolo.');
      const descarga = page.waitForEvent('download');
      await page.getByRole('button', { name: 'Exportar Anexo XVII' }).click();
      assert.equal((await descarga).suggestedFilename(), 'EPP-Anexo-XVII.pdf');
    }
    const externa = page.getByText('Vincular evaluación externa', { exact: true });
    await externa.click();
    await page.getByRole('combobox', { name: /^PDF del expediente/ }).selectOption({ label: 'evaluacion-sintetica.pdf' });
    if (fase === 'origen') {
      await page.getByLabel('Instrumento externo').fill('Registro sintético de desempeño');
      await page.getByLabel('Fecha de evaluación externa').fill('2026-10-20');
      for (const texto of ['Hallazgo sintético inicial.', 'Hallazgo sintético actualizado.']) {
        await page.getByLabel('Resultados externos cotejados').fill(texto);
        await page.getByText('Verifiqué que el original y los resultados corresponden al alumno').click();
        const guardado = page.waitForResponse(r => r.request().method() === 'PUT' && r.url().includes('/externa/'));
        await page.getByRole('button', { name: 'Guardar evaluación externa' }).click();
        assert.equal((await guardado).status(), 200);
        await page.getByText('Evaluación externa guardada.', { exact: true }).waitFor();
      }
    } else {
      assert.equal(await page.getByLabel('Resultados externos cotejados').inputValue(), 'Hallazgo sintético actualizado.');
      const descarga = page.waitForEvent('download');
      await page.getByRole('button', { name: 'Descargar original' }).click();
      assert.equal((await descarga).suggestedFilename(), 'evaluacion-sintetica.pdf');
      await page.getByRole('button', { name: 'Seguimiento', exact: true }).click();
      await page.getByText('Comparar EPP por ciclo', { exact: true }).click();
      await page.getByRole('row').filter({ hasText: '2025-2026' }).waitFor();
      await page.getByRole('row').filter({ hasText: '2026-2027' }).waitFor();
    }
    console.log('Edge / padrón nominal: ' + fase + ' verificado');
  } finally {
    await browser.close();
  }
}

verificar().catch(error => { console.error(error); process.exitCode = 1; });
