# Acceso con llave de acceso

Cada persona entra primero con usuario y contraseña y abre «Acceso con huella o rostro» en la barra lateral. Confirma su contraseña, pulsa «Activar en este dispositivo» y después «Confirmar con mi teléfono». Debe aceptar la solicitud del sistema en un dispositivo personal. En accesos posteriores utiliza «Entrar con huella o rostro».

El navegador y el sistema operativo seleccionan rostro, huella o código de desbloqueo. No se garantiza biometría exclusiva; no se capturan ni almacenan imágenes del rostro o huellas. Las llaves pueden sincronizarse mediante el proveedor del dispositivo. Si el navegador no las admite, se mantiene el acceso normal.

## Seguridad y almacenamiento

WebAuthn verifica origen y dominio de producción, desafío aleatorio de un solo uso (120 segundos), presencia, verificación del usuario y firma criptográfica. La autorización usa la misma función que el acceso normal, con la cuenta leída nuevamente del directorio del servidor. Un cambio de contraseña invalida las llaves anteriores.

El registro público se añade a la pestaña privada `Accesos_Llaves_Publicas` de la base central. No se modifica ningún padrón, acta, evento o cronograma. El registro es acumulativo; la revocación no borra filas. Sus entradas se autentican mediante HMAC derivado de la clave privada de servicio del servidor; nunca se envía esa clave al navegador. Si se rota esa clave, las llaves anteriores dejan de funcionar: deberá migrarse el registro con ambas claves o reiniciarse exclusivamente esta pestaña y solicitar nueva activación. La contraseña sigue disponible.

La desactivación de todas las llaves propias está disponible en la misma sección. El bloqueo de escritura o lectura del registro impide el acceso con llave, sin simular una autenticación correcta. No se necesita habilitar OAuth de Drive.

## Verificación

11 pruebas de backend con autenticador sintético y firmas P-256 reales cubren alta, acceso, revocación, cuentas eliminadas, cambio de contraseña, firmas alteradas, origen/dominio incorrectos, falta de verificación de usuario, vencimiento y repetición de desafíos, contadores y registro adulterado. Estas pruebas no equivalen a una inscripción física en iOS/Android; cada persona deberá completar la activación y verificarla en su teléfono.
