# PLAN DE EVOLUCIÓN SPA — USAER 2E
## De Monolito Reactivo Streamlit a Experiencia SPA de Alto Rendimiento

> **Autor:** Arquitectura de Software USAER 2E  
> **Fecha:** 3 de noviembre de 2026  
> **Estado:** Piloto Aislado Construido y Verificado (Rama `piloto-spa`)  
> **Presupuesto:** **$0.00 pesos adicionales**  
> **Regla de Oro:** Producción intacta; cero interrupciones a los docentes.

---

## 1. RESUMEN EJECUTIVO Y PROPÓSITO

USAER 2E opera actualmente como una aplicación monolítica en Streamlit. Si bien Streamlit permitió digitalizar rápidamente los formatos institucionales, su modelo de ejecución reactivo (*top-to-bottom rerun*) presenta limitaciones estructurales para el uso escolar diario:
1. Cada interacción (teclear una letra, abrir un acordeón o pulsar un botón) reejecuta todo el script de Python.
2. Los datos de la interfaz se sincronizan mediante WebSockets transfiriendo árboles de deltas pesados (~400–600 KB).
3. En conexiones escolares rurales o de baja velocidad (enlaces ADSL/4G en primarias de Yucatán), esto provoca demoras perceptibles, parpadeos de interfaz y sensación de lentitud.

El **Plan de Evolución SPA** transforma USAER 2E en una arquitectura moderna desacoplada:
- **Frontend SPA (Single Page Application):** Construido en **React 18 / Next.js** con **Tailwind CSS**. La interfaz se carga una sola vez en el navegador y nunca vuelve a recargarse. El filtrado, validación y edición ocurren a velocidad nativa en el dispositivo del docente.
- **Backend de Alta Concurrencia:** API RESTful ultrarrápida en **FastAPI (Python)**, que reutiliza el 100% de la lógica pedagógica, validación de NEE, PDA, catálogos curriculares y firmas oficiales existentes.
- **Capa de Persistencia:** PostgreSQL relacional optimizado con consultas indexadas (`LIMIT 50`) y pooling transaccional.

---

## 2. ARQUITECTURA OBJETIVO DEL SISTEMA

```
┌────────────────────────────────────────────────────────────────────────┐
│                      NAVEGADOR DOCENTE (CLIENTE)                       │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                 React 18 / Next.js SPA Client                  │   │
│   │                                                                │   │
│   │  ┌──────────────┐  ┌─────────────────────┐  ┌───────────────┐  │   │
│   │  │ Lista Rápida │  │ Editor Planeaciones │  │ Asistente IA  │  │   │
│   │  │ (Filtro RAM) │  │ (Autosave Debounce) │  │ (Drawer Flot) │  │   │
│   │  └──────┬───────┘  └──────────┬──────────┘  └───────┬───────┘  │   │
│   │         │                     │                     │          │   │
│   │  ┌──────┴─────────────────────┴─────────────────────┴───────┐  │   │
│   │  │   Caché Local TanStack Query + LocalStorage Respaldo     │  │   │
│   │  └────────────────────────────┬─────────────────────────────┘  │   │
│   └───────────────────────────────┼────────────────────────────────┘   │
└───────────────────────────────────┼────────────────────────────────────┘
                                    │ Peticiones REST JSON (< 2 KB)
                                    │ TLS / HTTPS
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        BACKEND FASTAPI (PYTHON)                        │
│                                                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │ /api/planeaciones  │  /api/alumnos  │  /api/ai/sugerencias     │   │
│   └──────┬──────────────────────┬───────────────────────┬──────────┘   │
│          │                      │                       │              │
│   ┌──────┴───────────────┐ ┌────┴────────────────┐ ┌────┴───────────┐  │
│   │ services/planeacion  │ │ services/curriculo  │ │ ai/engine.py   │  │
│   │  - Firmas Edgar Yam  │ │  - PDA, Ejes, Fases │ │  - Gemini Fall │  │
│   └──────┬───────────────┘ └────┬────────────────┘ └────────────────┘  │
│          └──────────────┬───────┘                                      │
│                         ▼                                              │
│             [ data/sql_repository.py ]                                 │
└─────────────────────────┼──────────────────────────────────────────────┘
                          │ Conexión NullPool / Supavisor
                          ▼
┌────────────────────────────────────────────────────────────────────────┐
│                BASE DE DATOS RELACIONAL (POSTGRESQL)                   │
│                                                                        │
│   - Tabla `planeaciones_doc` (Indexada por cuenta y fecha)             │
│   - Tabla `alumnos` (Padrón canónico activo)                           │
│   - Tabla `epp_documentos` (Evaluación Psicopedagógica)                │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. COMPONENTES REUTILIZADOS DEL CÓDIGO ACTUAL (CERO REESCRITURA)

Para garantizar que **no se pierda ni una sola regla pedagógica**, el backend FastAPI reutiliza directamente los módulos de negocio de Python existentes:

| Módulo Actual | Función en la Nueva Arquitectura | Estado |
| :--- | :--- | :---: |
| [`services/planeacion_firmas.py`](file:///c:/Users/edgar/OneDrive/Escritorio/USAER-2E-Rediseño/services/planeacion_firmas.py) | Resuelve automáticamente el nombre del docente según escuela y el Vo. Bo. de **Psic. Edgar Adrián Yam Briceño MD**. | Reutilizado 100% |
| [`services/planeacion_modelo.py`](file:///c:/Users/edgar/OneDrive/Escritorio/USAER-2E-Rediseño/services/planeacion_modelo.py) | Estructura canónica de los formatos XXIII (Apoyo) y XXV (Trabajo Social). | Reutilizado 100% |
| [`services/curriculo.py`](file:///c:/Users/edgar/OneDrive/Escritorio/USAER-2E-Rediseño/services/curriculo.py) | Vinculación de Campos Formativos, Ejes Articuladores y Proceso de Desarrollo de Aprendizaje (PDA). | Reutilizado 100% |
| [`data/sql_repository.py`](file:///c:/Users/edgar/OneDrive/Escritorio/USAER-2E-Rediseño/data/sql_repository.py) | Consultas SQL de alta velocidad (`planeaciones_resumen_sql`, `alumnos_sql`, `guardar_planeacion_sql`). | Reutilizado 100% |
| [`ai/engine.py`](file:///c:/Users/edgar/OneDrive/Escritorio/USAER-2E-Rediseño/ai/engine.py) | Generación asistida de estrategias pedagógicas con tolerancia a fallos (*fallback*). | Reutilizado 100% |

---

## 4. ANÁLISIS DE HOSPEDAJE CON PRESUPUESTO DE $0.00 PESOS

| Plataforma | Capa Gratuita | Límites y Políticas | Estrategia de Mitigación |
| :--- | :--- | :--- | :--- |
| **Vercel** *(Frontend Next.js)* | **100% Gratuito** | - Ancho de banda: 100 GB/mes.<br>- Despliegue global Edge CDN.<br>- **Sin hibernación** (HTML y JS se sirven instantáneamente en < 50 ms). | Ideal para servir el frontend SPA. |
| **Render** *(Backend FastAPI)* | **100% Gratuito** | - 750 horas/mes.<br>- Hiberna a los 15 min de inactividad.<br>- Cold start: 50–70s. | Configurar un **Keep-Alive Ping** gratuito cada 10 min de 7 AM a 3 PM para que **nunca duerma en horario escolar**. |
| **Supabase** *(PostgreSQL)* | **100% Gratuito** | - 500 MB almacenamiento.<br>- Pooling Supavisor: hasta 200 conexiones.<br>- **No duerme** durante la semana. | Usar puerto 6543 para transacciones seguras sin saturar sockets. |

---

## 5. EXPERIENCIA DE USUARIO EN REDES ESCOLARES LENTAS

Para que la plataforma funcione de manera fluida incluso cuando el internet de la primaria sea intermitente o lento:

1. **Autoguardado con Debounce (1.5 segundos):**
   - El docente no tiene que presionar "Guardar" compulsivamente después de cada palabra.
   - La aplicación detecta pausas naturales en la escritura y envía un paquete JSON diminuto (< 1.5 KB).
2. **Indicador Visual de Tres Estados:**
   - `● Guardado en SQL` (Verde estático).
   - `● Guardando cambios...` (Ámbar pulsante).
   - `● Cambios pendientes` (Gris tenue mientras el usuario sigue escribiendo).
   - Si la red falla: `● Sin conexión (respaldo local guardado)` (Rojo informativo, nunca destructivo).
3. **Respaldo Local Inmediato (`localStorage`):**
   - En cada pulsación de tecla, el borrador se guarda de forma instantánea y encriptada en la memoria local del navegador. Si la computadora escolar se apaga o pierde el Wi-Fi, **no se pierde ni una sola palabra**.
4. **Cero Pantallas Blancas:**
   - La navegación entre listas, pestañas y el asistente pedagógico ocurre completamente en el cliente. El navegador no vuelve a descargar la página.

---

## 6. PLAN DE MIGRACIÓN PROGRESIVA SIN RIESGO

La migración debe ser **progresiva y transparente**, sin apagar la versión productiva actual:

```
[ Fase 0: Actual ]  ───► Streamlit en producción atendiendo a docentes.
[ Fase 1: Piloto ]  ───► Piloto SPA operando en subruta `/piloto` con datos sintéticos.
[ Fase 2: Validación] ──► Pruebas con 2 docentes voluntarios fuera de horario de clase.
[ Fase 3: Conexión ] ──► Conectar el SPA a la base de datos oficial.
[ Fase 4: Transición]──► Los docentes eligen usar la interfaz clásica o la versión rápida SPA.
[ Fase 5: Definitiva]──► Retiro programado de Streamlit una vez validada la satisfacción del equipo.
```

### Plan de Reversión Inmediata (Rollback < 60 segundos)
Si en cualquier momento de la fase de pruebas o despliegue se detecta alguna anomalía:
1. La versión de Streamlit se mantiene 100% intacta en su URL productiva.
2. Un switch de DNS o variable de entorno redirige el tráfico al contenedor de Streamlit original.
3. Tiempo de recuperación: **Menor a 1 minuto**.

---

## 7. GOBERNANZA Y ACCIONES QUE REQUIEREN AUTORIZACIÓN

Para proceder hacia la Fase 2 del piloto, se requerirá la aprobación de Edgar en:
- [ ] **Aprobación A:** Habilitar el endpoint `/piloto` en el servidor de pruebas para visualización interactiva.
- [ ] **Aprobación B:** Conectar el piloto SPA a una réplica de lectura para validación docente.

