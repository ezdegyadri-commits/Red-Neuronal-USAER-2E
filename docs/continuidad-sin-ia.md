# Continuidad de planeación sin IA

Para maestras de apoyo, Psicología, Comunicación y Trabajo Social, en las
modalidades individual y grupal. Se conserva el formato de cada perfil.

1. Abre tu borrador o selecciona los alumnos y el periodo como siempre.
2. En **Preparar con IA**, pulsa **Continuar sin IA · abrir mi formato**.
   Está disponible aunque falte evidencia para generar o el motor falle.
3. En **Revisar y enviar**, abre **Información del expediente y referentes ·
   sin IA**. Si lo necesitas, pulsa **Autollenar información disponible · sin IA**.
   Reutiliza antecedentes vinculados y referentes ya seleccionados, sin consultar
   al motor. Alumno, escuela y periodo provienen de la selección existente.
4. Revisa y edita las celdas de tu formato. El autollenado no inventa NEE,
   objetivos, actividades ni resultados, ni sustituye una conclusión de EPP.
5. Usa **Guardar borrador** y comprueba su confirmación. Si el guardado queda
   pendiente, conserva **Descargar respaldo editable** antes de cerrar sesión.
   El PDF y las reglas de revisión/envío existentes siguen disponibles.
6. Cuando quieras retomar la asistencia, pulsa **Volver a preparar con IA**.
   Volver no genera por sí solo ni consume una solicitud.

## Decisión técnica y verificación

La continuidad es una opción adicional del recorrido existente, no un segundo
formato ni una base de datos nueva. Abrir el formato no escribe ni crea versiones.
El servicio reutiliza `planeacion_generacion.prellenar` y la autorización canónica;
el botón de autollenado conserva el guardado/recuperación existentes y es
idempotente cuando no cambia la información. Las celdas manuales quedan intactas.
No modifica permisos, esquemas, registros históricos ni configuración de Gemini.

Verificación sin servicios externos: `tools/probar_estabilizacion_sin_red.py`.
La suite pasó 336 pruebas, incluidas fallas simuladas de IA y guardado, ausencia
de fuentes, preservación de ediciones, recuperación, PDF y cuatro perfiles.
Las simulaciones de concurrencia son sintéticas, no una certificación de carga
de usuarios reales ni disponibilidad del proveedor o de Google Sheets.
