# Android · USAER 02E 1.0.0

APK de acceso al portal mediante Android Custom Tabs (o navegador predeterminado si no lo admite). No usa WebView ni una interfaz paralela. Android 7.0/API 24 o posterior. Necesita internet y un navegador compatible actualizado. No solicita permisos de cámara, archivos, huella, contactos, ubicación ni internet propios: el navegador gestiona la navegación y permisos web.

La URL es fija, HTTPS y oficial. No acepta destinos ni roles de intents externos. La barra del navegador muestra el dominio; no se simula una aplicación nativa offline ni una TWA sin asociación verificada. La autenticación y autorizaciones se realizan en el portal, incluyendo las llaves WebAuthn cuando el navegador/dispositivo las admitan. No se puede asegurar equivalencia completa sin probar cargas, descargas y acceso por llave en dispositivos físicos.

## Compilar en Windows sin servicios pagados

Después de aceptar personalmente los términos del Android SDK de Google:

```powershell
./download-tools.ps1 -AndroidSdkTermsAccepted
./build.ps1
```

Fuentes oficiales Java/Android con sumas verificadas. Sin Gradle ni dependencias de terceros dentro del APK. El propietario aceptó los términos del SDK para esta compilación; el script no acepta licencias automáticamente.

El APK se genera en `output/mobile/`. Los recursos, Java y DEX se compilan y empaquetan con aapt2, javac y D8; zipalign verifica la alineación y apksigner firma/verifica los esquemas v2/v3.

## Mantener actualizaciones

Conserva una copia PRIVADA de `.private-signing/usaer02e-release.p12` y `.private-signing/password.dpapi.xml`. La contraseña está protegida para este usuario Windows mediante DPAPI: mover solo esos archivos a otra cuenta/equipo no basta para recuperarla; se requiere exportación privada segura desde el equipo original. No publicar ninguno de esos archivos. Perder la clave impediría actualizaciones normales de la misma aplicación.

Identificador: `mx.usaer02e.portal`. En actualizaciones se debe aumentar `versionCode` y mantener la clave. La mayoría de cambios del portal se reflejan sin reinstalar este lanzador.

Certificado público SHA-256: `7f7e6d5cd52dd31fdebdf48b4791aae4efa361bb03423bc742ae45a198536a3d`.

## Verificado y pendiente

Compilación, firma, alineación, SDK mínimo/objetivo, ausencia de permisos y contenido del archivo verificados. No hay Android físico conectado, por lo que la instalación y la navegación real todavía no están verificadas. No presentar el APK como aprobado en dispositivos ni como versión de tienda.

Referencia del protocolo: https://developer.android.com/reference/androidx/browser/customtabs/CustomTabsIntent
