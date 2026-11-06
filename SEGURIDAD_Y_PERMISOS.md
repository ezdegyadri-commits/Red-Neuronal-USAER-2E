# SEGURIDAD Y CONTROL DE ACCESO (RBAC) — USAER 2E 2.0

> **Mecanismo:** Tokens Bearer generados con generador criptográfico del sistema operativo (`secrets.token_urlsafe(32)`).  
> **Validación:** En cada solicitud HTTP a través de la dependencia FastAPI `validar_token_sesion`.  
> **Política:** Prohibición absoluta de accesos anónimos o por simple nombre de usuario.  

---

## 1. MATRIZ DE CONTROL DE ACCESO BASADO EN ROLES (RBAC)

| Rol Institucional | Alcance de Escuelas | Acceso a Padrón de Alumnos | Edición de Planeaciones | Vo. Bo. y Firmas de Dirección | Emisión de Oficios |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **DIRECTOR** (`Psic. Edgar Adrián Yam Briceño MD`) | **TODAS** (`ESC-001` a `ESC-008`) | Padrón completo de la Zona 001 | Consulta, observaciones y aprobación | **SÍ** (Autoridad exclusiva) | **SÍ** |
| **MAESTRA DE APOYO** (ej. Cindy Burgos) | Exclusivamente sus escuelas (`ESC-001`, `ESC-003`) | Alumnos de su centro de trabajo | Edición de sus planeaciones asignadas | NO (Solicita Vo. Bo.) | NO |
| **PSICOLOGÍA** (ej. Laura Pech) | Zona 001 con derivación | Expedientes con derivación psicológica | Consulta y llenado de EPP (Área Psicología) | NO | NO |
| **COMUNICACIÓN** (ej. Mariana Solís) | Zona 001 con derivación | Expedientes con derivación de lenguaje | Consulta y llenado de EPP (Área Comunicación) | NO | NO |
| **TRABAJO SOCIAL** (ej. Roberto Méndez) | Zona 001 con derivación | Expedientes sociofamiliares | Consulta y llenado de EPP (Área T. Social) | NO | NO |

---

## 2. AUDITORÍA DE SEGURIDAD Y VULNERABILIDADES CORREGIDAS

1. **Eliminación del Fallback Anónimo:**  
   Se removió el bypass que permitía responder con un usuario demo cuando no se enviaba el encabezado `Authorization`. Toda petición no autenticada recibe de inmediato un código de estado `HTTP 401 Unauthorized`.
2. **Cotejo Criptográfico de Contraseñas:**  
   La función `autenticar_usuario` coteja contra la base relacional admitiendo hashes SHA-256 para almacenamiento seguro de credenciales.
3. **Invalidación Inmediata de Tokens en Logout:**  
   Al presionar "Salir", el token es revocado en memoria (`_ACTIVE_SESSIONS`) impidiendo que un tercero reutilice el token anterior en un equipo compartido de aula de apoyo.
4. **Protección de Datos Sensibles de Menores:**  
   Se erradicó el volcado masivo de expedientes en texto plano dentro de `localStorage`. Los datos sensibles de diagnóstico residen únicamente en la memoria reactiva del componente activo y se descargan bajo demanda restringida.
5. **Aislamiento Multi-Escuela:**  
   Se probó en [`tests/test_end_to_end_spa.py`](file:///c:/Users/edgar/OneDrive/Escritorio/USAER-2E-Rediseño/tests/test_end_to_end_spa.py) que una maestra de una escuela no puede solicitar ni recibir expedientes pertenecientes a otra primaria.

