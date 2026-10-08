# AGENTS.md — USAER 2E

## 1. Propósito del proyecto

USAER 2E es un sistema de información educativo integrado para apoyar la
gestión administrativa y pedagógica de una USAER.

NO debe limitarse a digitalizar formatos ni trasladar burocracia del papel
a una pantalla.

Principio central:

> Capturar una vez y reutilizar después.

La información de alumnos, docentes, escuelas y procesos debe formar parte
de un sistema conectado. Los diferentes módulos son ventanas hacia una misma
historia educativa, no sistemas independientes.

Objetivos:

- Reducir captura duplicada.
- Automatizar tareas administrativas repetitivas.
- Conservar la trayectoria educativa de los alumnos.
- Conectar información entre módulos.
- Generar productos administrativos a partir de datos existentes.
- Facilitar posteriormente análisis y apoyo a decisiones pedagógicas.
- Reducir la dependencia de procesos manuales realizados por el director.

La tecnología debe liberar tiempo para la atención educativa, no crear
nueva burocracia digital.


## 2. Principio de arquitectura

USAER 2E debe evolucionar de prototipo funcional a producto mantenible.

No aceptar como criterio suficiente:

> "Funciona."

Una solución debe procurar ser:

- comprensible
- mantenible
- modular
- verificable
- reutilizable
- segura
- escalable razonablemente

Evitar soluciones rápidas que generen deuda técnica innecesaria.


## 3. Regla fundamental antes de modificar código

Antes de modificar una función, estructura de datos, servicio, repositorio
o módulo:

1. Identificar quién lo utiliza.
2. Buscar dependencias en otros módulos.
3. Evaluar posibles regresiones.
4. Mantener compatibilidad cuando sea razonable.
5. Probar los flujos afectados después del cambio.

Una corrección local NO se considera exitosa si rompe otro módulo.

Evitar el patrón:

> arreglar una cosa y romper diez.


## 4. Fuente única de verdad

Los datos fundamentales deben tener una representación canónica.

Ejemplos:

- alumnos
- escuelas
- docentes
- ciclos escolares
- servicios
- expedientes
- usuarios y roles

Evitar que cada módulo mantenga su propia versión incompatible de los
mismos datos.

Cuando un dato ya existe, reutilizarlo en lugar de solicitar nuevamente
su captura.


## 5. Separación de responsabilidades

Siempre que sea razonable, separar:

### Interfaz
Streamlit presenta información y captura acciones del usuario.

### Lógica de negocio
Servicios y funciones contienen las reglas del sistema.

### Acceso a datos
Repositorios gestionan Google Sheets, bases de datos u otras fuentes.

Evitar colocar lógica crítica directamente dentro de las pantallas de
Streamlit.

Idealmente:

UI → Servicios → Repositorios → Datos


## 6. Contratos entre módulos

Las interfaces entre componentes deben ser previsibles.

Si una función como `repo.alumnos()` cambia su estructura de salida,
primero identificar todos los consumidores.

Evitar cambios silenciosos en:

- nombres de columnas
- tipos de datos
- estructuras retornadas
- identificadores
- parámetros
- permisos
- rutas

Si un contrato debe cambiar, actualizar conscientemente sus consumidores.


## 7. Pruebas y regresiones

Los flujos críticos deben ir adquiriendo pruebas automáticas.

Priorizar pruebas para:

- autenticación
- roles y permisos
- padrón de alumnos
- alta y modificación de alumnos
- filtros por maestra/escuela
- carga masiva
- expedientes
- eventos
- actas
- mapas
- hojas de eventos
- generación de documentos
- integraciones con Google Sheets

Cada bug importante corregido debe considerarse candidato para una prueba
de regresión.


## 8. Cambios pequeños y verificables

Preferir cambios pequeños sobre grandes reescrituras.

Antes de realizar una refactorización extensa:

1. explicar el problema arquitectónico;
2. identificar componentes afectados;
3. proponer una estrategia;
4. conservar comportamiento existente cuando sea posible;
5. verificar después del cambio.

No reescribir componentes estables únicamente porque exista una solución
más elegante.


## 9. Parches temporales

Un parche temporal puede utilizarse para resolver una emergencia, pero debe:

- quedar claramente identificado;
- explicar por qué existe;
- evitar convertirse en una dependencia permanente;
- ser eliminado o refactorizado cuando sea posible.

Nunca construir nuevas capas de funcionalidad encima de un parche frágil
sin revisar primero su diseño.


## 10. Automatización y autonomía

Principio organizacional:

> Automatizar la rutina; reservar la intervención humana para aquello que
> requiere criterio.

USAER 2E debe funcionar normalmente sin que Edgar tenga que iniciar sesión
para habilitar manualmente procesos rutinarios.

Evitar procesos que requieran constantemente:

- cambiar permisos manualmente;
- subir archivos manualmente;
- copiar información entre módulos;
- autorizar operaciones ordinarias sin necesidad;
- intervenir como intermediario técnico.

La dirección debe supervisar el sistema, no convertirse en su middleware
humano.


## 11. Independencia técnica de Edgar

USAER 2E tampoco debe depender de que solamente Edgar comprenda cómo
funciona internamente.

El proyecto debe tender a que otro desarrollador competente pueda:

- comprender la arquitectura;
- localizar los datos;
- entender los módulos;
- ejecutar el proyecto;
- diagnosticar errores;
- realizar cambios;
- ejecutar pruebas;
- desplegarlo;

sin depender de conocimiento almacenado únicamente en la memoria de Edgar.


## 12. Documentación

Documentar especialmente:

- decisiones arquitectónicas;
- contratos importantes;
- dependencias no evidentes;
- configuraciones necesarias;
- integraciones externas;
- procesos de despliegue;
- decisiones cuya razón no sea evidente leyendo el código.

No documentar cada línea.

Documentar principalmente el **por qué**.


## 13. Desarrollo y producción

Cuando sea posible:

- experimentar en desarrollo;
- probar antes de desplegar;
- proteger datos reales;
- evitar experimentar directamente sobre producción;
- disponer de mecanismos razonables de recuperación.

Una funcionalidad nueva no debe comprometer la estabilidad de los procesos
que ya utiliza el personal.


## 14. Manejo de errores

Evitar fallos silenciosos.

Los errores deben proporcionar información suficiente para determinar:

- qué operación falló;
- dónde falló;
- qué componente estuvo involucrado;

sin exponer información sensible al usuario.

Cuando sea apropiado, implementar logging y trazabilidad.


## 15. Seguridad y privacidad

USAER 2E trabaja con información educativa.

Aplicar el principio de mínimo privilegio.

Nunca:

- exponer credenciales;
- colocar secretos directamente en el repositorio;
- mostrar información a usuarios sin autorización;
- ampliar permisos simplemente para solucionar rápidamente un error.

Las decisiones de comodidad no deben comprometer privacidad o seguridad.


## 16. Filosofía UX

La plataforma debe reducir carga cognitiva y administrativa.

Antes de agregar un campo preguntar:

> ¿USAER 2E ya conoce esta información?

Antes de agregar un nuevo formulario preguntar:

> ¿Podemos producirlo utilizando información que ya existe?

Antes de agregar un nuevo módulo preguntar:

> ¿Debe ser realmente independiente o es otra vista de información que el
> sistema ya conoce?


## 17. Criterio para nuevas funcionalidades

Antes de implementar una función nueva evaluar:

1. ¿Qué problema real resuelve?
2. ¿Quién la utilizará?
3. ¿Qué información necesita?
4. ¿Esa información ya existe?
5. ¿Con qué módulos debe comunicarse?
6. ¿Introduce duplicidad?
7. ¿Introduce una nueva dependencia?
8. ¿Qué podría romper?
9. ¿Cómo comprobaremos que funciona?
10. ¿Simplifica realmente el trabajo?


## 18. Instrucciones para Codex

Antes de realizar cambios importantes:

1. inspeccionar la estructura existente;
2. leer este archivo;
3. localizar los componentes relevantes;
4. buscar dependencias;
5. explicar brevemente el plan;
6. implementar el cambio más pequeño razonable;
7. ejecutar las pruebas disponibles;
8. revisar posibles regresiones;
9. informar qué cambió y qué se verificó.

No asumir que una solución es correcta únicamente porque compila o porque
la pantalla funciona.

Cuando una solicitud pueda resolverse de dos maneras, preferir aquella que
mantenga la arquitectura más clara y reduzca deuda técnica, salvo que la
complejidad añadida no esté justificada.


## 19. Principio rector

USAER 2E debe ser capaz de crecer sin convertirse en una colección de
parches conectados entre sí.

La prioridad no es solamente construir más rápido.

La prioridad es construir un sistema que podamos seguir entendiendo,
manteniendo y mejorando conforme crezca.
