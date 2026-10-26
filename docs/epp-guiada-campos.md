# Campos visibles y persistidos en la EPP guiada

La vista guiada leía y escribía los apartados en la raíz del contenido cuando
no recibía una sección explícita. Los generadores y el PDF usan `campos`. Por
ello una conclusión generada podía permanecer invisible, y los hallazgos escritos
desde esa vista podían quedar fuera del contenido canónico consultado por el equipo.

Los apartados usan ahora `campos`, salvo una sección explícita como `generales`.
La reconstrucción de versiones y la validación recuperan campos conocidos desde
la raíz únicamente cuando el campo canónico está vacío. No borran el dato original
ni sustituyen un contenido canónico ya corregido. Esta es una proyección de
lectura; no reescribe el historial en Google Sheets.

Tras generar se renuevan las claves de widgets y bases de tablas de Conclusión,
para que muestren el resultado actual. Solo se anuncia guardado confirmado cuando
la persistencia lo confirma; de lo contrario el resultado queda como pendiente.

Se prueba el botón exacto de la vista guiada, la conclusión visible, las filas NEE,
la edición posterior y el valor canónico guardado. Los datos son ficticios.
