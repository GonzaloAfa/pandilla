# Perfil de pandilla: <proyecto>

Lo leen `/pandilla:lote`, `/pandilla:panel` y `/pandilla:entrega`. Es del dueño del repo: edítalo cuando cambie algo.

## Proyecto

- **Base:** `main` (o `origin/main` si se trabaja contra el remoto)
- **Ramas:** `<tipo>/<slug>` (o `<usuario>/<ticket>`)
- **Commits:** convencionales en inglés (`fix(scope): …`) | otro formato
- **Publicación:** `pr` | `local`
- **PR con:** skill `create-pr` del repo | `gh pr create --base <base>`
- **Revisión independiente:** skill `/review-pr` del repo | `/code-review high`
- **Pedidos:** texto | tickets de <Linear | GitHub Issues | Jira>
- **Máximo de tareas activas:** 4
- **Carpeta de informes:** `tmp/` (ignorada por git)

## Entorno

- **Preparar:** `bash scripts/pandilla/entorno.sh --instalar "<comando>" --puerto DEV=23000 --var 'PORT=$DEV' --negar mcp__<servidor-de-prod>`
- **Correr:** `scripts/pandilla/wt <comando>` (en este perfil, `wt`)
- **Liberar:** `bash scripts/pandilla/entorno.sh --borrar`
- **Del checkout principal (no usar desde un worktree):** puertos <3000, …>, bases <…>
- **En fila:** <recurso> → `bash scripts/pandilla/fila.sh <proyecto>-<recurso> -- scripts/pandilla/wt <comando>`

## Compuertas

En orden; las lentas van en la prueba local.

1. `wt <formato>`
2. `wt <lint>`
3. `wt <tipos>`
4. `wt <tests unitarios>`
5. `wt <integración>` (lenta)
6. e2e en fila (lenta)

**Fallas conocidas** (ya fallan en la base; se nombran, no se esconden): <ninguna | lista>

## Prueba local

Regla fija de pandilla: la prueba es completa o no cuenta (todos los servicios del flujo arriba, entrada y pasos reales sin atajos, navegador con capturas si lo ve una persona, tabla de cobertura; si no se puede, BLOQUEADO). Ver el paso 3 de /pandilla:entrega.

- Cómo levantar lo necesario con los puertos del worktree: <comando>
- Flujos típicos y sus servicios (para armar la «Prueba completa» de cada brief): <flujo → servicios, p. ej. «compra web → web, api, pagos (sandbox), worker de eventos»>
- Cómo pagar, loguearse o disparar webhooks en local sin atajos: <tarjetas de sandbox, cuentas de prueba, CLI de webhooks>
- Datos de prueba y usuarios: <semillas, cuentas de prueba>
- Evidencia: capturas, salida de tests, logs.

## Rutas y revisores

| Tipo | Rutas | Revisores | Docs del área |
|---|---|---|---|
| ui | `<…>` | `superficies`, `correctitud` | `<…>` |
| backend | `<…>` | `correctitud`, `sistemas`, `seguridad`, `datos`, `costos` | `<…>` |
| datos | `<…>` | `datos`, `seguridad`, `correctitud` | `<…>` |
| infra | `<…>` | `infra`, `seguridad`, `costos` | `<…>` |
| docs | `docs/`, `*.md` | `superficies` | |
| generado | lockfiles, código generado | (no cuentan) | |

Reglas adicionales de ruteo: <ninguna | lista>

**Revisores propios** (opcional): un archivo en `.claude/pandilla/revisores/<nombre>.md` con el mismo formato que los del plugin. Con un nombre nuevo (`clinico`, `pagos`…) es un revisor más que se puede poner en la tabla. Con el nombre de uno del plugin (`seguridad`…) lo complementa con las reglas del proyecto.

## Flujos críticos

Los que nunca se pueden romper, y cómo se prueba cada uno en local:

- <flujo>: <cómo se prueba>

## Producción

- **Acceso:** ninguno | solo lectura y solo agregados, lo mide el orquestador, nunca las tareas
- **Herramienta y envoltorio:** <por ejemplo, una transacción `READ ONLY` con `statement_timeout`>
- **Nunca:** filas de tablas de personas, escrituras, pruebas de rendimiento.

## Al mergear

<qué se despliega solo, qué queda manual (builds de tienda, OTA, migraciones aplicadas a mano)>

## Prohibido para las tareas

Además de producción, publicar y secretos: <carpetas o archivos>

## Reglas del proyecto

Las que no están en `CLAUDE.md` y los agentes tienen que seguir: <lista>
