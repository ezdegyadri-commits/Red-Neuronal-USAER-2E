// Los identificadores de Drive se configuran en Apps Script > Configuración del proyecto > Propiedades del script.
function propiedadRequerida_(nombre) {
  const valor = PropertiesService.getScriptProperties().getProperty(nombre);
  if (!valor) throw new Error(`Falta configurar la propiedad del script: ${nombre}`);
  return valor.trim();
}

function propiedadOpcional_(nombre) {
  return nombre ? (PropertiesService.getScriptProperties().getProperty(nombre) || "").trim() : "";
}

const DIRECTORIO = {
  "Psicología": [
    { nombre: "María José Cupul Realpozo", escuelas: ["DAMIÁN CARMONA", "ICHCAANZIHO", "ELVIRA PARRA ÁVILA", "QUINTANA RO0"] },
    { nombre: "Abril de María Chable Ríos", escuelas: ["GREGORIO TORRES QUINTERO", "REMIGIO AGUILAR SOSA", "MANUEL SARRADO", "DOMINGO SOLÍS RODRÍGUEZ"] }
  ],
  "Comunicación": [
    { nombre: "Elmy Lucelly Puerto Gone", escuelas: ["DAMIÁN CARMONA", "ICHCAANZIHO", "ELVIRA PARRA ÁVILA", "QUINTANA RO0"] },
    { nombre: "Marilyn Pérez Lizama", escuelas: ["GREGORIO TORRES QUINTERO", "REMIGIO AGUILAR SOSA", "MANUEL SARRADO", "DOMINGO SOLÍS RODRÍGUEZ"] }
  ],
  "Trabajo Social": [
    { nombre: "Diego Peralta Torres", escuelas: ["DAMIÁN CARMONA", "ICHCAANZIHO", "GREGORIO TORRES QUINTERO", "REMIGIO AGUILAR SOSA", "ELVIRA PARRA ÁVILA", "MANUEL SARRADO", "DOMINGO SOLÍS RODRÍGUEZ", "QUINTANA RO0"] }
  ]
};

const PROPIEDADES_FIRMAS = {
  "Edgar Adrián Yam Briceño": "FIRMA_EDGAR",
  "María José Cupul Realpozo": "FIRMA_MARIA_JOSE",
  "Abril de María Chable Ríos": "FIRMA_ABRIL",
  "Elmy Lucelly Puerto Gone": "FIRMA_ELMY",
  "Marilyn Pérez Lizama": "FIRMA_MARILYN",
  "Diego Peralta Torres": "FIRMA_DIEGO"
};

function doGet() {
  if (!usuarioEspecialistaAutorizado_()) {
    return HtmlService.createHtmlOutput('Acceso exclusivo al equipo de especialistas de la USAER 02-E.')
      .setTitle('Acceso restringido');
  }
  return HtmlService.createHtmlOutputFromFile('Index')
      .setTitle('Generador de Cronogramas USAER 02-E')
      .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL)
      .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function obtenerDirectorio() {
  if (!usuarioEspecialistaAutorizado_()) return {};
  return DIRECTORIO;
}

function usuarioEspecialistaAutorizado_() {
  const correo = (Session.getActiveUser().getEmail() || "").trim().toLowerCase();
  const lista = propiedadOpcional_("CORREOS_ESPECIALISTAS");
  const autorizados = lista.split(",").map(valor => valor.trim().toLowerCase()).filter(Boolean);
  return Boolean(correo && autorizados.includes(correo));
}

function validarEspecialista_(datos) {
  const especialistas = Object.keys(DIRECTORIO)
    .filter(area => area !== "Dirección")
    .flatMap(area => DIRECTORIO[area].map(persona => ({ nombre: persona.nombre, area })));
  return especialistas.find(persona =>
    persona.nombre === datos.especialista && persona.area === datos.area
  );
}

// --- TRADUCTOR DE FECHAS (Solución al fallo de recuperación) ---
function normalizarFecha(valor) {
  if (!valor) return "";
  if (valor instanceof Date) {
    const yyyy = valor.getFullYear();
    const mm = String(valor.getMonth() + 1).padStart(2, '0');
    const dd = String(valor.getDate()).padStart(2, '0');
    return `${yyyy}-${mm}-${dd}`;
  }
  let str = String(valor).trim();
  if (str.includes('/')) {
    const p = str.split('/');
    if(p.length === 3) return `${p[2]}-${p[1].padStart(2, '0')}-${p[0].padStart(2, '0')}`;
  }
  return str;
}

function obtenerAgendaEspecialista(mes, especialista) {
  try {
    if (!usuarioEspecialistaAutorizado_()) return { exito: false, mensaje: "Acceso exclusivo al equipo de especialistas." };
    if (!validarEspecialista_({ especialista, area: Object.keys(DIRECTORIO).find(area =>
      DIRECTORIO[area].some(persona => persona.nombre === especialista)
    ) })) return { exito: false, mensaje: "Acceso reservado al equipo de especialistas." };
    const libro = SpreadsheetApp.openById(propiedadRequerida_("ID_BASE_DATOS"));
    const hoja = libro.getSheetByName('Registros');
    if (!hoja) return { exito: false, mensaje: "Hoja 'Registros' no encontrada." };

    // Usar getValues() en lugar de getDisplayValues para manejar fechas correctamente
    const datos = hoja.getDataRange().getValues();
    datos.shift();

    let agendaRecuperada = {};

    datos.forEach(fila => {
      const especialistaBD = fila[1];
      const escuelaBD = fila[4];
      const fechaBD = normalizarFecha(fila[5]); // Estandarizamos la fecha
      const actividadBD = fila[6];

      if (especialistaBD === especialista && fechaBD.startsWith(mes) && String(fila[7] || "ACTIVO") !== "SUSTITUIDO") {
        agendaRecuperada[fechaBD] = { escuela: escuelaBD, actividad: actividadBD };
      }
    });

    return { exito: true, datos: agendaRecuperada };
  } catch (error) {
    return { exito: false, mensaje: error.toString() };
  }
}

function generarPDFCronograma(datos) {
  try {
    if (!usuarioEspecialistaAutorizado_()) {
      return { exito: false, mensaje: "Acceso exclusivo al equipo de especialistas." };
    }
    if (!validarEspecialista_(datos)) {
      return { exito: false, mensaje: "El generador está reservado al equipo de especialistas." };
    }
    const plantilla = DriveApp.getFileById(propiedadRequerida_("ID_PLANTILLA_DOC"));
    const selloTiempo = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyyMMdd_HHmmss");
    const nombreArchivo = `Cronograma_${datos.especialista}_${datos.mes}_${selloTiempo}`;
    const idCarpeta = propiedadOpcional_("ID_CARPETA_DESTINO");
    let carpeta = idCarpeta ? DriveApp.getFolderById(idCarpeta) : DriveApp.getRootFolder();

    const docCopia = plantilla.makeCopy(nombreArchivo, carpeta);
    const doc = DocumentApp.openById(docCopia.getId());
    const cuerpo = doc.getBody();

    cuerpo.replaceText('{{AREA}}', datos.area);
    cuerpo.replaceText('{{MES}}', datos.mes);
    cuerpo.replaceText('{{ESPECIALISTA}}', datos.especialista);

    cuerpo.replaceText('{{ETIQUETA_NOMBRE}}', 'Especialista');
    cuerpo.replaceText('{{CARGO_IZQ}}', 'Elaboró');
    cuerpo.replaceText('{{NOMBRE_IZQ}}', datos.especialista);
    inyectarImagen(cuerpo, '{{ESPACIO_FIRMA_IZQ}}', propiedadOpcional_(PROPIEDADES_FIRMAS[datos.especialista]), null);

    cuerpo.replaceText('{{CARGO_DER}}', 'Vo. Bo.');
    cuerpo.replaceText('{{NOMBRE_DER}}', 'Psic. Edgar Adrian Yam Briceño MD\nDirector de la USAER 02');
    inyectarImagen(cuerpo, '{{ESPACIO_FIRMA_DER}}', propiedadOpcional_(PROPIEDADES_FIRMAS["Edgar Adrián Yam Briceño"]), propiedadOpcional_("ID_SELLO_OFICIAL"));

    const tablas = cuerpo.getTables();
    if (tablas.length > 0) {
      const tabla = tablas[0];
      const filaMolde = tabla.getRow(1).copy();
      tabla.removeRow(1);

      datos.agenda.forEach(item => {
        let nuevaFila = tabla.appendTableRow(filaMolde.copy());
        nuevaFila.getCell(0).setText(item.fecha);
        nuevaFila.getCell(1).setText(item.escuela);
        nuevaFila.getCell(2).setText(item.actividad);
      });
    }

    // --- LIMPIEZA DE SALTO DE PÁGINA FANTASMA ---
    const numHijos = cuerpo.getNumChildren();
    for (let i = numHijos - 1; i >= 0; i--) {
      const hijo = cuerpo.getChild(i);
      if (hijo.getType() === DocumentApp.ElementType.PARAGRAPH) {
        const parrafo = hijo.asParagraph();
        if (parrafo.getText().trim() === '' && parrafo.getNumChildren() === 0) {
          if (cuerpo.getNumChildren() > 1) {
            try { cuerpo.removeChild(parrafo); } catch (e) {
              parrafo.editAsText().setFontSize(1);
              parrafo.setSpacingBefore(0).setSpacingAfter(0);
            }
          } else {
            parrafo.editAsText().setFontSize(1);
            parrafo.setSpacingBefore(0).setSpacingAfter(0);
          }
        } else { break; }
      }
    }

    const ultimoHijo = cuerpo.getChild(cuerpo.getNumChildren() - 1);
    if (ultimoHijo.getType() === DocumentApp.ElementType.PARAGRAPH) {
      const pFinal = ultimoHijo.asParagraph();
      if (pFinal.getText().trim() === '') {
        pFinal.editAsText().setFontSize(1);
        pFinal.setSpacingBefore(0).setSpacingAfter(0).setLineSpacing(1);
      }
    }

    doc.saveAndClose();
    Utilities.sleep(500);

    const blobPDF = docCopia.getAs('application/pdf');
    const archivoPDF = carpeta.createFile(blobPDF);
    docCopia.setTrashed(true);

    // --- GUARDADO A PRUEBA DE GOOGLE SHEETS ---
    let bloqueo = null;
    try {
      const libroDB = SpreadsheetApp.openById(propiedadRequerida_("ID_BASE_DATOS"));
      let hojaDB = libroDB.getSheetByName('Registros');
      if (!hojaDB) throw new Error("No se encontró la hoja 'Registros'.");
      bloqueo = LockService.getScriptLock();
      bloqueo.waitLock(30000);
      if (hojaDB.getMaxColumns() < 8) hojaDB.insertColumnAfter(hojaDB.getMaxColumns());
      if (!hojaDB.getRange(1, 8).getValue()) hojaDB.getRange(1, 8).setValue("Estado");
      const datosDB = hojaDB.getDataRange().getValues();

      // Primero agrega la versión nueva; solo después marca la anterior como
      // sustituida. Así, un fallo durante el guardado nunca oculta la agenda vigente.
      datos.agenda.forEach(item => {
        // Convertimos DD/MM/YYYY a YYYY-MM-DD
        let fechaISO = item.fecha;
        if (fechaISO.includes('/')) {
          const p = fechaISO.split('/');
          fechaISO = `${p[2]}-${p[1]}-${p[0]}`;
        }

        hojaDB.appendRow([
          new Date(),
          datos.especialista,
          datos.area,
          "Sede Base",
          item.escuela,
          "'" + fechaISO, // El apóstrofe inicial obliga a Sheets a guardarlo como texto inmutable
          item.actividad,
          "ACTIVO"
        ]);
      });

      // Conserva el historial: marca la versión anterior sin borrar sus filas.
      for (let i = 1; i < datosDB.length; i++) {
        const especialistaBD = datosDB[i][1];
        const fechaBD = normalizarFecha(datosDB[i][5]);
        const estado = String(datosDB[i][7] || "ACTIVO");
        if (especialistaBD === datos.especialista && fechaBD.startsWith(datos.mes) && estado !== "SUSTITUIDO") {
          hojaDB.getRange(i + 1, 8).setValue("SUSTITUIDO");
        }
      }
    } catch(e) {
      console.error("Error al guardar en BD: " + e);
    } finally {
      if (bloqueo && bloqueo.hasLock()) bloqueo.releaseLock();
    }

    return {
      exito: true,
      url: archivoPDF.getUrl(),
      mensaje: "PDF generado exitosamente."
    };

  } catch (error) {
    return { exito: false, mensaje: "Error al generar: " + error.toString() };
  }
}

function inyectarImagen(cuerpo, etiqueta, idFirma, idSello) {
  const elemento = cuerpo.findText(etiqueta);
  if (!elemento) return;

  try {
    const txt = elemento.getElement();
    const p = txt.getParent().asParagraph();
    txt.setText('');

    p.setAlignment(DocumentApp.HorizontalAlignment.CENTER);
    p.setSpacingBefore(0);
    p.setSpacingAfter(0);
    p.setLineSpacing(1);

    if (p.getParent().getType() === DocumentApp.ElementType.TABLE_CELL) {
      const celda = p.getParent().asTableCell();
      celda.setVerticalAlignment(DocumentApp.VerticalAlignment.BOTTOM);
      celda.setPaddingTop(0);
      celda.setPaddingBottom(0);
    }

    if (idFirma && idFirma.trim() !== '') {
      const blobFirma = DriveApp.getFileById(idFirma.trim()).getBlob();
      const imgFirma = p.appendInlineImage(blobFirma);
      const propFirma = imgFirma.getHeight() / imgFirma.getWidth();
      imgFirma.setWidth(110).setHeight(Math.round(110 * propFirma));
    }

    if (idSello && idSello.trim() !== '') {
      p.appendText('  ');
      const blobSello = DriveApp.getFileById(idSello.trim()).getBlob();
      const imgSello = p.appendInlineImage(blobSello);
      const propSello = imgSello.getHeight() / imgSello.getWidth();
      imgSello.setWidth(70).setHeight(Math.round(70 * propSello));
    }

  } catch (e) {
    console.error("Error al inyectar imagen: " + e);
  }
}

function obtenerAgendaGlobal(mes) {
  try {
    if (!usuarioEspecialistaAutorizado_()) return { exito: false, mensaje: "Acceso exclusivo al equipo de especialistas." };
    const libro = SpreadsheetApp.openById(propiedadRequerida_("ID_BASE_DATOS"));
    const hoja = libro.getSheetByName('Registros');
    if (!hoja) return { exito: false, mensaje: "No se encontró la base de datos." };

    const datos = hoja.getDataRange().getValues();
    datos.shift();

    let agendaGlobal = {};

    datos.forEach(fila => {
      const especialista = fila[1];
      const escuela = fila[4];
      const fechaBD = normalizarFecha(fila[5]);

      if (fechaBD.startsWith(mes) && String(fila[7] || "ACTIVO") !== "SUSTITUIDO") {
        if (!agendaGlobal[fechaBD]) {
          agendaGlobal[fechaBD] = [];
        }
        const primerNombre = especialista.split(" ")[0];
        const yaExiste = agendaGlobal[fechaBD].some(act => act.nombre === primerNombre && act.escuela === escuela);

        if (!yaExiste) {
          agendaGlobal[fechaBD].push({
            nombre: primerNombre,
            escuela: escuela
          });
        }
      }
    });

    return { exito: true, datos: agendaGlobal };
  } catch (error) {
    return { exito: false, mensaje: error.toString() };
  }
}