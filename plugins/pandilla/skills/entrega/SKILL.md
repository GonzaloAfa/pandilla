---
name: entrega
description: >-
  Ciclo completo para llevar un cambio hasta «listo para merge» en el checkout y la rama actuales: alineación con el usuario, en bugs un comando rojo con el síntoma exacto, compuertas, /panel con re-revisión, prueba local completa rojo/verde (todo el flujo arriba, sin atajos, navegador si lo ve una persona), regresión de flujos críticos, un commit, un PR (o commit local según el perfil), revisión independiente en sesión limpia, correcciones y resumen final. Usar con "/entrega", "llévalo a PR", "déjalo listo para merge", o al terminar de implementar algo. Invocarla autoriza el commit y, si el perfil publica PRs, el push y el PR de ESTA tarea; nunca el merge.
---

# /entrega

El mismo flujo que hace cada tarea de `/pandilla:lote`, para una sola tarea y en el checkout actual. Sirve para no tener que preguntar paso a paso «¿probaste en local?», «¿corriste la revisión?» o «¿ya está listo?».

Lee primero el perfil del proyecto. **Dónde está el perfil.** En orden: `<raíz>/.claude/pandilla.md` (versionado en el repo), o `~/.claude/pandilla/perfiles/<repo>.md` (local, para repos donde no se puede commitear; `<repo>` es el nombre de la carpeta del checkout principal: `basename "$(dirname "$(cd "$(git rev-parse --git-common-dir)" && pwd)")"`, así funciona igual desde un worktree). Los revisores propios están junto al perfil: `<raíz>/.claude/pandilla/revisores/` o `~/.claude/pandilla/perfiles/<repo>/revisores/`. En adelante, «el perfil» es el que encontraste. Si no hay ninguno, propone `/pandilla:iniciar`; si el usuario quiere seguir igual, pregunta la base, las compuertas y si se publica PR.

Argumentos: `--pedido "<texto>"` (o un ticket), `--base <rama>`, `--sin-regresion` (solo cambios sin lógica: docs, textos; dilo en el resumen), `--pr <n>` (retoma con el PR ya abierto, desde el paso 6).

Lleva una lista de pasos visible y actualízala en cada paso.

**Complementos:** al empezar, corre `<plugin>/scripts/complementos.sh` y aplica `<plugin>/referencias/complementos.md` en cada paso con los instalados (y sin los que el perfil apague). Los que falten no bloquean: dilo una vez en el resumen y propone `/pandilla:iniciar --complementos`.

## 0. Antes de empezar

- La rama no puede ser la base ni una rama de release. Si lo es, crea una según el perfil.
- `git status` y `git log <base>..HEAD --oneline`: el diff tiene que ser solo de esta tarea. Si ves cambios ajenos, para y pregunta. Si el checkout principal está sucio con trabajo ajeno, trabaja en un worktree (`git worktree add ../<repo>-<slug> -b <rama> <base>`), prepáralo con «Entorno» del perfil y avísalo.
- Lee el pedido, `CLAUDE.md` y los docs del área.
- **Alinear (obligatorio):** sigue `<plugin>/referencias/alinear.md` (`<plugin>` es la carpeta dos niveles arriba de esta skill). Si el cambio ya está implementado, la ronda incluye las decisiones que el diff tomó sin que nadie las pidiera: confírmalas con el usuario. Guarda el bloque de «Decisiones» en la carpeta de informes y pásalo al panel con el pedido.
- **Tipo `bug`:** sigue `<plugin>/referencias/bug-rojo.md` antes de arreglar. Si el arreglo ya está hecho, construye el comando rojo igual y córrelo en la base, en un worktree temporal (§Regresión 3): tiene que salir rojo ahí con el síntoma exacto y verde en la rama. Si no se reproduce en la base, para y díselo al usuario con la evidencia: el arreglo puede estar apuntando a otro problema.

## 1. Compuertas

Las del perfil («Compuertas»), en su orden, con `wt` si estás en un worktree. Las lentas (integración, e2e) pueden esperar al paso 3. Las fallas conocidas del perfil se nombran, no se esconden; ante la duda, córrelas en la base (§Regresión 3).

## 1b. Diseño simple

- `<plugin>/scripts/duplicados.sh <base>`: cada duplicado de código nuevo se reutiliza o se justifica.
- El «Mapa de reutilización» de `<plugin>/referencias/diseno-simple.md` en la carpeta de informes, hecho desde el diff: qué existente se reutiliza y por qué cada pieza nueva no podía usar lo que había. Si encuentras algo existente que servía, cámbialo ahora.
- `/simplify` sobre el diff: aplica lo que simplifique sin cambiar el comportamiento y repite el paso 1.

## 2. /panel

Antes de correrlo, si el cambio altera algo visible o una regla, los docs del área ya tienen que estar actualizados: el panel los revisa en la primera vuelta y no gasta una vuelta en pedirlos.

Corre `/pandilla:panel`. Corrige los C y W confirmados o plausibles; los S a tu criterio (anota cuáles dejaste). Repite el paso 1 y corre `--re-revision <informe>`. Máximo 3 vueltas; si en la tercera siguen los C o W, para y pregunta.

## 3. Prueba local completa, rojo/verde (obligatoria y estricta)

Una prueba solo cuenta si es **completa**. Estas reglas no tienen excepción ni se cambian por «es un cambio chico»:

- **Todo el flujo arriba.** Levanta todos los servicios por los que pasa el flujo, no solo los que tocaste: si el dato viaja de A a B a C, los tres corren. Si uno no levanta, se arregla o la tarea queda BLOQUEADA.
- **Entrada real y pasos reales.** El flujo parte por donde parte para quien lo usa (la pantalla, la API pública, el webhook o el evento que lo dispara de verdad) y recorre cada paso intermedio por su camino normal: login real, pago por la pasarela local o sandbox, jobs y colas que corren solos. **Prohibido** llamar a mano funciones internas, publicar a mano eventos o mensajes, forzar estados en la base o saltarse un servicio para llegar más rápido. Sembrar datos solo vale *antes* de empezar el flujo.
- **Navegador si lo ve una persona.** Si el cambio lo ve o lo usa un usuario final, un cliente o un operador (pantalla, correo, notificación, un dato que se muestra o se cobra), la prueba se hace en el navegador (o en el simulador, si es app), con capturas antes y después. GraphQL, curl o la consola complementan, nunca reemplazan.
- **Rojo y verde por la misma vía.** El rojo en la base y el verde en la rama se corren con el mismo flujo completo. Todo bug trae además un test que falla antes del arreglo, si el área ya tiene infra de test.
- **Tabla de cobertura** en la evidencia: una fila por paso del flujo (pantalla, servicio, job, evento) con cómo se ejecutó (`real` o `sembrado antes del flujo`), resultado en la base, resultado en la rama y archivo de evidencia. Si un paso del flujo no aparece o no es `real`, la prueba no está completa.
- **Si no se puede completar: BLOQUEADO**, con el motivo y lo que falta (un servicio que no levanta, credenciales de sandbox, datos). Nunca «pendiente», «no probado» o «fuera de alcance» como nota al pie de algo que se declara listo.
- Compuertas lentas y la prueba de «Prueba local» del perfil. Recursos compartidos en fila (`fila.sh`), como comando en segundo plano.
- Evidencia en la carpeta de informes del perfil (por defecto `tmp/entrega/<rama>/`): la tabla de cobertura, capturas y logs.

## 4. Regresión de flujos críticos (obligatoria)

Demostrar con evidencia que el cambio no rompe un flujo crítico. Complementa la prueba rojo/verde. Si el diff es grande o el contexto está cargado, delégala en un `Agent` general-purpose de una sola vez, con esta sección, la rama, los archivos y las preguntas concretas de riesgo («¿alguien atrapaba este error?», «¿alguien espera un array?»), y la prohibición de editar o commitear.

1. **Mapa de impacto.** Busca con grep TODOS los consumidores de lo que cambió: quienes llaman a la función, quienes leen lo que el cambio escribe, las pantallas, APIs, jobs y servicios que muestran o reciben el dato, y los clientes viejos (apps instaladas, integraciones) si cambia una respuesta. Por cada uno: archivo:línea, qué recibía antes y qué recibe ahora, y si depende del comportamiento viejo.
2. **Flujos críticos.** De los «Flujos críticos» del perfil, elige los que toca el mapa. Lista también los descartados y por qué.
3. **Tests: base frente a la rama.** Corre las compuertas y los tests de los consumidores en la rama y, para lo que falle, en la base, en un worktree temporal (`git worktree add --detach ../<repo>-base-<slug> <base>`, prepáralo, y bórralo al terminar). Nunca `git stash`. Un test que falla en la rama y no en la base es una regresión.
4. **De punta a punta en local**, para cada flujo crítico elegido, con las reglas del paso 3 (todo el flujo arriba, entrada y pasos reales, navegador si lo ve una persona) y la «Prueba local» del perfil. Un flujo que no se puede probar completo deja la entrega BLOQUEADA, salvo que el usuario acepte explícitamente esa excepción; nunca lo marques OK.
5. **Producción**, solo si el perfil lo permite y con sus reglas (solo lectura, solo agregados): cuántos casos reales caen en lo que cambia. Dentro de /lote lo mide el orquestador, nunca la tarea. Si sale una hipótesis sobre un bug que ya existía, confírmala antes de darla por cierta.

Informe (`<carpeta de informes>/regresion/<rama>.md`): tabla de consumidores, tabla de flujos (cómo se probó, resultado, evidencia), tests base frente a rama, lo que no se pudo probar y los riesgos. Última línea: «REGRESIÓN <rama>: OK, <k> flujos verificados» o «REGRESIÓN <rama>: RIESGO, <resumen>». Si sale RIESGO, arregla, vuelve al paso 1 y re-revisa con el panel.

## 5. Commit y publicación

Solo con el panel APROBADO, los pasos 3 y 4 en verde y la tabla de cobertura completa (todos los pasos `real`):

- `git diff --numstat <base>` (pisadas) y que no entre ningún secreto ni dato real.
- Un solo commit con el formato del perfil, con el código y los docs revisados por el panel.
- **Publicación: pr** → push y PR con la herramienta del perfil (skill del repo o `gh pr create`), en un solo push. Cuerpo: decisiones de la alineación, veredicto del panel y S que quedaron, evidencia rojo/verde con la tabla de cobertura, y tabla de regresión. En un `bug`, también el comando rojo, la causa confirmada y las hipótesis descartadas.
- **Publicación: local** → sin push. El mismo contenido va en `<carpeta de informes>/entrega/<rama>/informe.md`.

## 6. Revisión independiente en una sesión limpia

Nunca la corras tú: necesita contexto limpio. Lánzala con `delegate_task` `role: "review"` (T3) o con un `Agent` general-purpose nuevo:

- con PR: la revisión de PR del perfil sobre `#<n>`, sin aprobar ni pedir cambios, sin checkout, stash ni reset, leyendo con `git fetch origin pull/<n>/head:refs/remotes/pr/<n>`;
- local: `/code-review high` sobre `git diff <base>...<rama>`, solo lectura.

Si quedan C, W o SEC confirmados: corrígelos, repite los pasos 1 y 3 y la parte de la regresión que toque el arreglo, súbelos como **commits nuevos al mismo PR** (o a la misma rama) y lanza otra revisión. Lo preexistente no se arregla aquí: propón una tarea aparte.

## 7. Cierre

- Con PR, mira la CI (`gh pr checks <n>`); si algo falla, revisa el log, arregla y súbelo al mismo PR.
- **Listo para merge:** panel APROBADO, compuertas verdes, prueba local completa (tabla de cobertura sin pasos saltados ni simulados, navegador si lo ve una persona), regresión OK, revisión independiente sin C ni SEC y, con PR, CI verde y `mergeable`. Si falta cualquiera, no digas «listo»: di qué falta.
- **No mergees.** Lo decide el usuario. Si el perfil dice qué pasa al mergear (despliegue automático, pasos manuales), dilo.
- Resumen final en una tabla: PR o rama · panel · rojo/verde · regresión · revisión · CI · pendiente; más una línea con qué cambia para quien usa el producto.
- En un worktree, libera el entorno con el comando del perfil.
