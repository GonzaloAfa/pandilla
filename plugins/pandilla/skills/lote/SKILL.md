---
name: lote
description: >-
  Lanza un lote de pedidos o tickets en paralelo, cada uno en su propio git worktree: alineación previa con el usuario (una ronda de preguntas con respuesta recomendada), en bugs un comando rojo con el síntoma exacto antes de tocar código, implementación, compuertas, /panel con re-revisión, prueba local completa rojo/verde (todo el flujo arriba, sin atajos, navegador si lo ve una persona), regresión de flujos críticos y un único PR (o un commit local, según el perfil del proyecto). Usa T3 Code si está disponible y, si no, subagentes de Claude Code con worktree. Usar con "/lote "pedido 1" "pedido 2"", "/lote ABC-12 ABC-13", "lanza un lote", "trabaja estos pedidos en paralelo".
---

# /lote

Orquestas; no implementas. Cada pedido es una tarea con su worktree. Las tareas corren solas y tú llevas el tablero de estado y el resumen final.

Lee primero el perfil del proyecto. **Dónde está el perfil.** En orden: `<raíz>/.claude/pandilla.md` (versionado en el repo), o `~/.claude/pandilla/perfiles/<repo>.md` (local, para repos donde no se puede commitear; `<repo>` es el nombre de la carpeta del checkout principal: `basename "$(dirname "$(cd "$(git rev-parse --git-common-dir)" && pwd)")"`, así funciona igual desde un worktree). Los revisores propios están junto al perfil: `<raíz>/.claude/pandilla/revisores/` o `~/.claude/pandilla/perfiles/<repo>/revisores/`. En adelante, «el perfil» es el que encontraste. Si no hay ninguno, para y propone `/pandilla:iniciar`: sin perfil no sabes la base, las compuertas, cómo aislar los worktrees ni qué está prohibido. 

El tablero (`/pandilla:tablero`) muestra el lote en vivo: un pizarrón con el título y los pedidos, 4 habitaciones (una por tarea activa, con su paso del flujo y lo que hace ahora), 2 sillas de espera para la cola, y los hitos. **Tú mantienes el pizarrón** con `python3 <plugin>/scripts/pizarron.py` (`<plugin>` es la carpeta dos niveles arriba de esta skill); `<repo>` es el nombre de la carpeta del checkout principal:

- al terminar «Preparar»: `pizarron.py lote --repo <repo> --titulo "<título corto del lote>" --tarea "<ID>|<título>" …` (todas quedan en espera);
- al despachar cada una: `pizarron.py tarea --repo <repo> --id <ID> --estado activa --rama <rama>` (y `--worktree <ruta>` si la conoces);
- al terminar cada una: `--estado lista --pr "<PR #n o rama + commit>"` o `--estado bloqueada --pr "<motivo corto>"`;
- al cerrar el lote: `pizarron.py cerrar --repo <repo>`.

## 0. Motor

- **T3 Code** (existe la herramienta `delegate_task`): cada tarea es un hilo de T3 con su worktree. Es una sesión completa: corre su propio /panel. El hilo de T3 tiene que estar en el proyecto del repo (el worktree se crea en el proyecto del hilo). Llama a `orchestrator_capabilities` una vez por hilo.
- **Claude Code nativo** (no hay `delegate_task`): cada tarea es un `Agent` con `isolation: "worktree"`, `subagent_type: "general-purpose"` y `run_in_background: true`. Un subagente no puede lanzar subagentes, así que **el /panel y la revisión independiente los corres tú** sobre su worktree, y le devuelves los hallazgos con `SendMessage`. El brief cambia en el paso 4 (ver abajo).

## 1. Preparar

- **Entrada:** según «Pedidos» del perfil: texto (`/lote "arreglar X" "agregar Y"`), tickets (lee cada uno con la herramienta del gestor: Linear, GitHub Issues, Jira…) o un archivo con un pedido por sección. Por cada uno: título corto, problema, arreglo esperado, cómo se prueba.
- **Recursos:** `df -h /` (con menos de 40 GB libres, avisa), `git worktree list`, y lo que pida el perfil (por ejemplo `docker ps`).
- **Alinear (obligatorio):** sigue `<plugin>/referencias/alinear.md` con todos los pedidos. Tú verificas los hechos (la premisa en la base, el síntoma, el código actual); el usuario toma las decisiones, en una ronda de preguntas numeradas con tu respuesta recomendada. Un pedido cuya premisa ya no se cumple no se lanza sin una decisión del usuario. Ningún pedido se despacha con una decisión abierta.
- **Complementos:** corre `<plugin>/scripts/complementos.sh` una vez y aplica `<plugin>/referencias/complementos.md` en cada paso, con los instalados y sin los que el perfil apague. En cada brief, la línea «Complementos» lista los que le tocan a esa tarea (nombre y ruta). Si faltan los recomendados, dilo una vez en la tabla del lote y propone `/pandilla:iniciar --complementos`.
- Descarta, explicando por qué, los pedidos que:
  - escriben en producción o necesitan datos reales (backfills, migraciones de datos, scripts contra prod);
  - publican o mandan algo de verdad (correos, mensajes, push, cobros, builds de tienda, despliegues manuales);
  - tocan secretos, `.env*` o credenciales;
  - cambian una regla de negocio que el usuario no decidió en la alineación;
  - tocan los mismos archivos que otro pedido del lote, o agregan migración a la vez que otro (van en serie);
  - lo que el perfil liste en «Prohibido para las tareas».
- **Radio en producción:** si el perfil permite medir prod (sección «Producción») y un pedido cambia comportamiento sobre datos existentes, mide tú, antes de lanzar, cuántos casos reales caen en lo que cambia, con las reglas del perfil (solo lectura, solo agregados). Ese número va en el brief. Las tareas nunca consultan prod: corren sin supervisión y leen texto de terceros, y una instrucción inyectada podría llegar a una herramienta con permisos.
- **Flujo a probar por pedido.** Antes de lanzar, escribe para cada pedido el flujo completo que la tarea tendrá que recorrer en la prueba local: por dónde entra quien lo usa (pantalla, API pública, webhook), cada servicio y paso por el que pasa (login, pago, jobs, eventos), dónde se ve el resultado y si va en navegador (sí, siempre que lo vea un usuario final, un cliente o un operador). Va en el brief, en «Prueba completa». Un brief sin ese flujo no se despacha.
- Con la alineación cerrada, muestra la tabla del lote (pedido · tipo · decisiones · flujo a probar) y lanza sin esperar más si el usuario ya pidió lanzarlo.

## 2. Despachar

- Máximo de tareas activas: el del perfil (por defecto 4). El resto queda en cola.
- **T3:** `delegate_task` con `isolation: "worktree"`, `role: "implementation"`, `mode: "async"`, `title: "<id> · <resumen>"` y `task` = el brief completo. No hagas polling: sigue el `next` de cada delegate y espera sus notificaciones.
- **Nativo:** `Agent` con `isolation: "worktree"`, `run_in_background: true`, `description: "<id> · <resumen>"` y el brief. Lanza los de la primera tanda en un solo mensaje. Espera las notificaciones.

## 3. Seguir y cerrar

- Tabla de estado: en cola → implementando → panel → arreglando → re-revisión → prueba local → listo / bloqueado.
- Cuando una tarea termina, registra su última línea y lanza la siguiente de la cola.
- **En nativo, el panel es tuyo:** cuando una tarea dice «LISTO PARA PANEL <ruta del worktree> <rama>», corre `/pandilla:panel` sobre ese worktree (con el pedido como `--pedido`) y mándale el informe con `SendMessage`. Ella corrige y vuelve a avisar; tú corres `--re-revision`. Máximo 3 vueltas. Con APROBADO, mándale «APROBADO: sigue al paso de regresión y commit».
- **Revisión independiente por cada entrega** (obligatoria; el panel local no la reemplaza): una sesión nueva con contexto limpio, nunca tú ni la tarea que implementó.
  - Con «Publicación: pr»: la revisión de PR del perfil (por ejemplo una skill `/review-pr` que comenta en el PR) sobre `#<n>`, sin aprobar ni pedir cambios, leyendo con `git fetch origin pull/<n>/head:refs/remotes/pr/<n>`.
  - Con «Publicación: local»: `/code-review high` sobre `git diff <base>...<rama>`, solo lectura.
  - En T3, lánzala con `delegate_task` `role: "review"` sin worktree. En nativo, con un `Agent` `general-purpose` nuevo.
  - Si deja C, W o SEC confirmados, pásaselos a la tarea que implementó: corrige y sube los commits al mismo PR (o a la misma rama), y lanza otra revisión.
- Si una tarea pregunta algo que solo el usuario puede decidir, pásale la pregunta tal cual.
- **Verifica tú la prueba local antes de aceptar una entrega**, y si está `reality-checker`, lánzalo además sobre la evidencia (ver complementos). Lee la tabla de cobertura y abre la evidencia (capturas, logs). Devuélvela a la tarea si: falta un paso del flujo del brief, un paso no es `real` (función llamada a mano, evento publicado a mano, estado forzado), un servicio del flujo estaba abajo, falta el rojo en la base, o lo ve una persona y no hay capturas del navegador. El informe de la tarea no basta: «lo probé» sin tabla y evidencia no cuenta.
- **En un `bug`, verifica también el comando rojo:** que compruebe el síntoma exacto del brief, que haya evidencia de que el arnés hizo lo que debía (el rojo no vino del script), que la causa confirmada y las hipótesis descartadas estén en el informe y que no quede ningún `[DEBUG-`. Una tarea que termina en «NO SE REPRODUCE» no es un fracaso: revisa su evidencia y propón al usuario cerrar el ticket o pedir más datos.
- **Listo para merge:** panel APROBADO, compuertas verdes, prueba local completa verificada por ti, regresión OK, revisión independiente sin C ni SEC y, con PR, la CI verde. Nunca digas «listo» con algo «no probado» o «pendiente» en el informe.
- **Nunca mergees.** Lo decide el usuario. Si el perfil dice qué pasa después del merge (despliegue automático, algo manual pendiente), dilo por cada PR.
- Al final: resumen por pedido (PR o rama, veredicto del panel, vueltas, qué se probó y la evidencia, pendientes) en la carpeta de informes del perfil (por defecto `tmp/lotes/<AAAAMMDD-HHMM>.md`, ignorada por git).

## Brief de cada tarea (copiar y completar)

```
Eres el agente de implementación de «<título>». Trabajas solo en este worktree. Al terminar, tu última línea debe ser una de:
PR <URL completa>, head <SHA>, checks <estado>          (si el perfil publica PRs)
RAMA <nombre>, commit <SHA>, compuertas <estado>         (si el perfil es local)
NO SE REPRODUCE: <resumen y ruta de la evidencia>        (solo bug)
BLOQUEADO: <motivo>

## Pedido
<problema, arreglo esperado, cómo se prueba; spec, ticket o docs que aplican>
<radio en producción medido por el orquestador, si aplica>

## Decisiones
<el bloque que deja la alineación: tipo, premisa, síntoma exacto (bug), decisiones con quién las tomó, fuera de alcance>
Si al implementar aparece una decisión que no está aquí, no la tomes tú: BLOQUEADO con la pregunta y tu respuesta recomendada.

## Complementos
<los de referencias/complementos.md que le tocan a esta tarea, con su ruta; «ninguno» si no aplica. Cárgalos en el paso que indica cada uno>

## Prueba completa
<entrada real (pantalla, API pública, webhook) → cada servicio y paso del flujo (login, pago, jobs, eventos) → dónde se ve el resultado; navegador: sí/no y por qué; casos rojo/verde>

## Flujo obligatorio
0. Rama y entorno:
   - `git checkout -b <rama según el perfil> <base>`.
   - Prepara el worktree con el comando de «Entorno» del perfil. Si el perfil define un envoltorio (`wt`), cada comando del proyecto va con él: el entorno no persiste entre comandos. Nunca uses los puertos ni las bases del checkout principal que lista el perfil.
1. Lee CLAUDE.md (o AGENTS.md), el perfil y los docs del área.
   - Tipo `bug`: sigue `<ruta absoluta del plugin>/referencias/bug-rojo.md` completo antes de tocar código: comando rojo con el síntoma exacto y el arnés verificado, caso reducido, 3–5 hipótesis, logs `[DEBUG-xxxx]`, test que falla, arreglo. Si no se reproduce: termina con «NO SE REPRODUCE».
   - Tipo `cambio`: muestra el comportamiento actual en local antes de cambiarlo (un test o la pantalla).
2. Antes de escribir código, el «Mapa de reutilización» de `<ruta absoluta del plugin>/referencias/diseno-simple.md` en tu informe: qué existente reutilizas (buscado con `git grep` por el concepto) y, por cada pieza nueva, por qué no sirve lo que hay. Después implementa el cambio mínimo y correcto, con las «Reglas del proyecto» del perfil y las cuatro preguntas de ese documento. Si cambia algo visible o una regla, actualiza en este mismo paso los docs del área: el panel los revisa en la primera vuelta.
3. Compuertas rápidas del perfil (formato, lint, tipos, tests unitarios) y `<ruta absoluta del plugin>/scripts/duplicados.sh <base>`: un duplicado de código nuevo se reutiliza o se justifica en el mapa. La primera vez que pasan, corre `/simplify` sobre tu diff (reutilización, simplificación, capas que sobran), aplica lo que mejore sin cambiar el comportamiento y repite las compuertas.
4. Panel:
   - [T3] Corre /pandilla:panel sobre tu rama. Corrige los C y W confirmados o plausibles; los S a tu criterio (anota cuáles dejaste). Repite el paso 3 y corre `/pandilla:panel --re-revision <informe>`. Máximo 3 vueltas; si en la tercera sigue habiendo C o W: BLOQUEADO.
   - [nativo] Escribe «LISTO PARA PANEL <ruta del worktree> <rama>» y espera. El orquestador corre el panel y te manda el informe; corrige los C y W, repite el paso 3 y vuelve a avisar. Sigue cuando recibas «APROBADO».
5. Prueba local COMPLETA rojo → verde (OBLIGATORIA Y ESTRICTA): sigue las reglas del paso 3 de la skill /pandilla:entrega. Todos los servicios del flujo arriba; el flujo de «Prueba completa» de este brief recorrido de punta a punta por su entrada real (pantalla, API pública, webhook), sin llamar funciones internas ni publicar eventos a mano ni forzar estados; navegador con capturas si lo ve un usuario final, un cliente o un operador; rojo en la base y verde en la rama por la misma vía. Deja la tabla de cobertura (paso · real/sembrado · base · rama · evidencia) en la carpeta de informes. Si no puedes completarla: BLOQUEADO con el motivo, nunca «pendiente». Además, las compuertas lentas del perfil (integración, e2e). Los recursos compartidos van en la fila que diga el perfil (`fila.sh` u otra, como un runner con `--wait`), como comando en segundo plano esperado sin polling.
6. Regresión (OBLIGATORIA): sigue la sección «Regresión» de la skill /pandilla:entrega con los «Flujos críticos» del perfil. Nunca consultes producción. Si necesitas un número real, pídelo en tu informe final: lo mide el orquestador. Si sale RIESGO, arregla y vuelve al paso 3.
7. Con el panel APROBADO, la prueba verde y la regresión OK:
   - `git diff --numstat <base>`: ningún archivo ajeno con líneas borradas; ningún secreto ni dato real.
   - Un solo commit con el formato del perfil, con el código y los docs del paso 2.
   - Según «Publicación» del perfil: push y un PR con el veredicto del panel, la evidencia y la tabla de regresión en el cuerpo (un solo push); o sin push, con el informe en la carpeta de informes.
8. Al cerrar, libera el entorno con el comando de «Entorno» del perfil.

## Reglas
- Nunca escribas en producción ni publiques nada. Si hace falta: BLOQUEADO y explica.
- Nunca toques `.env*`, secretos ni credenciales.
- No crees infra de test nueva; usa la que hay.
- No uses `git stash`, no mergees la base en tu rama y revisa `git status` antes de cualquier reset.
- No uses subagentes salvo los que lanza /pandilla:panel.
- <reglas del proyecto del perfil>
```
