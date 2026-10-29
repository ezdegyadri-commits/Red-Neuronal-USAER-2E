# Modelos de IA disponibles para todas las áreas

La generación heredada se detenía en 404 y varios accesos preferían un nombre fijo. La nueva capa `ai.modelos_gemini` consulta ListModels únicamente después de un 404, filtra modelos Gemini que anuncian generateContent y descarta imágenes, audio y herramientas especializadas. Prueba como máximo dos alternativas anunciadas; conserva esquema, validación y contenido. No cambia claves ni proveedor.

Se aplica a Planeación (camino directo y segundo plano), chat, EPP contextual y lectura visual. Recupera preferencias antiguas sin exigir que cada docente cambie ajustes. Recuerda el modelo exitoso cinco minutos por conexión mediante un hash, con cachés acotados; no conserva claves ni documentos en ese caché. Si el sustituto desaparece, actualiza el catálogo. Si falla el catálogo, conserva el error original y el borrador.

No evade errores de permisos, cuota o facturación. No altera documentos, matrículas ni reglas pedagógicas. Se mantiene el manejo existente de esas condiciones. Actualiza las referencias de sesiones abiertas y conserva ejecutores, semáforos y ContextVars, también mediante una prueba de recarga real.

Validación: 105 casos de generación, memoria, EPP y transportes aprobados; tras completar activación, 26 casos dirigidos aprobados. Se probaron las cuatro áreas con datos ficticios, 404 y caché, renovación de catálogo, aislamiento por conexión, exclusión de modelos no compatibles y respeto de errores 400/401/402/403/429/503. Dos comprobaciones antiguas se alinearon con el contrato ya publicado de fuentes verificadas y decisiones docentes conservadas, sin modificar esos prompts.

No hay clave local de producción. La recuperación se probó con el SDK simulado; queda pendiente comprobar una generación autorizada desde la sesión publicada.

Referencia oficial: https://ai.google.dev/api/models?hl=es-419 (ListModels y supported_actions).
