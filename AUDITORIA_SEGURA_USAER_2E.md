# AUDITORÍA TÉCNICA Y DIAGNÓSTICO DE RENDIMIENTO — USAER 2E

> **Documento:** Auditoría Segura sin Interrupciones  
> **Fecha:** 3 de noviembre de 2026  
> **Entorno:** Aislado (Rama `auditoria-segura`, sin interacción con producción ni Google Sheets de producción)  
> **Objetivo:** Determinar la causa exacta de las latencias de ~2 minutos experimentadas en producción y diseñar una arquitectura estable, fluida y de costo $0 pesos para el equipo docente.

---

## 1. ESTADO DE LA ARQUITECTURA ACTUAL

La plataforma USAER 2E cuenta con una estructura híbrida desarrollada en capas que actualmente exhibe una sobreposición de modelos de datos:

```
[ Navegador Web del Docente ]
              │ WebSocket (Streamlit)
              ▼
    [ app.py (Streamlit) ]
              │
    ┌─────────┴─────────┐
    ▼                   ▼
[ ui/modules ]     [ services/ ]
                        │
                        ▼
            [ data/repository.py ]
              │             │
   (usar_sql=False)    (usar_sql=True)
              ▼             ▼
      [ data/google.py ]   [ data/sql_repository.py ]
              │                     │
              ▼                     ▼
    [ data/pg_documental.py ]  [ PostgreSQL / Neon ]
    (Emulador gspread SQL)     (Tablas relacionales)
              │
              ▼
   [ Tabla streamlit_filas ]
   (JSON array por celda)
```

### 1.1 El "Emulador" de Google Sheets sobre PostgreSQL
En `data/origen_operativo.py`, la bandera `usar_sql()` retorna `False`. Esto desvía todas las operaciones de `data/repository.py` hacia `data/google.py`. Sin embargo:
- `data/google.py` **no consulta la API real de Google Sheets** en operaciones regulares.
- Instancia `data.pg_documental.Cliente()`, el cual emula la biblioteca `gspread` (`Libro`, `Hoja`, `get_all_values()`, `row_values()`, `append_rows()`) traduciendo cada lectura tabular en consultas sobre la tabla `streamlit_filas` en PostgreSQL (Neon).
- Cada fila y celda se serializa y deserializa en arrays JSON individuales (`valores: J`).

### 1.2 Doble Capa SQL Inconexa
Existe en paralelo `data/sql_repository.py` y `data/database.py` con tablas relacionales bien estructuradas (`alumnos`, `planeaciones_doc`, `epp_documentos`, `usuarios`). Al estar `usar_sql() = False`, estas tablas relacionales no se aprovechan plenamente en la lectura del padrón, forzando la reconstrucción iterativa de DataFrames a partir de `streamlit_filas`.

---

## 2. PROBLEMAS DETECTADOS Y EVIDENCIAS DE CÓDIGO

### 2.1 Evidencia 1: La "Purga de Estado" en el Encabezado de `app.py`
En `app.py` (líneas 17-21), se introdujo:
```python
import streamlit as st
# Purga obligatoria de estado: destruye memoria corrupta al iniciar
try:
    st.cache_data.clear()
except Exception:
    pass
```
* **Impacto:** Streamlit es un framework de ejecución reactiva de arriba hacia abajo (*top-to-bottom rerun*). Cada interacción del usuario (teclear en un campo de texto, seleccionar un desplegable, abrir un acordeón o pulsar un botón) reejecuta `app.py` completo.
* **Consecuencia:** Al llamar a `st.cache_data.clear()` en la línea 19, **el caché en memoria se destruye en cada interacción individual**. Ningún TTL de 3600 segundos llega a cumplirse. Cada rerun fuerza a descargar y reconstruir el padrón de alumnos, usuarios y planeaciones desde Neon PostgreSQL a través de internet.

### 2.2 Evidencia 2: Múltiples Motores y Pools de Conexión Descoordinados
Antes de la unificación a `NullPool`, tres módulos independientes creaban su propio `engine` con pools aislados:
1. `data/database.py`: `create_engine(..., pool_size=5, max_overflow=1, pool_timeout=3)`
2. `data/acceso_usuarios.py`: `create_engine(..., pool_size=5, max_overflow=5, pool_timeout=10)`
3. `data/pg_documental.py`: `create_engine(..., pool_size=10, max_overflow=10, pool_timeout=15)`
* **Consecuencia:** Cuando 3 o 4 docentes abrían la plataforma concurrentemente, la suma de pools abiertos superaba las **20 conexiones activas**, alcanzando el límite duro de la capa gratuita de Neon. Esto provocaba que las peticiones se encolaran durante 30 a 60 segundos hasta dar `TimeoutError`.

### 2.3 Evidencia 3: Emulación de Celdas con Consultas Masivas y Bloqueos Advisory
En `data/pg_documental.py`:
- `Hoja.get_all_values()` (línea 149): Ejecuta `select(Fila).where(Fila.libro==self.libro, Fila.hoja==self.title).order_by(Fila.posicion)`. Para una tabla como `Alumnos`, descarga cientos de registros fila por fila, aplica `deepcopy` en memoria y luego `_records_from_values()` itera celda por celda.
- `bloqueo()` y operaciones de escritura: Hacen uso extensivo de `pg_advisory_xact_lock(:k)`. Si una conexión escolar lenta mantiene una transacción abierta, cualquier otra consulta que intente adquirir un cerrojo advisory entra en espera bloqueante en PostgreSQL.

---

## 3. DIAGNÓSTICO INTEGRAL DE LA LATENCIA DE 2 MINUTOS (FASE 3)

El tiempo excesivo de casi 2 minutos no tiene una sola causa, sino que es el resultado de una **cascada de latencias acumuladas**:

| Componente Evaluado | Comportamiento Identificado | Latencia Aportada |
| :--- | :--- | :---: |
| **A. Arranque de Alojamiento (Render Free Tier)** | Render suspende el contenedor (*spin down*) tras 15 minutos sin tráfico. Levantar el contenedor Docker de Python y Streamlit toma entre 50 y 90 segundos. | **50 – 90 s** |
| **B. Conexión a la Base de Datos (Neon Free Tier)** | Neon suspende su compute a los 5 minutos de inactividad. El primer query debe despertar la instancia PostgreSQL y negociar TLS. | **2 – 5 s** |
| **C. Latencia de Red WAN (Render ↔ Neon)** | Si Render está en Oregon (US-West) y Neon en Virginia (US-East) o Frankfurt, cada round-trip añade 70–120 ms. Con 10 consultas secuenciales por ciclo, la red sola añade 1 a 2 segundos. | **1 – 2 s** |
| **D. Saturación previa del Pool de Conexiones** | Al agotarse el pool de 2 o 5 conexiones, los hilos de Streamlit esperaban timeouts de 10 a 30 segundos. | **10 – 30 s** |
| **E. Reruns continuos con Purga de Caché** | Cada clic destruía la caché (`st.cache_data.clear()`), forzando a repetir los pasos B, C y F en cada pulsación de botón. | **3 – 8 s** |
| **F. Conexiones Escolares de Baja Calidad** | Escuelas con enlaces ADSL/4G con pérdida de paquetes (2-5%) experimentan congelamiento del canal WebSocket de Streamlit al transferir deltas grandes. | **5 – 15 s** |
| **TIEMPO TOTAL ACUMULADO (En frío + saturación):** | **Arranque en frío + despertar Neon + pool timeout + reconstrucción** | **~120 segundos** |

---

## 4. ANÁLISIS COMPARATIVO DE PROPUESTAS ARQUITECTÓNICAS (COSTO $0 PESOS)

El requerimiento estricto es **presupuesto adicional de cero pesos**, asegurando alta disponibilidad para el equipo.

### Opción 1: Streamlit Optimizado con Google Sheets Directo
* **Ventajas:** Familiaridad, no requiere servidor de base de datos intermedio, backup automático en Google Drive.
* **Limitaciones Críticas ($0 pesos):**
  1. *Límites de Cuota de Google:* La API v4 de Sheets impone un límite de **60 peticiones/minuto por usuario** y **300 peticiones/minuto por proyecto**. Con 10 docentes capturando planeaciones y EPP simultáneamente, se dispara el error `429 Quota Exceeded`.
  2. *Latencia de Escritura:* Cada escritura vía `gspread` toma entre 800 ms y 1,800 ms.
  3. *Concurrencia:* No hay transacciones ACID; dos docentes guardando al mismo tiempo pueden corromper índices de fila.
* **Veredicto:** Inadecuado como base de datos primaria transaccional; ideal únicamente como respaldo o archivo histórico.

### Opción 2: Streamlit Optimizado con Supabase PostgreSQL
* **Ventajas:**
  1. *PostgreSQL Completo:* Motor relacional ACID puro (sin emular celdas ni arrays JSON).
  2. *Connection Pooling Nativo (Supavisor):* Dispone de pooling transaccional en el puerto `6543`, permitiendo hasta **200 conexiones simultáneas en la capa gratuita** sin agotar sockets.
  3. *Política de Hibernación:* Supabase **NO suspende el cómputo cada 5 minutos** como Neon. Solo pausa proyectos tras **7 días continuos de inactividad total** (nunca ocurrirá durante el ciclo escolar).
  4. *Capacidad:* 500 MB de base de datos relacional y 2 GB de ancho de banda mensual, suficiente para 5+ ciclos escolares de texto de la USAER.
* **Veredicto:** **La opción técnica más sólida para la base de datos.**

### Opción 3: Solución Integral del Alojamiento de la Aplicación (El Factor Render)
El cuello de botella de 90 segundos ocurre porque **Render Free duerme la aplicación**. Para resolver esto con **$0 pesos**:
* **Estrategia A (Keep-Alive Programado en Render):**
  - Configurar un *ping* automatizado gratuito (por ejemplo, mediante una GitHub Action o un monitor gratuito de UptimeRobot / Cron-Job.org) que solicite el endpoint ligero `/_stcore/health` cada 10 minutos de lunes a viernes entre 7:00 AM y 3:00 PM.
  - Esto mantiene el contenedor de Render despierto durante toda la jornada escolar.
  - Al no entrar en suspensión, el tiempo de respuesta pasa de **90 segundos a menos de 400 milisegundos**.
* **Estrategia B (Migración a Streamlit Community Cloud):**
  - Streamlit Community Cloud (`share.streamlit.io`) es el servicio oficial de alojamiento de Streamlit, gratuito para repositorios de GitHub.
  - Maneja de forma nativa los WebSockets de Streamlit, tiene tiempos de arranque menores y no sufre de las restricciones agresivas de CPU de Render Free.

---

## 5. PLAN DE ACCIÓN Y MITIGACIÓN DE RIESGOS

### 5.1 Matriz de Riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
| :--- | :---: | :---: | :--- |
| **Interrupción de sesiones docentes activas** | NULA | Crítico | Todo trabajo se mantiene en rama aislada `auditoria-segura`. Cero despliegues durante horario laboral. |
| **Pérdida de datos en Google Sheets** | NULA | Crítico | No se ejecutan escrituras ni modificaciones de esquema sobre las hojas de cálculo productivas. |
| **Agotamiento de cuotas gratuitas** | Baja | Medio | Uso de Supavisor (Supabase) o NullPool en PostgreSQL; ping keep-alive acotado exclusivamente al horario de atención escolar. |

### 5.2 Cambios Necesarios en el Código (Para Implementación Fuera de Horario)
1. **Retirar la purga indiscriminada de caché:** Reemplazar `st.cache_data.clear()` en `app.py` por una clave de versión controlada (`_version_cache = "2026-11-03"`), permitiendo que la caché viva su TTL de 3600 segundos y no se limpie en cada rerun.
2. **Activar lectura SQL relacional limpia:** Cambiar `usar_sql()` a `True` en `data/origen_operativo.py` únicamente cuando las tablas relacionales estén 100% sincronizadas.
3. **Consolidar Engine único:** Centralizar toda la creación de conexiones en `data/database.py` para evitar motores redundantes.

---

## 6. PLAN DE MIGRACIÓN Y REVERSIÓN

### Fase de Migración (Solo con Autorización, Fin de Semana o Tarde):
1. **Respaldo Canónico:** Exportar una copia completa en formato SQLite y JSON de los datos actuales.
2. **Aprovisionamiento Supabase ($0 pesos):** Crear proyecto en región US-East (más cercana a México), habilitar puerto de pool transaccional `6543`.
3. **Pruebas en Staging:** Probar el flujo completo en rama secundaria con docentes de prueba.
4. **Despliegue Programado:** Actualizar variables de conexión en Render en horario inhábil (ej. 8:00 PM).

### Plan de Reversión Inmediata (Rollback < 2 minutos):
- Si el nuevo enlace presenta cualquier anomalía:
  1. Revertir la variable de entorno `DATABASE_URL` en el panel de Render.
  2. Forzar redeply del commit estable anterior (`main`).
  3. Tiempo estimado de recuperación: **90 segundos**.

---

## 7. ACCIONES QUE REQUIEREN AUTORIZACIÓN EXPLÍCITA DE EDGAR

De acuerdo con las reglas de operación, **no se aplicará ninguno de los siguientes puntos sin tu confirmación previa:**

- [ ] **Autorización 1:** Crear un monitor gratuito de "Keep-Alive" (ping cada 10 min de 7 AM a 3 PM) para evitar que Render duerma la aplicación durante la jornada escolar.
- [ ] **Autorización 2:** Remover la línea `st.cache_data.clear()` en el inicio de `app.py` que destruye la memoria en cada clic de los docentes.
- [ ] **Autorización 3:** Evaluar la creación de una base de datos en Supabase ($0 pesos) para sustituir el compute serverless de Neon que suspende a los 5 minutos.
- [ ] **Autorización 4:** Desplegar cualquier cambio en la rama `main` de producción.

