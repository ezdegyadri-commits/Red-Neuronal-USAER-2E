# Formato vivo de planeación

## Decisión de diseño

La pantalla principal es el documento, no un asistente de tres pasos ni un panel de configuración del motor. Crear o recuperar abre la hoja directamente. Las propuestas locales y la IA son ayudas opcionales dentro de esa hoja. El recorrido anterior queda disponible sobre el mismo ID, revisión y estado.

Se revisaron los cinco ejemplos grupales 2025–2026 compartidos por Dirección (primero, tercero, cuarto, quinto y sexto), el Manual de Operatividad USAER y los acuerdos vigentes de zona y Psicología. Solo se reutilizan estructuras y encabezados, nunca nombres, condiciones o intervenciones de esos ejemplos. El entorno no dispone de LibreOffice empaquetado para renderizar los Word originales; no se afirma una réplica gráfica exacta. La matriz de nueve columnas se verificará en el navegador.

## Contraste documental

- Manual, Anexo XIX, p. impresa 152 / PDF 163: guía grupal por alumno, cuatro áreas, derivación y situación inicial/final. Coincide con la estructura de los cinco ejemplos.
- Acuerdos de zona de octubre de 2026: actividades horizontales en el formato ajustado de zona; PI anual en su formato modificado. Se conserva la edición adaptada de zona existente. Esta vista no cambia la vigencia ni el esquema del PI.
- Anexo XX, p. 153 / PDF 164: enriquecimiento para AS, solo con aptitudes documentadas, conservado como complemento.
- XXI y XXII: intervención individual, NEE/IEPP, BAP, apoyos, ajustes y seguimiento; no se sustituye con la matriz grupal.
- XXIII/XXIV, pp. 166–171 / PDF 177–182: trimestral del servicio de apoyo, objetivos y descriptores observables, dosificación por contextos, evaluación y observaciones. La guía grupal es complementaria, no reemplaza estos fundamentos.
- XXV/XXVI, pp. 172–175 / PDF 183–186: Trabajo Social conserva BAP compartidas, apoyos, acciones, fechas y recursos por contexto; no recibe una tabla de NEE propia de otra función.
- Psicología USAER: subgrupos, al menos cinco sesiones grupales calendarizadas por trimestre, cinco competencias emocionales, una sesión en aula regular y sugerencia para familias. No se añaden esos mínimos a otras áreas ni requisitos CAM a USAER.

## Responsabilidades y compatibilidad

`ui/planeacion_viva.py` presenta la hoja. `services/planeacion_viva.py` acota la edición de guía y selecciona antecedentes por ID y vínculo verificado. No tiene acceso directo a Sheets ni llama IA. Los callbacks reutilizan `ui.planeacion._open/_persist/_autosave`, los servicios canónicos de permisos, creación, contexto, propuestas y salida documental.

La creación compartida está en `ui.planeacion_simple.crear_borrador`; ambas vistas llaman la misma ruta y conservan el bloqueo de ediciones pendientes. No hay migración, tabla nueva, permiso nuevo ni escritura masiva. Esta matriz quedó como alternativa; Dirección autorizó publicar la vista de papel descrita en `planeacion-sobre-formato-word.md` el 14 de octubre de 2026.

La guía se proyecta desde el documento canónico. Las propuestas locales ya incorporadas y con destinatario por ID pueden aparecer en una celda vacía del área propia; nunca sustituyen una edición manual ni se asocian por parecido de nombres. El PDF lee esa misma proyección. Las identidades, condición y aportaciones de otras áreas quedan protegidas en la hoja nueva; las guías enlazadas conservan el flujo de aportaciones.

La matriz y el campo de texto ampliado son dos formas de editar la misma celda. Los referentes se muestran separadamente de objetivos docentes. El panel del alumno solo muestra antecedentes asociados a ese ID; los materiales generales se etiquetan como tales. No se precargan situaciones finales, firmas, nuevas NEE ni diagnósticos.

El guardado conserva intervalos, reintentos, revisión optimista e historial existentes; no se prometen escrituras inmediatas ni trabajo completamente sin internet. Ante fallo de IA continúa la edición local; ante fallo de guardado permanece la edición de sesión y el respaldo descargable.

## Verificación

Las pruebas del recorrido anterior siguen ejecutándose contra su entrada explícita, porque se conserva como alternativa. Las pruebas nuevas ejercitan la entrada productiva, cuatro perfiles, individual/PI/grupal, edición y recuperación, filtro por modalidad y escuela, protección de identidad/aportes, aislamiento de fuentes, preparación local, falla de IA y falla de guardado. La batería offline incluye también expedientes, EPP, roles, horarios, calendario y coordinación sintética concurrente. La carga sintética no equivale a una certificación de veinte navegadores reales.

Resultado de desarrollo del 14 de octubre: 392 pruebas offline correctas (127.657 s), incluidas doce del adaptador/vista viva. Matriz de nueve columnas inspeccionada en Chrome a 1536 px con alumnos ficticios, sin usar registros productivos. Se comprobó la edición ampliada sobre la misma fila. Las guías en texto se actualizaron; el PDF de la interfaz anterior permanece disponible y se etiqueta como tal.
