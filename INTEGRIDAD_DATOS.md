# INTEGRIDAD DE DATOS Y CONCILIACIÓN DE MIGRACIÓN — USAER 2E 2.0

> **Herramienta implementada:** [`tools/migracion_historica_idempotente.py`](file:///c:/Users/edgar/OneDrive/Escritorio/USAER-2E-Rediseño/tools/migracion_historica_idempotente.py)  
> **Garantía de Producción:** Las hojas oficiales de Google Sheets **no han sido leídas masivamente ni modificadas**.  
> **Comprobación de Idempotencia:** 2 ejecuciones consecutivas verificadas (0 duplicados generados).  

---

## 1. REGLAS DE NORMALIZACIÓN Y LIMPIEZA DE DATOS

Durante el análisis del padrón histórico se detectaron inconsistencias en la captura de grados y grupos en formularios de Google Sheets. El motor de migración aplica las siguientes reglas canónicas antes de persistir en base relacional:

| Campo | Entrada Heterogénea en Sheets | Salida Canónica Normalizada en PostgreSQL | Justificación Pedagógica / Relacional |
| :--- | :--- | :--- | :--- |
| **Grado y Grupo** | `"2A"`, `"2°a"`, `"2-A"`, `"2° A"` | `grado: "2"`, `grupo: "A"` | Evita fragmentación de grupos en filtros y estadísticas. |
| **CURP** | `"cabj160512mynrrn01 "`, `" CABJ160512MYNRRN01"` | `"CABJ160512MYNRRN01"` (18 chars, uppercase, trimmed) | Clave única institucional para evitar alumnos duplicados. |
| **ID Escuela** | `"1"`, `"Damián Carmona"`, `"ESC-001"` | `"ESC-001"` (CCT: `31DPR0001A`) | Mapeo al catálogo oficial de las 8 primarias de la Zona 001. |
| **Revisión Documental** | Cadena vacía o `None` | `rev-xxxxxx` (Hash hexadecimal determinista) | Control de versiones para evitar conflictos de concurrencia. |

---

## 2. RESULTADOS DE LA PRUEBA DE IDEMPOTENCIA

Se ejecutó el script de migración sobre un lote sintético de prueba con registros nuevos y un registro duplicado intencional:

### Primera Ejecución:
```json
{
  "total_procesados": 3,
  "insertados": 2,
  "actualizados": 0,
  "duplicados_omitidos": 1,
  "errores": [],
  "reconciliacion_epp": 0,
  "dry_run": false
}
```

### Segunda Ejecución (Mismo Lote Exacto):
```json
{
  "total_procesados": 3,
  "insertados": 0,
  "actualizados": 2,
  "duplicados_omitidos": 1,
  "errores": [],
  "reconciliacion_epp": 0,
  "dry_run": false
}
```

### Conclusión de Integridad:
- **Cero registros duplicados** insertados en la segunda corrida.
- Actualización in situ de campos modificados sin pérdida de historial.
- Detección precisa de CURP duplicada.
- Compatible con modo `--dry-run` para pre-visualizar migraciones sin persistir en disco.

