# ARQUITECTURA DE SOFTWARE — USAER 2E 2.0

> **Modelo de Arquitectura:** Desacoplada de 3 Capas (SPA React 18 + API REST FastAPI + Base Relacional PostgreSQL / SQLite)  
> **Patrón de Persistencia:** Domain-Driven Services + SQLAlchemy ORM con Pool Acotado y Bloqueos de Concurrencia  
> **Costo de Operación:** $0.00 MXN adicionales durante desarrollo y pruebas  

---

## 1. DIAGRAMA ARQUITECTÓNICO INTEGRAL

```mermaid
flowchart TD
    subgraph Frontend["Capa de Presentación (Frontend SPA)"]
        UI["React 18 + Tailwind CSS<br/>(Cero Recargas / 0 ms Navegación)"]
        HUB["Mis Documentos<br/>(Apertura en 1 Clic)"]
        EDITOR["Editor de Planeación<br/>(Debounce 1.5s / 4 Pestañas)"]
        EXP["Expedientes Integrales<br/>(EPP + BAP + Sugerencias)"]
        DRAWER["Asistente Pedagógico IA<br/>(1 Clic Inserción)"]
        STORAGE["sessionStorage Seguro<br/>(Token Criptográfico Bearer)"]
    end

    subgraph Backend["Capa de Servicios (FastAPI Backend)"]
        API["FastAPI 2.0 RESTful Gateway<br/>(Puerto 8000 / 32 Endpoints)"]
        AUTH["auth_service.py<br/>(RBAC Estricto / Validación Token)"]
        DOMAIN["domain_services.py<br/>(Lógica Pedagógica y Transacciones)"]
        AI_ENGINE["ai/engine.py<br/>(14 Indicadores Zona 001)"]
        DOCS["documents/planeacion.py<br/>(Exportación PDF Oficial)"]
    end

    subgraph Persistence["Capa de Persistencia (PostgreSQL / SQLite Aislada)"]
        ORM["SQLAlchemy ORM + SafeSession<br/>(Conexiones Acotadas / Auto-Rollback)"]
        TABLES[("Tablas Relacionales Indexadas<br/>alumnos · escuelas · planeaciones<br/>epp_documentos · anexos · usuarios")]
        LOCKS["Control de Bloqueos de Concurrencia<br/>(Namespace: usaer2e)"]
    end

    UI --> HUB & EDITOR & EXP
    EDITOR <--> DRAWER
    UI <--> STORAGE
    UI -- "JSON REST (< 3 KB)" --> API
    API --> AUTH
    AUTH -- "Sesión Verificada" --> DOMAIN
    DOMAIN --> AI_ENGINE & DOCS
    DOMAIN --> ORM
    ORM <--> TABLES
    ORM <--> LOCKS
```

---

## 2. SEPARACIÓN ESTRICTA DE RESPONSABILIDADES

### A. Frontend (React 18 SPA)
- **Tecnología:** React 18, Tailwind CSS, Babel Standalone / Bundler estático minimalista.
- **Responsabilidad:** Renderizado client-side inmediato, manejo del estado reactivo de edición, debouncing de autoguardado (1,500 ms), filtrado instantáneo en memoria sobre arrays ya transferidos (0 ms de latencia percibida).
- **Seguridad en Cliente:** Eliminación total de almacenamiento de expedientes completos en `localStorage` plano. Únicamente se conserva el token Bearer en `sessionStorage`, el cual se purga automáticamente al cerrar el navegador o invocar el botón de Salir.

### B. Backend (Python / FastAPI)
- **Tecnología:** FastAPI, Pydantic v2, Starlette.
- **Responsabilidad:** 
  1. **Autenticación Criptográfica:** Emisión de tokens de portador de 32 bytes aleatorios generados mediante `secrets.token_urlsafe(32)`.
  2. **Control de Acceso Basado en Roles (RBAC):** Verificación estricta en cada petición de las escuelas asignadas al docente (`user.escuelas_permitidas`). Un docente asignado a `ESC-001` no puede consultar ni modificar alumnos de `ESC-002`.
  3. **Control de Concurrencia:** Asignación de hash de revisión atómico (`rev-xxxxxx`) en cada guardado de planeación y EPP, previniendo sobrescrituras ciegas.
  4. **Servicios de Asistencia Pedagógica:** Inyección de contexto educativo real del alumno sin enviar expedientes reales a servicios externos sin consentimiento.

### C. Persistencia Relacional (PostgreSQL / SQLite Aislado)
- **Tecnología:** PostgreSQL 16 con Neon / SQLite local protegido (`data/usaer_local.db`).
- **Control de Conexiones:** Motor SQLAlchemy configurado con `SafeSession` que garantiza cierre forzoso inmediato en bloques `try...finally` y `pool_pre_ping=True`, evitando fugas de conexiones como las sufridas anteriormente en Streamlit.
- **Esquema:** Integridad referencial con índices primarios en `id`, `curp`, `id_escuela`, `cuenta`, y marcas de tiempo UTC.

---

## 3. CONTRATO DE CONCURRENCIA PARA 25 DOCENTES SIMULTÁNEOS

```mermaid
sequenceDiagram
    autonumber
    actor Docente as Docente en Aula
    participant SPA as React SPA (Navegador)
    participant API as FastAPI Backend
    participant DB as PostgreSQL / SQLite

    Docente->>SPA: Escribe descriptor en Editor
    Note over SPA: Temporizador Debounce (1.5s)<br/>Estado: 'Cambios pendientes'
    Docente->>SPA: Pausa de escritura
    SPA->>API: POST /api/planeaciones (Payload JSON 2 KB)
    Note over SPA: Estado: 'Guardando cambios...'
    API->>DB: UPDATE planeaciones SET ... WHERE id=plan_id
    DB-->>API: Confirmación de Transacción (Revision: rev-7fa2)
    API-->>SPA: HTTP 200 OK (firmas y nueva revisión)
    Note over SPA: Estado: 'Guardado confirmado'<br/>Latencia: 84 ms
```
