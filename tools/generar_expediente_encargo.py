"""Generador del Expediente Jurídico-Técnico de Encargo de Tratamiento de Datos Personales.

Genera la documentación completa para USAER 2E 2.0 en la Pila Spark 140 (Uppcoder / WEBSSON d.o.o.),
en estricto apego a:
- Ley General de Protección de Datos Personales en Posesión de Sujetos Obligados (LGPDPPSO, arts. 53, 55-58, 62).
- Ley de Protección de Datos Personales en Posesión de Sujetos Obligados del Estado de Yucatán (LPDPPSOY, arts. 30, 44-49).
- Condiciones del Servicio y DPA (Apéndice 1) de Uppcoder / WEBSSON d.o.o.

Genera los archivos Markdown oficiales y compila el documento en formato Microsoft Word (.docx).
"""
import os
import sys
from pathlib import Path

# Directorio destino en el Escritorio del usuario
DESKTOP_DIR = Path(r"C:\Users\edgar\OneDrive\Escritorio\Expediente_Encargo_Tratamiento_USAER2E_Uppcoder")
DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------
# 1. CONTENIDO: 00_INDICE_Y_GUIA_DEL_EXPEDIENTE.md
# -------------------------------------------------------------
INDICE_MD = """# EXPEDIENTE DE ENCARGO DE TRATAMIENTO DE DATOS PERSONALES
## PLATAFORMA EDUCATIVA INTEGRAL USAER 2E 2.0
### INFRAESTRUCTURA: PILA SPARK 140 (UPPCODER / WEBSSON d.o.o.)

---

**Sujeto Obligado / Responsable:** Secretaría de Educación del Gobierno del Estado de Yucatán (SEGEY)  
**Centro de Trabajo:** Unidad de Servicios de Apoyo a la Educación Regular No. 02-E (USAER 02-E)  
**Clave de Centro de Trabajo (CCT):** 31FUA0002E | **Zona Escolar:** 001  
**Titular y Representante:** Psic. Edgar Adrián Yam Briceño MD — Director de la USAER 02-E  
**Proveedor / Encargado:** WEBSSON d.o.o. (Plataforma Uppcoder)  
**Entorno Técnico Asignado:** Pila Spark 140 (Dedicated Managed Tenant Stack)  
**Vigencia:** Ciclo Escolar 2026 - 2027 (Efectivo a partir del 1 de septiembre de 2026)  
**Folio Institucional:** `SEGEY-USAER02E-DPA-2026/SPARK140`

---

## 1. PROPÓSITO DEL EXPEDIENTE

El presente expediente reúne de forma canónica, verificable y trazable los instrumentos jurídicos, las especificaciones técnicas, las garantías de seguridad y los dictámenes de impacto a la privacidad que acreditan que la **USAER 02-E**, como institución responsable de los expedientes psicopedagógicos de sus alumnos, ha formalizado y adoptado con **WEBSSON d.o.o. (Uppcoder)** el encargo de tratamiento y alojamiento de datos personales en la **Pila Spark 140**, dando cabal cumplimiento a:

1. **Ley General de Protección de Datos Personales en Posesión de Sujetos Obligados (LGPDPPSO)**:
   - **Artículo 53**: Elementos mínimos y cláusulas obligatorias del instrumento jurídico de encargo.
   - **Artículos 55 y 56**: Condiciones obligatorias para la contratación de servicios de cómputo en la nube.
   - **Artículos 57, 58 y 62**: Garantías para el tratamiento y almacenamiento fuera del territorio nacional, transferencias internacionales y destrucción segura certificada de copias.
2. **Ley de Protección de Datos Personales en Posesión de Sujetos Obligados del Estado de Yucatán (LPDPPSOY)**:
   - **Artículo 30**: Obligaciones del responsable en la formalización de encargados de tratamiento.
   - **Artículos 44 al 49**: Evaluación de Impacto en la Protección de Datos Personales (EIPDP) para tratamientos intensivos o relevantes que involucren a menores de edad o datos sensibles de salud/educación especial.
3. **Condiciones del Servicio y Apéndice 1 de Uppcoder / WEBSSON d.o.o.**:
   - **Cláusula 12.2**: Formalización y alcance del Data Processing Addendum (DPA).
   - **Apéndice 1**: Cláusulas contractuales tipo de protección de datos (*Standard Contractual Clauses - SCC*) y medidas de seguridad técnicas y organizativas.

---

## 2. ESTRUCTURA Y CONTENIDO DEL EXPEDIENTE

Este expediente se compone de los siguientes instrumentos vinculantes e interconectados:

| Archivo | Documento | Marco Jurídico / Función |
| :--- | :--- | :--- |
| **01** | `01_CONSTANCIA_FORMALIZACION_ENCARGO_SPARK140.md` | **Constancia Ejecutiva de Formalización y Adopción Técnica**: Certifica la adopción institucional del servicio, identifica la cuenta, la pila Spark 140 y la base de datos relacional. |
| **02** | `02_CONTRATO_ENCARGO_TRATAMIENTO_DPA_USAER_UPPCODER.md` | **Acuerdo de Encargo de Tratamiento de Datos (DPA)**: Instrumento vinculante con las 12 cláusulas obligatorias del Art. 53 de la Ley General (objeto, alcance, categorías de datos, obligaciones, confidencialidad, incidentes y destrucción). |
| **03** | `03_ANEXO_TECNICO_NUBE_Y_TRANSFERENCIA_INTERNACIONAL.md` | **Anexo Técnico de Cómputo en la Nube y Almacenamiento en el Extranjero**: Documenta la ubicación física de centros de datos, arquitectura de la Pila Spark 140, subencargados, retención y *crypto-shredding* (Arts. 55-58 y 62 LGPDPPSO). |
| **04** | `04_DICTAMEN_EIPDP_EVALUACION_IMPACTO_YUCATAN.md` | **Dictamen de Evaluación de Impacto a la Privacidad (EIPDP) y Análisis de Excepción**: Análisis de necesidad, proporcionalidad y riesgos conforme a los Arts. 44-49 de la Ley de Yucatán, acreditando salvaguardas robustas y exención de consulta previa. |
| **05** | `05_APENDICE_MEDIDAS_SEGURIDAD_Y_SUBENCARGADOS.md` | **Apéndice de Medidas de Seguridad y Cadena de Subencargados**: Detalle de cifrado AES-256 / TLS 1.3, hashing PBKDF2-HMAC-SHA256, RBAC por CCT y matriz de subprocesadores certificados. |
| **COMPILADO** | `EXPEDIENTE_LEGAL_COMPLETO_ENCARGO_SPARK140_USAER02E.docx` | **Expediente Completo en Formato Word (.docx)**: Versión formal compilada con diseño institucional, lista para firma autógrafa, archivo y presentación ante auditorías de transparencia. |

---

## 3. TABLA DE CONCORDANCIA NORMATIVA

```
┌───────────────────────────────────────────────────┬─────────────────────────────────────────────────┐
│ Requerimiento Legal Exigido                       │ Documento y Cláusula en este Expediente         │
├───────────────────────────────────────────────────┼─────────────────────────────────────────────────┤
│ Partes, vigencia e identificación técnica         │ Doc. 01 (Constancia) y Doc. 02 (Cláusula 1 y 2) │
│ Delimitación de categorías de datos (sensibles)   │ Doc. 02 (Cláusula 3 y Anexo A)                  │
│ Finalidades exclusivas de la USAER 02-E           │ Doc. 02 (Cláusula 4)                            │
│ Obligaciones del proveedor (Art. 53 LGPDPPSO)     │ Doc. 02 (Cláusula 5, 6, 7 y 8)                  │
│ Notificación de brechas de seguridad (< 48 hrs)   │ Doc. 02 (Cláusula 9)                            │
│ Cómputo en nube y almacenamiento fuera de México  │ Doc. 03 (Anexo Técnico Internacional)           │
│ Devolución, retención y destrucción segura        │ Doc. 02 (Cláusula 11) y Doc. 03 (Sección 5)     │
│ Evaluación de Impacto (Arts. 44-49 Ley Yucatán)   │ Doc. 04 (Dictamen EIPDP)                        │
│ Cadena de subencargados y medidas técnicas        │ Doc. 05 (Apéndice de Seguridad)                 │
└───────────────────────────────────────────────────┴─────────────────────────────────────────────────┘
```

---
*Expediente integrado y validado para efectos de archivo legal, auditoría del Órgano Interno de Control de la SEGEY y verificación del Instituto Estatal de Transparencia, Acceso a la Información Pública y Protección de Datos Personales (INAIP Yucatán).*
"""

# -------------------------------------------------------------
# 2. CONTENIDO: 01_CONSTANCIA_FORMALIZACION_ENCARGO_SPARK140.md
# -------------------------------------------------------------
CONSTANCIA_MD = """# CONSTANCIA INSTITUCIONAL DE FORMALIZACIÓN Y ADOPCIÓN DEL ENCARGO DE TRATAMIENTO DE DATOS PERSONALES
## INFRAESTRUCTURA CLOUD: PILA SPARK 140 (UPPCODER / WEBSSON d.o.o.)

**Folio Institucional:** `SEGEY-USAER02E-DPA-2026/SPARK140`  
**Fecha de Expedición:** 01 de septiembre de 2026  
**Lugar de Expedición:** Mérida, Yucatán, México  

---

### I. CERTIFICACIÓN DE LA INSTITUCIÓN RESPONSABLE

El suscrito, **Psic. Edgar Adrián Yam Briceño MD**, en mi carácter de **Director de la Unidad de Servicios de Apoyo a la Educación Regular No. 02-E (USAER 02-E)**, dependiente de la Dirección de Educación Especial de la Secretaría de Educación del Gobierno del Estado de Yucatán (SEGEY), con Clave de Centro de Trabajo (CCT) **31FUA0002E**, perteneciente a la **Zona Escolar 001**:

**HAGO CONSTAR Y CERTIFICO:**

1. **Adopción del Encargo de Tratamiento:** Que con fundamento en el artículo 53 de la Ley General de Protección de Datos Personales en Posesión de Sujetos Obligados (LGPDPPSO) y el artículo 30 de la Ley de Protección de Datos Personales en Posesión de Sujetos Obligados del Estado de Yucatán (LPDPPSOY), la **USAER 02-E** formalizó y adoptó válidamente los términos de encargo de tratamiento contenidos en las Condiciones del Servicio y en el **Apéndice 1 (Data Processing Addendum - DPA)** de la empresa proveedora de infraestructura tecnológica **WEBSSON d.o.o.** (operadora de la plataforma **Uppcoder**).
2. **Entorno Técnico Acreditado:** Que el servicio de cómputo en la nube y persistencia de base de datos relacional para el sistema educativo **USAER 2E 2.0** opera bajo el entorno técnico denominado **Pila Spark 140 (Spark 140 Stack)**, configurado como espacio privado, dedicado y lógicamente aislado para la gestión de los expedientes escolares.
3. **Identificación de Cuentas y Recursos:**
   - **Razón Social del Proveedor:** WEBSSON d.o.o. (Registro de Eslovenia / Unión Europea, con sujeción a estándares GDPR).
   - **Plataforma del Servicio:** Uppcoder Cloud Infrastructure.
   - **Identificador de Organización Institucional:** `ORG-USAER02E-YUC`
   - **Cuenta de Administración Institucional:** `direccion.usaer02e@segey.gob.mx`
   - **Pila Técnica Asignada:** `Stack-Spark-140-USAER2E-Prod`
   - **Base de Datos Administrada:** `usaer_pg_spark140` (PostgreSQL Engine v15+, esquema relacional normalizado con control de acceso por CCT).
   - **Almacenamiento Conectado:** Volumen privado cifrado de alta disponibilidad con snapshots diarios encriptados.

---

### II. ALCANCE Y GARANTÍAS INSTITUCIONALES DEL ENCARGO

De conformidad con los instrumentos jurídicos y técnicos adjuntos a este expediente:

1. **Titularidad Invariable:** La USAER 02-E conserva la propiedad exclusiva, el control absoluto y la titularidad sobre la totalidad de los datos personales, académicos, clínicos y psicopedagógicos tratados en la plataforma.
2. **Finalidad Estrictamente Educativa:** Los datos son tratados con el único propósito de gestionar los expedientes de Evaluación Psicopedagógica (EPP), detección de Barreras para el Aprendizaje y la Participación (Anexo 3), Propuestas Curriculares Adaptadas (Anexo 4), seguimiento de intervención (Anexo 5) y planeaciones docentes institucionales de la Zona 001.
3. **Prohibición de Uso Secundario:** Queda terminantemente prohibido al proveedor y a cualquier subencargado utilizar, ceder, transferir, monetizar o emplear los datos para fines comerciales o para el entrenamiento de modelos de inteligencia artificial externos.
4. **Seguridad y Cifrado:** El entorno Spark 140 implementa cifrado en tránsito mediante TLS 1.3 y cifrado en reposo mediante AES-256 con separación estricta de llaves criptográficas.

---

### III. CONSTANCIA DE VIGENCIA Y REVISIÓN

La presente constancia y el contrato de encargo que ampara surten plenos efectos jurídicos y técnicos a partir del **01 de septiembre de 2026** y mantendrán su vigencia durante el **Ciclo Escolar 2026-2027**, renovable de manera anual y verificable ante cualquier auditoría del Órgano Interno de Control de la SEGEY o del Instituto Estatal de Transparencia, Acceso a la Información Pública y Protección de Datos Personales (INAIP Yucatán).

Se expide para los fines legales, administrativos y de transparencia que correspondan.

---

```
____________________________________________________
Psic. Edgar Adrián Yam Briceño MD
Director de la USAER 02-E (CCT: 31FUA0002E)
Zona Escolar 001 — Educación Especial
Secretaría de Educación del Gobierno del Estado de Yucatán
```
"""

# -------------------------------------------------------------
# 3. CONTENIDO: 02_CONTRATO_ENCARGO_TRATAMIENTO_DPA_USAER_UPPCODER.md
# -------------------------------------------------------------
CONTRATO_MD = """# ACUERDO VINCULANTE DE ENCARGO DE TRATAMIENTO DE DATOS PERSONALES (DPA)
## EN CUMPLIMIENTO DEL ARTÍCULO 53 DE LA LGPDPPSO Y ARTÍCULO 30 DE LA LPDPPSOY
### SISTEMA INTEGRAL USAER 2E 2.0 | INFRAESTRUCTURA PILA SPARK 140

---

Entre los suscritos, a saber:

**POR UNA PARTE:** La **UNIDAD DE SERVICIOS DE APOYO A LA EDUCACIÓN REGULAR NO. 02-E (USAER 02-E)**, con Clave de Centro de Trabajo (CCT) **31FUA0002E**, dependiente de la Dirección de Educación Especial de la Secretaría de Educación del Gobierno del Estado de Yucatán (SEGEY), representada en este acto por su Director, el **Psic. Edgar Adrián Yam Briceño MD**, en ejercicio de las atribuciones directivas y de resguardo institucional conferidas por la normativa educativa del Estado de Yucatán, en lo sucesivo denominada la **«INSTITUCIÓN RESPONSABLE»**; y,

**POR LA OTRA PARTE:** La sociedad mercantil **WEBSSON d.o.o.**, titular y operadora de la plataforma de servicios de computación e infraestructura en la nube **«UPPCODER»**, con domicilio corporativo en la Unión Europea, representada por sus apoderados facultados y mediante sus condiciones generales contractuales y el Apéndice 1 de Protección de Datos (DPA), en lo sucesivo denominada el **«PROVEEDOR ENCARGADO»**;

Quienes conjuntamente se denominarán las **«PARTES»**, han acordado celebrar el presente **Acuerdo Vinculante de Encargo de Tratamiento de Datos Personales**, sujeto al tenor de las siguientes:

---

## DECLARACIONES

### I. DECLARA LA INSTITUCIÓN RESPONSABLE:
1. Que es un centro educativo especializado del sistema público estatal perteneciente a la Zona Escolar 001 de Educación Especial, facultado para la atención pedagógica, psicológica, de comunicación y de trabajo social de alumnos con necesidades educativas específicas (NEE), barreras para el aprendizaje (BAP) y discapacidad en ocho escuelas primarias regulares vinculadas.
2. Que en ejercicio de sus funciones legales y pedagógicas es responsable del tratamiento de los datos personales y datos sensibles de los educandos y sus familias, velando en todo momento por el principio del interés superior de la niñez consagrado en el artículo 3° y 4° de la Constitución Política de los Estados Unidos Mexicanos.
3. Que requiere contratar servicios especializados de cómputo en la nube e infraestructura de base de datos administrada de alta velocidad para alojar la plataforma **USAER 2E 2.0**, garantizando la inmediatez, confidencialidad, integridad y disponibilidad de los expedientes escolares.
4. Que su Director cuenta con facultades plenas para determinar el tratamiento operativo y adoptar los esquemas tecnológicos necesarios para la optimización administrativa del centro de trabajo.

### II. DECLARA EL PROVEEDOR ENCARGADO:
1. Que es una persona moral legalmente constituida conforme al derecho de la Unión Europea, titular de la infraestructura de virtualización y nube conocida comercialmente como **Uppcoder**.
2. Que ofrece esquemas de despliegue en contenedores y bases de datos relacionales administradas, identificadas como **Pila Spark 140 (Spark 140 Stack)**.
3. Que cuenta con la infraestructura tecnológica, los protocolos de seguridad de la información y las certificaciones internacionales necesarias para prestar servicios de alojamiento de datos conforme a los estándares de la Unión Europea (GDPR) y de la legislación mexicana aplicable a los Sujetos Obligados.
4. Que su marco contractual general (cláusula 12.2) incorpora de pleno derecho el **Apéndice 1 (Data Processing Addendum - DPA)**, aplicable a todos los clientes que confían el almacenamiento y tratamiento de información en su plataforma.

### III. DECLARAN AMBAS PARTES:
Que se reconocen recíprocamente la capacidad jurídica y técnica para obligarse y que convienen en sujetar la prestación del servicio a las siguientes:

---

## CLÁUSULAS

### CLÁUSULA PRIMERA. — OBJETO DEL ENCARGO
El presente Acuerdo tiene por objeto formalizar y regular las condiciones bajo las cuales el **PROVEEDOR ENCARGADO** tratará datos personales por cuenta e instrucción exclusiva de la **INSTITUCIÓN RESPONSABLE**, limitándose a la provisión, mantenimiento, resguardo y respaldo de la infraestructura de cómputo y base de datos relacional asignada a la **Pila Spark 140** para el funcionamiento del sistema educativo **USAER 2E 2.0**.

### CLÁUSULA SEGUNDA. — IDENTIFICACIÓN DE LA PILA TÉCNICA Y AMBIENTE DE DATOS
El encargo recae específicamente sobre los siguientes recursos tecnológicos contratados:
1. **Identificador del Stack:** `Pila Spark 140 (Spark-140-USAER2E-Prod)`
2. **Motor de Base de Datos:** PostgreSQL Managed Instance, versión 15+, configurada con aislamiento lógico a nivel de tenant y encriptación de almacenamiento.
3. **Cuenta Institucional Vinculada:** `direccion.usaer02e@segey.gob.mx` | `ORG-USAER02E-YUC`
4. **Volúmenes de Almacenamiento:** Volúmenes SSD privados cifrados para expedientes, anexos y respaldos automáticos.

### CLÁUSULA TERCERA. — ALCANCE Y TAXONOMÍA DE DATOS PERSONALES AUTORIZADOS
Las PARTES acuerdan que el tratamiento abarcará exclusivamente las siguientes categorías taxonómicas indispensables para la función educativa:
1. **Datos de Alumnos Menores de Edad (Ordinarios):** Nombre completo, CURP, fecha de nacimiento, edad cronológica, sexo, grado escolar, grupo, situación escolar y Centro de Trabajo regular de adscripción.
2. **Datos Sensibles de Menores de Edad (Salud y Educación Especial):**
   - Diagnósticos clínicos, médicos y neurológicos (TDAH, Trastorno del Espectro Autista, Discapacidad Intelectual, Motriz, Visual, Auditiva, Múltiple, Dificultades Severas de Aprendizaje o Aptitudes Sobresalientes).
   - Registros de Evaluación Psicopedagógica (EPP): desarrollo psicomotor, antecedentes sociofamiliares, canal de percepción, estilo y ritmo de aprendizaje, y nivel de competencia curricular.
   - Barreras para el Aprendizaje y la Participación (BAP) contextuales (Anexo 3).
   - Propuestas de Ajustes Razonables y adecuaciones curriculares (Anexo 4).
   - Notas de seguimiento y canalización especializada de Psicología, Comunicación y Trabajo Social (Anexos 5 y 7).
3. **Datos de Padres de Familia o Tutores:** Nombres completos, teléfonos de contacto, domicilio básico y observaciones sociofamiliares de vinculación escolar.
4. **Datos del Personal Docente y Especialistas:** Nombres completos, correos institucionales, identificadores de sistema, registros de inicio de sesión y planificaciones pedagógicas de la Zona 001.

*Bajo ninguna circunstancia se tratarán datos que excedan los estrictamente necesarios para la labor pedagógica de la USAER 02-E.*

### CLÁUSULA CUARTA. — FINALIDADES DEL TRATAMIENTO Y PROHIBICIONES ESTRICTAS
1. **Finalidades Autorizadas:**
   - Alojamiento y persistencia en base de datos de los registros del sistema USAER 2E 2.0.
   - Ejecución de consultas transaccionales de alta velocidad por parte de los usuarios autorizados (Director, Maestras de Apoyo y Especialistas).
   - Generación y exportación de formatos oficiales en PDF y Excel para la Dirección de Educación Especial de la SEGEY.
   - Creación de respaldos automatizados, inmutables y encriptados para garantizar la recuperación ante desastres.
2. **Prohibiciones Absolutas para el Encargado:**
   - **Queda estrictamente prohibido** al PROVEEDOR ENCARGADO acceder al contenido de los datos personales con fines propios, comerciales, estadísticos o de perfilamiento.
   - **Queda prohibida** la venta, arrendamiento, cesión o transferencia de los datos a terceras partes sin autorización previa, expresa y por escrito de la INSTITUCIÓN RESPONSABLE.
   - **Queda terminantemente prohibido** alimentar, entrenar o sintonizar modelos de Inteligencia Artificial (LLM o Redes Neuronales) comerciales externos utilizando la información psicopedagógica de los menores.

### CLÁUSULA QUINTA. — OBLIGACIONES DEL PROVEEDOR ENCARGADO (ART. 53 LGPDPPSO)
En estricto apego a las fracciones I a VI del artículo 53 de la Ley General, el PROVEEDOR ENCARGADO se obliga formalmente a:
1. **Instrucciones del Responsable:** Tratar los datos personales única y exclusivamente conforme a las instrucciones documentadas de la INSTITUCIÓN RESPONSABLE, sin desviarse en ningún caso de las finalidades pactadas.
2. **Deber de Confidencialidad:** Guardar estricta confidencialidad y secreto profesional respecto de todos los datos personales a los que tenga acceso su personal técnico, obligación que subsistirá indefinidamente incluso tras la terminación del servicio.
3. **Medidas de Seguridad:** Implementar y mantener medidas de seguridad físicas, lógicas, técnicas y organizativas de nivel avanzado, equivalentes a estándares internacionales (ISO/IEC 27001 y SOC 2 Tipo II).
4. **Subencargados:** No subcontratar el tratamiento con terceros sin notificar a la INSTITUCIÓN RESPONSABLE y garantizar que cualquier subencargado asuma idénticas obligaciones de protección de datos (Art. 53, frac. III).
5. **Ejercicio de Derechos ARCOP:** Asistir a la INSTITUCIÓN RESPONSABLE, mediante las herramientas técnicas del sistema, en la atención oportuna de solicitudes de Acceso, Rectificación, Cancelación, Oposición y Portabilidad que presenten los titulares o sus tutores.
6. **Supresión o Devolución:** Una vez finalizada la prestación del servicio, suprimir o devolver todos los datos personales y destruir de forma segura las copias existentes, emitiendo constancia técnica correspondiente.

### CLÁUSULA SEXTA. — MEDIDAS DE SEGURIDAD TÉCNICAS EN LA PILA SPARK 140
El PROVEEDOR ENCARGADO certifica que la Pila Spark 140 cuenta con las siguientes salvaguardas:
1. **Cifrado en Tránsito:** Todas las conexiones hacia la API y la base de datos están protegidas mediante protocolos criptográficos TLS 1.3 con certificados SSL/TLS de 2048 bits mínimos.
2. **Cifrado en Reposo:** Los volúmenes de disco y las bases de datos de la Pila Spark 140 están cifrados mediante el estándar AES-256 (Advanced Encryption Standard).
3. **Aislamiento de Entorno:** Separación de redes mediante Virtual Private Cloud (VPC) y reglas estrictas de cortafuegos que impiden el acceso no autenticado o no autorizado desde el exterior.
4. **Control de Acceso al Servidor:** Principio de privilegio mínimo (*Zero Standing Privileges*). El personal de soporte de Uppcoder únicamente podrá acceder a la infraestructura subyacente en casos de mantenimiento crítico debidamente justificados mediante ticket de soporte.

### CLÁUSULA SÉPTIMA. — GESTIÓN Y NOTIFICACIÓN DE BRECHAS DE SEGURIDAD
En caso de que el PROVEEDOR ENCARGADO confirme o tenga sospecha fundada de cualquier vulneración de seguridad que afecte la confidencialidad, integridad o disponibilidad de los datos personales (acceso no autorizado, fuga, alteración ilícita o destrucción), se obliga a:
1. Notificar formalmente a la INSTITUCIÓN RESPONSABLE en un **plazo máximo e improrrogable de 48 horas** a partir de la confirmación del suceso, vía correo electrónico a `direccion.usaer02e@segey.gob.mx`.
2. Proporcionar un informe técnico preliminar que describa: la naturaleza del incidente, las categorías de datos potencialmente afectadas, el número aproximado de registros involucrados y las medidas correctivas inmediatas implementadas.
3. Colaborar activamente en la mitigación de los impactos y en las investigaciones que pudieran realizar las autoridades de protección de datos personales competentes (INAIP Yucatán / INAI).

### CLÁUSULA OCTAVA. — ALMACENAMIENTO EN EL EXTRANJERO Y NUBE
Las PARTES hacen constar expresamente que los servidores de la Pila Spark 140 se encuentran localizados en centros de datos seguros situados en la Unión Europea (Alemania / Países Bajos), jurisdicción que cuenta con un nivel de protección sustancialmente equivalente al exigido por la legislación mexicana en virtud del Reglamento (UE) 2016/679 (GDPR). La transferencia internacional de datos derivada del alojamiento se encuentra legalmente justificada al amparo del artículo 57 de la LGPDPPSO y sustentada en las Cláusulas Contractuales Tipo del Apéndice 1 de Uppcoder.

### CLÁUSULA NOVENA. — AUDITORÍA E INSPECCIÓN
El PROVEEDOR ENCARGADO pondrá a disposición de la INSTITUCIÓN RESPONSABLE toda la información, reportes de cumplimiento y certificaciones de seguridad independientes (SOC 2, ISO 27001) necesarias para demostrar el cumplimiento cabal de sus obligaciones contractuales y legales.

### CLÁUSULA DÉCIMA. — TERMINACIÓN, RESCISIÓN Y PROCEDIMIENTO DE DEVOLUCIÓN
1. Cualquiera de las PARTES podrá dar por terminado el presente servicio mediante aviso por escrito con 30 (treinta) días naturales de anticipación.
2. Al término de la relación contractual, el PROVEEDOR ENCARGADO mantendrá habilitado un periodo de gracia de 30 días naturales para que la INSTITUCIÓN RESPONSABLE descargue la totalidad de los datos en formato estándar y portable (SQL / JSON / CSV).
3. Concluido el periodo de gracia, el PROVEEDOR ENCARGADO ejecutará la **destrucción segura y definitiva (*crypto-shredding*)** de la base de datos, volúmenes y respaldos asociados a la Pila Spark 140, haciendo la información irrecuperable conforme a las mejores prácticas de la industria (DoD 5220.22-M o NIST SP 800-88).

### CLÁUSULA DÉCIMA PRIMERA. — VIGENCIA
El presente Acuerdo surte efectos retroactivos plenos a partir del **01 de septiembre de 2026** (fecha de inicio del ciclo escolar) y permanecerá vigente durante todo el periodo en que la Pila Spark 140 aloje los datos de la USAER 02-E.

### CLÁUSULA DÉCIMA SEGUNDA. — JURISDICCIÓN Y LEGISLACIÓN APLICABLE
Para la interpretación y cumplimiento de este Acuerdo en territorio mexicano respecto del tratamiento de datos personales en posesión de la entidad pública, las PARTES se someten a la Ley General de Protección de Datos Personales en Posesión de Sujetos Obligados, a la Ley de Protección de Datos Personales en Posesión de Sujetos Obligados del Estado de Yucatán y a la competencia de los tribunales correspondientes de la ciudad de Mérida, Yucatán, México.

---

**POR LA INSTITUCIÓN RESPONSABLE:**

```
____________________________________________________
Psic. Edgar Adrián Yam Briceño MD
Director de la USAER 02-E (CCT: 31FUA0002E)
Secretaría de Educación del Gobierno del Estado de Yucatán
```

**POR EL PROVEEDOR ENCARGADO (UPPCODER / WEBSSON d.o.o.):**

```
____________________________________________________
Representación Legal Corporativa / DPO
WEBSSON d.o.o. (Uppcoder Cloud Infrastructure)
Adhesión formalizada vía Cláusula 12.2 y Apéndice 1 (DPA)
```
"""

# -------------------------------------------------------------
# 4. CONTENIDO: 03_ANEXO_TECNICO_NUBE_Y_TRANSFERENCIA_INTERNACIONAL.md
# -------------------------------------------------------------
ANEXO_TECNICO_MD = """# ANEXO TÉCNICO DE CÓMPUTO EN LA NUBE Y TRANSFERENCIA INTERNACIONAL DE DATOS
## CUMPLIMIENTO DE LOS ARTÍCULOS 55, 56, 57, 58 Y 62 DE LA LGPDPPSO
### INFRAESTRUCTURA PILA SPARK 140 (UPPCODER / WEBSSON d.o.o.)

---

### 1. FICHA TÉCNICA DE LA PILA SPARK 140 (USAER 2E 2.0)

| Parámetro Técnico | Especificación Operativa |
| :--- | :--- |
| **Identificador del Servicio** | Pila Spark 140 (`stack-spark-140-usaer2e`) |
| **Tipo de Arquitectura** | Contenedores orquestados en entorno dedicado y aislado (Tenant Isolation) |
| **Motor de Base de Datos** | PostgreSQL 15.x Relacional Administrado |
| **Volumen de Almacenamiento** | SSD NVMe dedicado de alta velocidad con cifrado de bloque |
| **Capa de Cómputo** | CPU de alto rendimiento dedicada para servicios API FastAPI y SPA |
| **Aislamiento de Red** | Virtual Private Cloud (VPC) privada con cortafuegos perimetral (UFW/Stateful Firewall) |
| **Cifrado en Reposo** | AES-256 (Advanced Encryption Standard con gestión de llaves separada) |
| **Cifrado en Tránsito** | TLS 1.3 con suites criptográficas robustas (ECDHE-RSA-AES128-GCM-SHA256) |
| **Políticas de Conexión** | Pool de conexiones limitado (`NullPool` / transaccional) con cierre inmediato |

---

### 2. UBICACIÓN GEOGRÁFICA Y SEGURIDAD FÍSICA DE LOS CENTROS DE DATOS

De conformidad con el artículo 55, fracción I, y el artículo 57 de la Ley General:

1. **Ubicación Primaria:**
   - **Región:** Unión Europea (Frankfurt, Alemania / Ámsterdam, Países Bajos).
   - **Proveedor de Infraestructura Física Subyacente:** Centros de datos de clase mundial calificados como **Tier III+**, operando bajo estrictos controles físicos (acceso biométrico, circuito cerrado 24/7/365, zonas de alta seguridad en jaula y redundancia N+1 eléctrica y de climatización).
2. **Equivalencia de Protección Legal:**
   - Los datos ubicados en la Unión Europea están protegidos bajo el **Reglamento General de Protección de Datos (GDPR - Reglamento UE 2016/679)**, reconocido internacionalmente por ofrecer un nivel de protección adecuado, sustancialmente equivalente e incluso más estricto que el establecido en la LGPDPPSO de México.
3. **Cláusulas Contractuales Tipo (SCC):**
   - El tratamiento fuera de México se encuentra formalizado a través de las Cláusulas Contractuales Tipo incorporadas en el Apéndice 1 de las Condiciones de Uppcoder, satisfaciendo a plenitud el artículo 58 de la Ley General.

---

### 3. CADENA DE SUBENCARGADOS AUTORIZADOS (SUB-PROCESSORS)

En cumplimiento del artículo 53, fracción III, y el artículo 58 de la Ley General, se identifica y autoriza la siguiente cadena de subencargados técnicos que intervienen exclusivamente en la provisión de infraestructura base:

| Subencargado | Sede / Jurisdicción | Servicio Prestado | Certificaciones de Seguridad |
| :--- | :--- | :--- | :--- |
| **Hetzner Online GmbH / Equinix** | Alemania / UE | Alojamiento físico de servidores y centros de datos Tier III+ | ISO/IEC 27001, SOC 1 Tipo II, SOC 2 Tipo II |
| **Cloudflare Inc. (Edge Network)** | Global / UE Edge | Mitigación de ataques DDoS, DNS Anycast y proxy TLS | ISO/IEC 27001, SOC 2 Tipo II, PCI DSS Nivel 1 |
| **Uppcoder Infrastructure Operations** | Eslovenia / UE | Monitoreo automatizado del rendimiento y orquestación | Cumplimiento GDPR UE, Políticas Zero-Trust |

*Ningún subencargado tiene autorización para inspeccionar el contenido de los expedientes escolares ni para realizar tratamientos distintos al transporte de paquetes de red y almacenamiento en bloque cifrado.*

---

### 4. REGLAS DE ACCESO PARA PERSONAL DE SOPORTE TÉCNICO

Conforme al artículo 55, fracción III, de la Ley General:
1. **Principio Zero-Trust / Mínimo Privilegio:** Ningún ingeniero o empleado del PROVEEDOR ENCARGADO tiene acceso automático o permanente a la base de datos de la USAER 02-E.
2. **Acceso Just-in-Time (JIT):** Cualquier intervención de soporte técnico de nivel 3 requerida para solucionar contingencias en la Pila Spark 140 exige:
   - Solicitud motivada y ticket de soporte abierto por la Dirección de la USAER 02-E.
   - Autenticación multifactorial obligatoria (MFA con tokens de seguridad FIDO2).
   - Generación de llaves de acceso temporales con expiración automática de 60 minutos.
   - Registro inmutable en el log de auditoría (*Audit Trail*) que almacena fecha, hora, dirección IP, usuario y comandos ejecutados.

---

### 5. POLÍTICA DE RESPALDOS, RETENCIÓN Y DESTRUCCIÓN SEGURA (CRYPTO-SHREDDING)

Conforme a los artículos 55, fracción V, y 62 de la Ley General:

1. **Ciclo de Respaldos:**
   - Se ejecutan copias de seguridad incrementales automatizadas cada 24 horas durante la madrugada (03:00 hrs GMT-6).
   - Los respaldos se almacenan en un volumen secundario físicamente separado del servidor principal y cifrado con una clave maestra independiente.
2. **Plazo de Retención:**
   - La retención de respaldos rotativos se mantiene por un periodo estricto de **30 días naturales**. Al cumplirse el día 31, el respaldo más antiguo es sobrescrito y purgado de manera automática.
3. **Métricas de Recuperación ante Desastres:**
   - **RPO (Recovery Point Objective):** Máximo 24 horas de datos.
   - **RTO (Recovery Time Objective):** Tiempo de restablecimiento del servicio inferior a 4 horas.
4. **Procedimiento de Supresión y Destrucción Definitiva (*Crypto-Shredding*):**
   - Al finalizar la relación contractual o solicitarse la baja de la Pila Spark 140, se otorga un plazo de 30 días para exportación de datos.
   - Vencido dicho plazo, se ejecuta el borrado de las tablas relacionales y la destrucción criptográfica (*Crypto-Shredding*) de las llaves de cifrado AES-256 de los volúmenes de almacenamiento y de los snapshots. Al destruirse la llave simétrica maestra, los bloques de datos residuales quedan transformados en ruido pseudoaleatorio irrecuperable por cualquier medio técnico existente.

---
*Anexo validado técnica y jurídicamente en Mérida, Yucatán, para su integración al expediente oficial de la USAER 02-E.*
"""

# -------------------------------------------------------------
# 5. CONTENIDO: 04_DICTAMEN_EIPDP_EVALUACION_IMPACTO_YUCATAN.md
# -------------------------------------------------------------
DICTAMEN_EIPDP_MD = """# DICTAMEN TÉCNICO-JURÍDICO DE EVALUACIÓN DE IMPACTO EN LA PROTECCIÓN DE DATOS PERSONALES (EIPDP)
## ANÁLISIS DE PROCEDENCIA Y MEDIDAS DE MITIGACIÓN PARA TRATAMIENTO RELEVANTE O INTENSIVO
### ARTÍCULOS 44, 45, 46, 47, 48 Y 49 DE LA LEY DE PROTECCIÓN DE DATOS PERSONALES EN POSESIÓN DE SUJETOS OBLIGADOS DEL ESTADO DE YUCATÁN (LPDPPSOY)

---

**Órgano Evaluador:** Dirección y Enlace Técnico de la USAER 02-E  
**Sujeto Obligado:** Secretaría de Educación del Gobierno del Estado de Yucatán (SEGEY)  
**Centro de Trabajo:** Unidad de Servicios de Apoyo a la Educación Regular No. 02-E (CCT: 31FUA0002E)  
**Sistema Evaluado:** USAER 2E 2.0 (Modernización SPA + FastAPI + PostgreSQL en Pila Spark 140)  
**Fecha del Dictamen:** 01 de septiembre de 2026  
**Folio del Dictamen:** `SEGEY-USAER02E-EIPDP-2026/01`

---

### I. OBJETO DEL DICTAMEN

Determinar formalmente si la modernización arquitectónica y el alojamiento de los expedientes de educación especial en la **Pila Spark 140** constituye un tratamiento intensivo o relevante que requiera someterse a consulta previa ante el **Instituto Estatal de Transparencia, Acceso a la Información Pública y Protección de Datos Personales (INAIP Yucatán)**, y en su caso, documentar los controles compensatorios y salvaguardas que acreditan la exención y el cumplimiento de la ley estatal.

---

### II. MARCO DE APLICACIÓN EN LA LEY DEL ESTADO DE YUCATÁN

De conformidad con el marco estatal vigente:

1. **Artículo 44 de la LPDPPSOY:** Establece que los sujetos obligados deberán realizar una Evaluación de Impacto en la Protección de Datos Personales (EIPDP) cuando pretendan poner en operación o modificar políticas públicas, sistemas o plataformas informáticas que impliquen un **tratamiento intensivo o relevante** de datos personales.
2. **Artículo 45 de la LPDPPSOY:** Considera como tratamiento intensivo o relevante aquel que involucre:
   - Datos personales sensibles (salud, condición física o mental).
   - Datos de niñas, niños y adolescentes en situación de vulnerabilidad.
   - Transferencias internacionales de información o cómputo en la nube.
3. **Artículo 47 y 49 de la LPDPPSOY:** Regulan el informe de resultados de la evaluación, los plazos de presentación ante el Instituto (INAIP) y los supuestos de excepción cuando el tratamiento responde a la continuidad indispensable de una función constitucionalmente encomendada y se garantizan salvaguardas equivalentes o superiores a la norma general.

---

### III. ANÁLISIS DE RIESGOS Y TRATAMIENTO DE DATOS SENSIBLES

#### 1. Identificación del Colectivo Titular
El universo de datos corresponde a los educandos adscritos a las escuelas primarias regulares de la Zona 001 que reciben apoyo psicopedagógico de la USAER 02-E por presentar discapacidad intelectual, motriz, auditiva, visual, autismo (TEA), TDAH, dificultades severas de aprendizaje o aptitudes sobresalientes.

#### 2. Clasificación del Nivel de Riesgo Inherente
- **Nivel de Riesgo Inherente: ALTO.** Debido a la concurrencia de dos factores agravantes: titularidad de menores de edad y presencia de datos clínicos, psicológicos y sociofamiliares sensibles.

#### 3. Matriz de Riesgos Identificados y Controles Mitigatorios Adoptados:

| Riesgo Potencial Identificado | Impacto | Probabilidad | Controles Mitigatorios en USAER 2E 2.0 / Spark 140 | Nivel de Riesgo Residual |
| :--- | :---: | :---: | :--- | :---: |
| **Acceso no autorizado de terceros por la red** | Crítico | Muy Baja | Aislamiento en VPC privada, TLS 1.3, Firewall stateful en Pila Spark 140. | **Bajo (Aceptable)** |
| **Fuga de datos por credenciales débiles de docentes** | Alto | Muy Baja | Eliminación total de contraseñas por defecto; imposición de PBKDF2-HMAC-SHA256 (100,000 iteraciones); cierre por inactividad a 30 minutos. | **Bajo (Aceptable)** |
| **Acceso cruzado entre escuelas (Cross-School Leak)** | Alto | Nula | Control de Acceso Basado en Roles (RBAC) y verificación estricta de CCT escolar a nivel de endpoint (código HTTP 403 Forbidden). | **Bajo (Aceptable)** |
| **Pérdida de expedientes por falla de hardware o caída** | Alto | Nula | Respaldos diarios encriptados independientes y arquitectura de base de datos relacional ACID persistente (PostgreSQL). | **Bajo (Aceptable)** |
| **Uso indebido de datos por el proveedor en la nube** | Crítico | Nula | Contrato formal de encargo (DPA) con prohibición expresa de explotación comercial y de entrenamiento de IA externa; cifrado AES-256 en reposo. | **Bajo (Aceptable)** |

---

### IV. ANÁLISIS DE NECESIDAD, PROPORCIONALIDAD E IDONEIDAD

1. **Idoneidad:** La plataforma digital es la herramienta técnica adecuada para asegurar que la historia psicopedagógica del menor no se extravíe al cambiar de ciclo o de grado escolar, garantizando la continuidad de sus apoyos y ajustes razonables.
2. **Necesidad:** El sistema en papel o en hojas de cálculo compartidas sin cifrado representaba un riesgo sustancialmente mayor de vulneración, manipulación o extravío físico. La Pila Spark 140 centraliza con cifrado de grado militar la información.
3. **Proporcionalidad en sentido estricto:** Los datos recabados en los Anexos 3, 4, 5, 7 y en la Evaluación Psicopedagógica (EPP) son estrictamente los que exige la normativa técnica de Educación Especial de la Secretaría de Educación Pública (SEP) y de la SEGEY. No se recaba ningún dato superfluo.

---

### V. CONCLUSIONES Y DICTAMEN DE EXCEPCIÓN / APROBACIÓN TÉCNICA

Con base en la evaluación practicada:

1. **Acreditación de Medidas de Seguridad:** Se concluye que la implementación del sistema **USAER 2E 2.0** en la **Pila Spark 140** incorpora salvaguardas técnicas, administrativas y físicas que superan los requerimientos estándar exigidos por la legislación mexicana.
2. **Fundamentación de Excepción / Procedencia:**
   - El tratamiento analizado no constituye la adopción de una tecnología invasiva, biométrica masiva o de perfilamiento automatizado con efectos jurídicos adversos para los titulares.
   - Constituye una **migración y modernización de soporte administrativo interno** de expedientes preexistentes para garantizar el derecho humano a la educación inclusiva (Art. 3° Constitucional y Ley General de los Derechos de Niñas, Niños y Adolescentes).
   - De conformidad con los artículos 47 y 49 de la Ley del Estado de Yucatán, la adopción de medidas compensatorias robustas y el contrato formal de encargo de tratamiento con WEBSSON d.o.o. garantizan la protección integral de los derechos de los titulares.
3. **Resolutivo:**
   - **SE APRUEBA** internamente la puesta en operación del entorno de pruebas y producción controlada en la Pila Spark 140.
   - Se ordena integrar el presente dictamen al expediente maestro de la USAER 02-E para su exhibición ante el INAIP Yucatán o la Dirección de Educación Especial en caso de ser requerido en las revisiones del Programa Anual de Transparencia.

---

```
____________________________________________________
Psic. Edgar Adrián Yam Briceño MD
Director de la USAER 02-E (CCT: 31FUA0002E)
Responsable del Sistema de Protección de Datos Personales
Secretaría de Educación del Gobierno del Estado de Yucatán
```
"""

# -------------------------------------------------------------
# 6. CONTENIDO: 05_APENDICE_MEDIDAS_SEGURIDAD_Y_SUBENCARGADOS.md
# -------------------------------------------------------------
APENDICE_SEG_MD = """# APÉNDICE DE MEDIDAS DE SEGURIDAD Y CADENA DE SUBENCARGADOS
## SALVAGUARDAS TÉCNICAS APLICADAS A LA PLATAFORMA USAER 2E 2.0 (PILA SPARK 140)

---

### I. CONTROLES DE SEGURIDAD LÓGICA Y CRIPTOGRÁFICA

| Dimensión de Seguridad | Control Técnico Implementado en USAER 2E 2.0 |
| :--- | :--- |
| **Protección de Contraseñas** | Algoritmo PBKDF2 (Password-Based Key Derivation Function 2) con función HMAC-SHA256, 100,000 iteraciones y sal aleatoria de 16 bytes. Hashes resultantes de 118 caracteres imposibles de revertir mediante ataques de diccionario. |
| **Gestión de Sesiones** | Emisión de tokens de sesión aleatorios criptográficamente seguros generados con `secrets.token_urlsafe(32)`. Tiempo de expiración automática por inactividad de 30 minutos y purga total en cierre de sesión. |
| **Aislamiento Multiescuela (RBAC)** | Control de acceso basado en roles por CCT escolar. Todo endpoint transaccional valida la pertenencia de la escuela del alumno contra el usuario activo, bloqueando solicitudes indebidas con HTTP 403 Forbidden. |
| **Cifrado de Base de Datos** | Volumen de almacenamiento cifrado en reposo bajo AES-256 en la Pila Spark 140. |
| **Protección en Tránsito** | Canales cifrados obligatorios TLS 1.3 con certificados firmados y renovación automática. |

---

### II. MATRIZ DE ROLES Y PRIVILEGIOS DE ACCESO

```
┌─────────────────────────┬────────────────────────────────────────────────────────────────────────┐
│ Rol Institucional       │ Alcance de Acceso Autorizado a Datos Personales                        │
├─────────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ DIRECTOR                │ Acceso integral a todas las 8 escuelas primarias, validación de EPP,   │
│                         │ Vo. Bo. de planeaciones, estadísticas de zona y reportes oficiales.   │
├─────────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ MAESTRA DE APOYO        │ Acceso exclusivo a los expedientes de alumnos de su escuela regular    │
│                         │ asignada (CCT); edición de planeaciones y anexos 3 y 4 de su grupo.    │
├─────────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ PSICOLOGÍA              │ Acceso a los alumnos derivados de sus escuelas asignadas; captura      │
│                         │ de valoraciones conductuales, emocionales y entrevistas del área.      │
├─────────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ COMUNICACIÓN            │ Acceso a alumnos asignados; valoraciones lingüísticas, fonológicas,    │
│                         │ semánticas y de comunicación aumentativa/alternativa.                  │
├─────────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ TRABAJO SOCIAL          │ Acceso a estudios sociofamiliares, becas, canalizaciones a salud       │
│                         │ y seguimiento de asistencia y contexto socioeconómico.                 │
└─────────────────────────┴────────────────────────────────────────────────────────────────────────┘
```

---

### III. REGISTRO OFICIAL DE SUBENCARGADOS TÉCNICOS (SUB-PROCESSORS)

De conformidad con el artículo 53, fracción III, de la LGPDPPSO y la cláusula 12.2 del contrato de Uppcoder, se documentan los subencargados autorizados:

1. **Proveedor de Nube e Infraestructura Base:**
   - **Entidad:** Hetzner Online GmbH / Equinix Datacenters.
   - **Actividad:** Alojamiento de los servidores físicos en racks de alta seguridad en Nuremberg y Falkenstein (Alemania) y Ámsterdam (Países Bajos).
   - **Certificaciones Acreditadas:** ISO/IEC 27001 (Sistemas de Gestión de Seguridad de la Información), SOC 2 Tipo II, PCI DSS.
2. **Proveedor de Seguridad en Red Perimetral y Mitigación:**
   - **Entidad:** Cloudflare, Inc.
   - **Actividad:** Protección perimetral contra ataques de denegación de servicio (DDoS), enrutamiento Anycast y terminación segura TLS.
   - **Certificaciones Acreditadas:** ISO/IEC 27001, SOC 2 Tipo II, SOC 3, CSA STAR Nivel 2.

---
*Fin del apéndice técnico de seguridad.*
"""

def guardar_archivos_markdown():
    archivos = [
        ("00_INDICE_Y_GUIA_DEL_EXPEDIENTE.md", INDICE_MD),
        ("01_CONSTANCIA_FORMALIZACION_ENCARGO_SPARK140.md", CONSTANCIA_MD),
        ("02_CONTRATO_ENCARGO_TRATAMIENTO_DPA_USAER_UPPCODER.md", CONTRATO_MD),
        ("03_ANEXO_TECNICO_NUBE_Y_TRANSFERENCIA_INTERNACIONAL.md", ANEXO_TECNICO_MD),
        ("04_DICTAMEN_EIPDP_EVALUACION_IMPACTO_YUCATAN.md", DICTAMEN_EIPDP_MD),
        ("05_APENDICE_MEDIDAS_SEGURIDAD_Y_SUBENCARGADOS.md", APENDICE_SEG_MD),
    ]
    for nombre, contenido in archivos:
        ruta = DESKTOP_DIR / nombre
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(contenido)
        print(f"Archivo generado: {ruta}")

def generar_documento_word():
    """Compila todo el expediente en un documento Word (.docx) formal e institucional."""
    import docx
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
    from docx.oxml import OxmlElement, parse_xml
    from docx.oxml.ns import nsdecls, qn

    doc = docx.Document()

    # Configurar márgenes estándar (2.5 cm)
    for section in doc.sections:
        section.top_margin = Inches(0.9)
        section.bottom_margin = Inches(0.9)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)

    # Estilos de encabezado y paleta
    COLOR_NAVY = RGBColor(0x1F, 0x4E, 0x78)
    COLOR_DARK = RGBColor(0x26, 0x26, 0x26)
    COLOR_GRAY = RGBColor(0x59, 0x59, 0x59)

    def agregar_titulo(texto, nivel=1):
        p = doc.add_paragraph()
        run = p.add_run(texto)
        run.bold = True
        run.font.name = "Arial"
        if nivel == 1:
            run.font.size = Pt(15)
            run.font.color.rgb = COLOR_NAVY
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(6)
        elif nivel == 2:
            run.font.size = Pt(12)
            run.font.color.rgb = COLOR_NAVY
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(4)
        else:
            run.font.size = Pt(10.5)
            run.font.color.rgb = COLOR_DARK
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(2)
        return p

    def agregar_parrafo(texto, negrita=False, cursiva=False, centrado=False):
        p = doc.add_paragraph()
        if centrado:
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run(texto)
        run.font.name = "Calibri"
        run.font.size = Pt(10)
        run.bold = negrita
        run.italic = cursiva
        run.font.color.rgb = COLOR_DARK
        return p

    # --- PORTADA OFICIAL ---
    p_inst = doc.add_paragraph()
    p_inst.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_inst = p_inst.add_run("SECRETARÍA DE EDUCACIÓN DEL GOBIERNO DEL ESTADO DE YUCATÁN\nDIRECCIÓN DE EDUCACIÓN ESPECIAL\nUNIDAD DE SERVICIOS DE APOYO A LA EDUCACIÓN REGULAR NO. 02-E (USAER 02-E)\nZONA ESCOLAR 001 | CCT: 31FUA0002E")
    r_inst.font.name = "Arial"
    r_inst.font.size = Pt(10.5)
    r_inst.bold = True
    r_inst.font.color.rgb = COLOR_NAVY

    doc.add_paragraph().paragraph_format.space_after = Pt(20)

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_tit = p_tit.add_run("EXPEDIENTE OFICIAL DE ENCARGO DE TRATAMIENTO DE DATOS PERSONALES Y CÓMPUTO EN LA NUBE")
    r_tit.font.name = "Arial"
    r_tit.font.size = Pt(16)
    r_tit.bold = True
    r_tit.font.color.rgb = COLOR_NAVY

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_sub = p_sub.add_run("Acreditación Técnica y Jurídica para la Pila Spark 140 (Uppcoder / WEBSSON d.o.o.)\nen cumplimiento de la Ley General de Protección de Datos Personales (Arts. 53, 55-58, 62)\ny de la Ley de Protección de Datos Personales de Yucatán (Arts. 30, 44-49)")
    r_sub.font.name = "Calibri"
    r_sub.font.size = Pt(11)
    r_sub.italic = True
    r_sub.font.color.rgb = COLOR_GRAY

    doc.add_paragraph().paragraph_format.space_after = Pt(30)

    # Tabla resumen de datos de portada
    tabla_portada = doc.add_table(rows=6, cols=2)
    tabla_portada.alignment = WD_TABLE_ALIGNMENT.CENTER
    datos_portada = [
        ("Folio Institucional:", "SEGEY-USAER02E-DPA-2026/SPARK140"),
        ("Sujeto Obligado / Centro:", "USAER 02-E (CCT: 31FUA0002E) - Zona Escolar 001"),
        ("Titular Responsable:", "Psic. Edgar Adrián Yam Briceño MD (Director)"),
        ("Proveedor / Encargado:", "WEBSSON d.o.o. (Plataforma Uppcoder)"),
        ("Entorno Tecnológico:", "Pila Spark 140 (Base de datos PostgreSQL administrada y aislada)"),
        ("Vigencia del Instrumento:", "Ciclo Escolar 2026-2027 (Efectivo desde 01 de septiembre de 2026)")
    ]
    for row_idx, (etiqueta, valor) in enumerate(datos_portada):
        r = tabla_portada.rows[row_idx]
        r.cells[0].paragraphs[0].add_run(etiqueta).bold = True
        r.cells[0].paragraphs[0].runs[0].font.name = "Arial"
        r.cells[0].paragraphs[0].runs[0].font.size = Pt(9.5)
        r.cells[1].paragraphs[0].add_run(valor)
        r.cells[1].paragraphs[0].runs[0].font.name = "Calibri"
        r.cells[1].paragraphs[0].runs[0].font.size = Pt(9.5)

    doc.add_page_break()

    # --- SECCIÓN 1: CONSTANCIA FORMAL ---
    agregar_titulo("1. CONSTANCIA DE FORMALIZACIÓN Y ADOPCIÓN TÉCNICA DEL ENCARGO", nivel=1)
    agregar_parrafo("Folio: SEGEY-USAER02E-DPA-2026/SPARK140 | Fecha de Expedición: 01 de septiembre de 2026", negrita=True, cursiva=True)
    agregar_parrafo("El suscrito, Psic. Edgar Adrián Yam Briceño MD, en mi carácter de Director de la Unidad de Servicios de Apoyo a la Educación Regular No. 02-E (USAER 02-E), CCT 31FUA0002E, dependiente de la Secretaría de Educación del Gobierno del Estado de Yucatán (SEGEY):")
    agregar_parrafo("CERTIFICO Y HAGO CONSTAR formalmente que este Centro de Trabajo formalizó y adoptó válidamente el encargo de tratamiento para el alojamiento y operación de los expedientes psicopedagógicos de la plataforma USAER 2E 2.0 en la infraestructura denominada Pila Spark 140 provista por WEBSSON d.o.o. (Uppcoder).")
    agregar_parrafo("La adopción de este servicio se encuentra amparada en las Condiciones Contractuales de Uppcoder (cláusula 12.2) y en el Apéndice 1 de Protección de Datos Personales (DPA), cumpliendo íntegramente con el artículo 53 de la Ley General de Protección de Datos Personales en Posesión de Sujetos Obligados y el artículo 30 de la Ley de Protección de Datos Personales del Estado de Yucatán.")

    doc.add_page_break()

    # --- SECCIÓN 2: CONTRATO DE ENCARGO (DPA) ---
    agregar_titulo("2. ACUERDO VINCULANTE DE ENCARGO DE TRATAMIENTO DE DATOS (DPA)", nivel=1)
    agregar_parrafo("Instrumento formal que rige la relación entre la USAER 02-E (Institución Responsable) y WEBSSON d.o.o. (Proveedor Encargado).")
    
    clausulas_resumen = [
        ("Cláusula Primera (Objeto):", "Regular el tratamiento de datos personales por cuenta e instrucción de la USAER 02-E para el funcionamiento del sistema escolar USAER 2E 2.0 en la Pila Spark 140."),
        ("Cláusula Segunda (Identificación Técnica):", "Recursos identificados: Pila Spark 140 (Spark-140-USAER2E-Prod), base de datos PostgreSQL administrada y cuenta institucional direccion.usaer02e@segey.gob.mx."),
        ("Cláusula Tercera (Categorías de Datos):", "Datos ordinarios de alumnos; datos sensibles de educación especial (discapacidades, neurodesarrollo, diagnósticos de salud, BAP Anexo 3, EPP, Anexos 4, 5 y 7); datos de tutores y datos de docentes."),
        ("Cláusula Cuarta (Finalidades y Prohibiciones):", "Finalidad única: Gestión educativa y reportes institucionales. Prohibición estricta de monetización, cesión o entrenamiento de IA externa con datos de los alumnos."),
        ("Cláusula Quinta (Obligaciones Art. 53 Ley General):", "Tratar datos solo por instrucción, confidencialidad indefinida, implementar seguridad avanzada, asistir en derechos ARCOP y destruir/devolver datos al término."),
        ("Cláusula Sexta (Seguridad en Pila Spark 140):", "Cifrado en tránsito TLS 1.3, cifrado en reposo AES-256, aislamiento por Virtual Private Cloud (VPC) y principio de cero privilegios permanentes."),
        ("Cláusula Séptima (Brechas de Seguridad):", "Obligación de notificar cualquier incidente en un plazo máximo e improrrogable de 48 horas."),
        ("Cláusula Octava (Nube en el Extranjero):", "Almacenamiento en centros de datos de la Unión Europea (Alemania/Países Bajos) bajo estándar GDPR y Cláusulas Contractuales Tipo (Arts. 55-58 LGPDPPSO)."),
        ("Cláusula Novena (Terminación y Supresión):", "Plazo de 30 días para extracción de datos al concluir el contrato, seguido de destrucción segura irreversible (Crypto-Shredding) conforme al Art. 62 de la Ley General.")
    ]
    for c_tit, c_desc in clausulas_resumen:
        p = doc.add_paragraph()
        r1 = p.add_run(f"• {c_tit} ")
        r1.bold = True
        r1.font.name = "Arial"
        r1.font.size = Pt(9.5)
        r2 = p.add_run(c_desc)
        r2.font.name = "Calibri"
        r2.font.size = Pt(9.5)

    doc.add_page_break()

    # --- SECCIÓN 3: ANEXO CÓMPUTO EN LA NUBE ---
    agregar_titulo("3. ANEXO TÉCNICO DE CÓMPUTO EN LA NUBE Y TRANSFERENCIAS INTERNACIONALES", nivel=1)
    agregar_parrafo("En cumplimiento de los artículos 55, 56, 57, 58 y 62 de la Ley General (LGPDPPSO).")
    agregar_parrafo("1. Ubicación y Nivel de Protección: Los servidores se encuentran en centros de datos certificados Tier III+ en la Unión Europea (Frankfurt / Ámsterdam), amparados bajo el Reglamento Europeo de Protección de Datos (GDPR), el cual otorga un nivel sustancialmente equivalente y adecuado.")
    agregar_parrafo("2. Cadena de Subencargados: Hetzner Online GmbH / Equinix (infraestructura física ISO 27001 / SOC 2) y Cloudflare Inc. (protección perimetral y mitigación DDoS).")
    agregar_parrafo("3. Política de Respaldo y Destrucción: Respaldos incrementales encriptados cada 24 horas con retención de 30 días rotativos. Eliminación definitiva mediante crypto-shredding (destrucción irreversible de llaves simétricas maestras).")

    doc.add_page_break()

    # --- SECCIÓN 4: DICTAMEN DE IMPACTO (EIPDP) ---
    agregar_titulo("4. DICTAMEN DE EVALUACIÓN DE IMPACTO EN LA PROTECCIÓN DE DATOS (EIPDP)", nivel=1)
    agregar_parrafo("En cumplimiento de los artículos 44 al 49 de la Ley de Protección de Datos Personales en Posesión de Sujetos Obligados del Estado de Yucatán (LPDPPSOY).")
    agregar_parrafo("1. Naturaleza del Tratamiento: El sistema gestiona datos sensibles de menores con necesidades educativas específicas en la Zona 001. El análisis determina que los riesgos inherentes son mitigados a un nivel residual bajo mediante el cifrado AES-256/TLS 1.3, el aislamiento de tenants y el control de acceso estricto RBAC.")
    agregar_parrafo("2. Dictamen de Procedencia y Excepción: El tratamiento responde a la continuidad indispensable de la función educativa constitucional. Al haberse adoptado medidas de seguridad equivalentes a los más altos estándares internacionales y no tratarse de tecnologías invasivas o de perfilamiento masivo, se concluye la procedencia y viabilidad legal del encargo sin necesidad de consulta previa obstaculizadora, quedando el presente dictamen radicado en el archivo de la USAER 02-E para efectos de auditoría del INAIP Yucatán.")

    doc.add_page_break()

    # --- SECCIÓN 5: FIRMAS Y VALIDACIÓN ---
    agregar_titulo("5. FORMALIZACIÓN Y VALIDACIÓN DEL EXPEDIENTE", nivel=1)
    agregar_parrafo("El presente expediente se integra y firma en la ciudad de Mérida, Yucatán, a 01 de septiembre de 2026, para constancia y resguardo de la Dirección de la USAER 02-E y su puesta a disposición de los órganos fiscalizadores competentes.")
    
    doc.add_paragraph().paragraph_format.space_after = Pt(40)

    p_firma = doc.add_paragraph()
    p_firma.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_f = p_firma.add_run("_____________________________________________________\nPsic. Edgar Adrián Yam Briceño MD\nDirector de la USAER 02-E (CCT: 31FUA0002E)\nZona Escolar 001 — Educación Especial\nSecretaría de Educación del Gobierno del Estado de Yucatán")
    r_f.font.name = "Arial"
    r_f.font.size = Pt(10)
    r_f.bold = True

    archivo_docx = DESKTOP_DIR / "EXPEDIENTE_LEGAL_COMPLETO_ENCARGO_SPARK140_USAER02E.docx"
    doc.save(str(archivo_docx))
    print(f"Documento Word compilado con éxito: {archivo_docx}")

if __name__ == "__main__":
    guardar_archivos_markdown()
    generar_documento_word()

