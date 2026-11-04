const { chromium } = require(process.env.USAER_PLAYWRIGHT);
const assert = require('node:assert/strict');
const [,, base, password, grupoId, individualId, modo] = process.argv;
(async () => {
  const browser = await chromium.launch({ channel: 'msedge', headless: true });
  try {
    const contexto = await browser.newContext({ viewport: { width: 1440, height: 950 } });
    let page = await contexto.newPage();
    page.setDefaultTimeout(16000);
    page.on('pageerror', e => console.error('React:', e.message));
    const cdp = await page.context().newCDPSession(page);
    await cdp.send('Network.enable');
    await cdp.send('Network.emulateNetworkConditions', {
      offline: false, latency: 180, downloadThroughput: 180000, uploadThroughput: 80000
    });
    await page.goto(base, { waitUntil: 'domcontentloaded', timeout: 35000 });
    await page.locator('input[type=text]').first().fill(modo === 'editar' ? 'psi' : 'a');
    await page.locator('input[type=password]').fill(password);
    await page.getByRole('button', { name: /Entrar al Sistema/ }).click();
    const grupo = page.getByText('Revisión persistente A', { exact: true });
    await grupo.waitFor();
    const inicio = performance.now();
    await grupo.click();
    const fila = page.locator('fieldset').filter({ has: page.locator('legend').getByText('Alumno ficticio A', { exact: true }) });
    const psicologia = fila.getByRole('textbox', { name: 'Psicología', exact: true });
    await psicologia.waitFor();
    console.log('Apertura de guía, red simulada: ' + Math.round(performance.now() - inicio) + ' ms');
    const apoyo = fila.getByRole('textbox', { name: 'Aprendizaje', exact: true });
    assert.equal(await apoyo.inputValue(), 'Aporte pedagógico de apoyo');
    if (modo === 'editar') {
      assert.equal(await apoyo.getAttribute('readonly'), '');
      const frase = 'Frase sintética de recuperación 09';
      const texto = 'Aporte Psicología desde React';
      const abrirBoveda = async (pagina, secreto) => {
        await pagina.getByText('Recuperación de borradores en este navegador', { exact: true }).click();
        await pagina.getByLabel('Frase de recuperación').fill(secreto);
        await pagina.getByRole('button', { name: 'Abrir bóveda' }).click();
      };
      await abrirBoveda(page, frase);
      await page.getByText(/Bóveda abierta/).waitFor();

      await contexto.setOffline(true);
      const guardado = performance.now();
      await psicologia.fill(texto);
      await page.getByText('Copia cifrada disponible', { exact: true }).waitFor();
      assert.equal(await page.getByText('Aporte guardado', { exact: true }).count(), 0);
      const almacenamiento = await page.evaluate(() => JSON.stringify(Object.entries(localStorage)));
      assert.ok(almacenamiento.includes('cifrado'));
      assert.ok(!almacenamiento.includes(texto) && !almacenamiento.includes(frase));
      await page.close({ runBeforeUnload: false });
      await contexto.clearCookies();
      await contexto.setOffline(false);
      page = await contexto.newPage();
      await page.goto(base, { waitUntil: 'domcontentloaded' });
      await page.locator('input[type=text]').first().fill('psi');
      await page.locator('input[type=password]').fill(password);
      await page.getByRole('button', { name: /Entrar al Sistema/ }).click();
      await page.getByText('Revisión persistente A', { exact: true }).click();
      await abrirBoveda(page, 'Una frase incorrecta totalmente distinta');
      await page.getByText('La frase no abre esta bóveda.', { exact: true }).waitFor();
      await page.getByLabel('Frase de recuperación').fill(frase);
      await page.getByRole('button', { name: 'Abrir bóveda' }).click();
      await page.getByText('Aporte guardado', { exact: true }).waitFor();
      const estado = await page.evaluate(async id => (await fetch('/api/planeaciones/' + id)).json(), grupoId);
      assert.equal(estado.metadatos.guia_grupal_manual.filas.find(f => f.ID_Alumno === 'alu-A')['Psicología'], texto);
      await page.waitForFunction(() => Object.keys(localStorage).filter(k => k.startsWith('usaer-boveda-v1-') && k.includes(':')).length === 0);
      console.log('Recuperación y guardado después del cierre y pérdida de sesión: ' + Math.round(performance.now() - guardado) + ' ms');
      await page.getByRole('button', { name: 'Salir' }).click();
      await page.getByRole('button', { name: /Entrar al Sistema/ }).waitFor();
    } else {
      assert.equal(await psicologia.inputValue(), 'Aporte Psicología desde React');
      await page.getByRole('button', { name: /Volver a Mis Documentos/ }).click();
      await page.getByText('Planeación individual · 2026-2027', { exact: true }).click();
      await page.getByRole('button', { name: 'Propuestas pedagógicas' }).click();
      const nee = page.getByLabel('NEE confirmada', { exact: true });
      await nee.selectOption({ label: 'Necesita identificar ideas principales en textos breves' });
      const pda = page.getByLabel('PDA del catálogo', { exact: true });
      await pda.locator('option').nth(1).waitFor({ state: 'attached' });
      await pda.selectOption({ index: 1 });
      const [propuesta] = await Promise.all([
        page.waitForResponse(r => r.url().endsWith('/propuesta') && r.request().method() === 'POST'),
        page.getByRole('button', { name: 'Preparar propuestas' }).click()
      ]);
      assert.ok(propuesta.ok(), await propuesta.text());
      const descriptor = page.getByLabel('Descriptor de logro', { exact: true }).last();
      await descriptor.waitFor();
      assert.ok((await descriptor.inputValue()).startsWith('Alumno ficticio A'));
      await descriptor.fill('Alumno ficticio A identifica una idea principal con apoyo visual.');
      await page.getByRole('button', { name: 'Incorporar propuesta revisada' }).click();
      await page.getByText('Cambios pendientes', { exact: true }).waitFor();
      await page.getByText('Guardado confirmado', { exact: true }).waitFor();
      if (process.env.USAER_EVIDENCIA) {
        await descriptor.scrollIntoViewIfNeeded();
        await page.screenshot({ path: process.env.USAER_EVIDENCIA });
      }
      const estado = await page.evaluate(async id => (await fetch('/api/planeaciones/' + id)).json(), individualId);
      assert.equal(estado.tablas.aprendizajes.at(-1)['Descriptor de logro'], 'Alumno ficticio A identifica una idea principal con apoyo visual.');
      await page.getByRole('button', { name: /Alumnos y Expedientes/ }).click();
      await page.getByRole('button', { name: /^Eventos/ }).last().click();
      await page.getByRole('button', { name: 'Nuevo registro' }).click();
      await page.getByRole('textbox', { name: 'Evento significativo', exact: true }).fill('Evento ficticio desde React');
      await page.getByRole('button', { name: 'Guardar anexo' }).click();
      await page.getByText('Anexo guardado.', { exact: true }).waitFor();
      const registro = page.locator('article').filter({ hasText: 'Evento ficticio desde React' });
      await registro.getByRole('button', { name: 'Editar' }).click();
      await page.getByRole('textbox', { name: 'Evento significativo', exact: true }).fill('Seguimiento ficticio desde React');
      await page.getByRole('button', { name: 'Guardar anexo' }).click();
      const seguimiento = page.locator('article').filter({ hasText: 'Seguimiento ficticio desde React' });
      await seguimiento.waitFor();
      const [pdf] = await Promise.all([page.waitForEvent('download'),
        seguimiento.getByRole('button', { name: 'Descargar PDF' }).click()]);
      assert.equal(pdf.suggestedFilename(), 'Anexo-5.pdf');
      console.log('Edge / Anexo V: alta, edición y exportación OK');
    }
    console.log('Edge / PostgreSQL: ' + modo + ' OK');
  } finally {
    await browser.close();
  }
})().catch(e => { console.error(e); process.exitCode = 1; });
