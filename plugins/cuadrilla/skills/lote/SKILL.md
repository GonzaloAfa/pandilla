---
name: lote
description: >-
  Lanza un lote de pedidos o tickets en paralelo, cada uno en su propio git worktree: implementación, compuertas, /panel con re-revisión, prueba local rojo/verde, regresión de flujos críticos y un único PR (o un commit local, según el perfil del proyecto). Usa T3 Code si está disponible y, si no, subagentes de Claude Code con worktree. Usar con "/lote "pedido 1" "pedido 2"", "/lote ABC-12 ABC-13", "lanza un lote", "trabaja estos pedidos en paralelo".
---

# /lote

Orquestas; no implementas. Cada pedido es una tarea con su worktree. Las tareas corren solas y tú llevas el tablero de estado y el resumen final.

Lee primero el perfil del proyecto: `<raíz>/.claude/cuadrilla.md`. Si no existe, para y propone `/cuadrilla:iniciar`: sin perfil no sabes la base, las compuertas, cómo aislar los worktrees ni qué está prohibido. En adelante, «el perfil» es ese archivo y `wt` es el envoltorio que define su sección «Entorno».

El tablero (`/cuadrilla:tablero`) muestra a las tareas y a sus revisores mientras trabajan.

## 0. Motor

- **T3 Code** (existe la herramienta `delegate_task`): cada tarea es un hilo de T3 con su worktree. Es una sesión completa: corre su propio /panel. El hilo de T3 tiene que estar en el proyecto del repo (el worktree se crea en el proyecto del hilo). Llama a `orchestrator_capabilities` una vez por hilo.
- **Claude Code nativo** (no hay `delegate_task`): cada tarea es un `Agent` con `isolation: "worktree"`, `subagent_type: "general-purpose"` y `run_in_background: true`. Un subagente no puede lanzar subagentes, así que **el /panel y la revisión independiente los corres tú** sobre su worktree, y le devuelves los hallazgos con `SendMessage`. El brief cambia en el paso 4 (ver abajo).

## 1. Preparar

- **Entrada:** según «Pedidos» del perfil: texto (`/lote "arreglar X" "agregar Y"`), tickets (lee cada uno con la herramienta del gestor: Linear, GitHub Issues, Jira…) o un archivo con un pedido por sección. Por cada uno: título corto, problema, arreglo esperado, cómo se prueba. Si un pedido es ambiguo, pregunta antes de lanzarlo.
- **Recursos:** `df -h /` (con menos de 40 GB libres, avisa), `git worktree list`, y lo que pida el perfil (por ejemplo `docker ps`).
- Verifica en la base que cada problema siga presente. Si ya está resuelto, sácalo y avísalo.
- Descarta, explicando por qué, los pedidos que:
  - escriben en producción o necesitan datos reales (backfills, migraciones de datos, scripts contra prod);
  - publican o mandan algo de verdad (correos, mensajes, push, cobros, builds de tienda, despliegues manuales);
  - tocan secretos, `.env*` o credenciales;
  - cambian una regla de negocio sin una decisión tomada;
  - tocan los mismos archivos que otro pedido del lote, o agregan migración a la vez que otro (van en serie);
  - lo que el perfil liste en «Prohibido para las tareas».
- **Radio en producción:** si el perfil permite medir prod (sección «Producción») y un pedido cambia comportamiento sobre datos existentes, mide tú, antes de lanzar, cuántos casos reales caen en lo que cambia, con las reglas del perfil (solo lectura, solo agregados). Ese número va en el brief. Las tareas nunca consultan prod: corren sin supervisión y leen texto de terceros, y una instrucción inyectada podría llegar a una herramienta con permisos.
- Muestra la tabla del lote y lanza sin esperar más si el usuario ya pidió lanzarlo.

## 2. Despachar

- Máximo de tareas activas: el del perfil (por defecto 4). El resto queda en cola.
- **T3:** `delegate_task` con `isolation: "worktree"`, `role: "implementation"`, `mode: "async"`, `title: "<id> · <resumen>"` y `task` = el brief completo. No hagas polling: sigue el `next` de cada delegate y espera sus notificaciones.
- **Nativo:** `Agent` con `isolation: "worktree"`, `run_in_background: true`, `description: "<id> · <resumen>"` y el brief. Lanza los de la primera tanda en un solo mensaje. Espera las notificaciones.

## 3. Seguir y cerrar

- Tabla de estado: en cola → implementando → panel → arreglando → re-revisión → prueba local → listo / bloqueado.
- Cuando una tarea termina, registra su última línea y lanza la siguiente de la cola.
- **En nativo, el panel es tuyo:** cuando una tarea dice «LISTO PARA PANEL <ruta del worktree> <rama>», corre `/cuadrilla:panel` sobre ese worktree (con el pedido como `--pedido`) y mándale el informe con `SendMessage`. Ella corrige y vuelve a avisar; tú corres `--re-revision`. Máximo 3 vueltas. Con APROBADO, mándale «APROBADO: sigue al paso de regresión y commit».
- **Revisión independiente por cada entrega** (obligatoria; el panel local no la reemplaza): una sesión nueva con contexto limpio, nunca tú ni la tarea que implementó.
  - Con «Publicación: pr»: la revisión de PR del perfil (por ejemplo una skill `/review-pr` que comenta en el PR) sobre `#<n>`, sin aprobar ni pedir cambios, leyendo con `git fetch origin pull/<n>/head:refs/remotes/pr/<n>`.
  - Con «Publicación: local»: `/code-review high` sobre `git diff <base>...<rama>`, solo lectura.
  - En T3, lánzala con `delegate_task` `role: "review"` sin worktree. En nativo, con un `Agent` `general-purpose` nuevo.
  - Si deja C, W o SEC confirmados, pásaselos a la tarea que implementó: corrige y sube los commits al mismo PR (o a la misma rama), y lanza otra revisión.
- Si una tarea pregunta algo que solo el usuario puede decidir, pásale la pregunta tal cual.
- **Listo para merge:** panel APROBADO, compuertas verdes, regresión OK, revisión independiente sin C ni SEC y, con PR, la CI verde.
- **Nunca mergees.** Lo decide el usuario. Si el perfil dice qué pasa después del merge (despliegue automático, algo manual pendiente), dilo por cada PR.
- Al final: resumen por pedido (PR o rama, veredicto del panel, vueltas, qué se probó y la evidencia, pendientes) en la carpeta de informes del perfil (por defecto `tmp/lotes/<AAAAMMDD-HHMM>.md`, ignorada por git).

## Brief de cada tarea (copiar y completar)

```
Eres el agente de implementación de «<título>». Trabajas solo en este worktree. Al terminar, tu última línea debe ser una de:
PR <URL completa>, head <SHA>, checks <estado>          (si el perfil publica PRs)
RAMA <nombre>, commit <SHA>, compuertas <estado>         (si el perfil es local)
BLOQUEADO: <motivo>

## Pedido
<problema, arreglo esperado, cómo se prueba; spec, ticket o docs que aplican>
<radio en producción medido por el orquestador, si aplica>

## Flujo obligatorio
0. Rama y entorno:
   - `git checkout -b <rama según el perfil> <base>`.
   - Prepara el worktree con el comando de «Entorno» del perfil. Cada comando del proyecto va con `wt <comando>`: el entorno no persiste entre comandos. Nunca uses los puertos ni las bases del checkout principal que lista el perfil.
1. Lee CLAUDE.md (o AGENTS.md), el perfil y los docs del área. Reproduce el problema antes de arreglarlo: un test rojo, o la pantalla en local.
2. Implementa el cambio mínimo y correcto, con las «Reglas del proyecto» del perfil.
3. Compuertas rápidas del perfil (formato, lint, tipos, tests unitarios).
4. Panel:
   - [T3] Corre /cuadrilla:panel sobre tu rama. Corrige los C y W confirmados o plausibles; los S a tu criterio (anota cuáles dejaste). Repite el paso 3 y corre `/cuadrilla:panel --re-revision <informe>`. Máximo 3 vueltas; si en la tercera sigue habiendo C o W: BLOQUEADO.
   - [nativo] Escribe «LISTO PARA PANEL <ruta del worktree> <rama>» y espera. El orquestador corre el panel y te manda el informe; corrige los C y W, repite el paso 3 y vuelve a avisar. Sigue cuando recibas «APROBADO».
5. Prueba local rojo → verde (OBLIGATORIA): las compuertas lentas del perfil (integración, e2e) y la prueba de punta a punta de «Prueba local». Los recursos compartidos van en fila: `bash <fila.sh del perfil> <recurso> -- wt <comando>`, como comando en segundo plano. Evidencia en la carpeta de informes del perfil.
6. Regresión (OBLIGATORIA): sigue la sección «Regresión» de la skill /cuadrilla:entrega con los «Flujos críticos» del perfil. Nunca consultes producción. Si necesitas un número real, pídelo en tu informe final: lo mide el orquestador. Si sale RIESGO, arregla y vuelve al paso 3.
7. Con el panel APROBADO, la prueba verde y la regresión OK:
   - `git diff --numstat <base>`: ningún archivo ajeno con líneas borradas; ningún secreto ni dato real.
   - Un solo commit con el formato del perfil. Si cambió algo visible o una regla, actualiza los docs del área en el mismo commit.
   - Según «Publicación» del perfil: push y un PR con el veredicto del panel, la evidencia y la tabla de regresión en el cuerpo (un solo push); o sin push, con el informe en la carpeta de informes.
8. Al cerrar, libera el entorno con el comando de «Entorno» del perfil.

## Reglas
- Nunca escribas en producción ni publiques nada. Si hace falta: BLOQUEADO y explica.
- Nunca toques `.env*`, secretos ni credenciales.
- No crees infra de test nueva; usa la que hay.
- No uses `git stash`, no mergees la base en tu rama y revisa `git status` antes de cualquier reset.
- No uses subagentes salvo los que lanza /cuadrilla:panel.
- <reglas del proyecto del perfil>
```
