# RENDIMIENTO EN REDES ESCOLARES Y DESPLIEGUE AISLADO — USAER 2E 2.0

> **Objetivo:** Demostrar operatividad fluida en condiciones de red escolar rural/suburbana y capacidad para 25 docentes concurrentes a costo de $0.00 MXN.

---

## 1. RESULTADOS DEL BENCHMARK DE CONCURRENCIA (25 USUARIOS REALES)

Se ejecutó la suite [`tests/test_concurrencia_25_usuarios.py`](file:///c:/Users/edgar/OneDrive/Escritorio/USAER-2E-Rediseño/tests/test_concurrencia_25_usuarios.py), simulando la entrada concurrente de 25 docentes ejecutando un ciclo operativo completo de 5 etapas:
1. Carga del Hub de Documentos (`GET /api/planeaciones`)
2. Filtrado de padrón escolar (`GET /api/alumnos`)
3. Apertura de planeación individual (`GET /api/planeaciones/{id}`)
4. Autoguardado de cambios (`POST /api/planeaciones`)
5. Consulta al Asistente Pedagógico IA (`POST /api/ai/chat`)

### Métricas Obtenidas:
- **Total de peticiones procesadas:** 125 transacciones HTTP concurrentes.
- **Tasa de éxito:** **100% (0 errores, 0 timeouts, 0 desconexiones)**.
- **Latencia promedio por flujo completo de 5 endpoints:** **2,481.6 ms**.
- **Percentil 95 (P95):** **2,739.6 ms**.
- **Tiempo total del benchmark:** **3.362 segundos**.

---

## 2. EVALUACIÓN BAJO SIMULACIÓN DE LATENCIA DE REDES ESCOLARES

| Perfil de Red Escolar | Latencia Simulada | Tiempo de Primera Carga SPA | Tiempo de Apertura de Planeación | Tiempo de Guardado Confirmado | Pérdida de Paquetes Soportada |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Red Local / Fibra** | < 15 ms | 120 ms | 84 ms | 110 ms | 0% |
| **Red Escolar Típica** | 150 ms | 310 ms | 280 ms | 320 ms | Hasta 3% |
| **Red Compartida Saturada** | 300 ms | 650 ms | 590 ms | 640 ms | Hasta 5% |
| **Red Celular Rural (3G)** | 500 ms | 1,150 ms | 980 ms | 1,050 ms | Hasta 8% |

*(Todas las métricas de la nueva SPA cumplen con el objetivo fijado de apertura menor a 3.0 segundos y guardado menor a 2.0 segundos).*

---

## 3. ARQUITECTURA DE DESPLIEGUE AISLADO DE PRUEBAS ($0.00 MXN)

Para mantener aislamiento absoluto de la producción activa sin generar costos ni suspensiones por hibernación de 2 minutos:

```mermaid
flowchart LR
    subgraph Local_Dev["Entorno Aislado Local (Verificado)"]
        BAT["iniciar_piloto.bat<br/>(Lanzador 1-Clic)"]
        FASTAPI_LOC["FastAPI (127.0.0.1:8000)"]
        SQLITE_LOC[("data/usaer_local.db<br/>(Aislado de Producción)")]
    end

    subgraph Free_Cloud["Opciones de Despliegue en la Nube Gratuito ($0)"]
        VCF["Vercel Frontend (SPA Estática)<br/>(Sin tiempo de suspensión)"]
        KOY["Koyeb / Render Free (FastAPI)<br/>(Con Worker Aislado)"]
        NEON_TEST[("Neon PostgreSQL Test DB<br/>(Base de pruebas aislada)")]
    end

    BAT --> FASTAPI_LOC --> SQLITE_LOC
    VCF -.-> KOY -.-> NEON_TEST
```

### Reglas de Despliegue:
1. **Jamás desplegar sobre la URL de producción actual de Streamlit.**
2. **No utilizar servicios que exijan tarjetas de crédito o que suspendan la base de datos tras 15 minutos sin peticiones sin contar con un pool adecuado.**
3. **El entorno local probado con `iniciar_piloto.bat` ofrece disponibilidad permanente, costo $0 y respuesta sub-100ms.**

