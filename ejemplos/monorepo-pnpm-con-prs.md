# Perfil de cuadrilla: ejemplo de monorepo pnpm con PRs

Ejemplo ficticio: monorepo pnpm con API en Node, app móvil Expo, landing estática y Postgres local en Docker. Cada tarea abre un PR; producción se mide solo en lectura.

## Proyecto

- **Base:** `origin/main`
- **Ramas:** `<tipo>/<slug>` (`fix/…`, `feat/…`)
- **Commits:** convencionales (`fix(api): …`)
- **Publicación:** `pr`
- **PR con:** skill `create-pr` del repo
- **Revisión independiente:** skill `/review-pr` del repo
- **Pedidos:** texto
- **Máximo de tareas activas:** 4
- **Carpeta de informes:** `tmp/`

## Entorno

- **Preparar:** `bash scripts/cuadrilla/entorno-db.sh`, un script propio sobre `entorno.sh`. Además de los puertos, copia la base de desarrollo `app` a `app_wt_<rama>` y crea una base de test propia:
  ```
  bash scripts/cuadrilla/entorno.sh \
    --instalar "pnpm install --frozen-lockfile" \
    --copiar .env --copiar apps/api/.env \
    --puerto API=18000 --puerto WEB=17000 --puerto METRO=19000 \
    --var 'PORT=$API' --var 'EXPO_PUBLIC_API_URL=http://localhost:$API' \
    --var "DATABASE_URL=postgres://app:app@127.0.0.1:5432/app_wt_<rama>" \
    --negar mcp__Neon
  ```
- **Correr:** `scripts/cuadrilla/wt <comando>`
- **Liberar:** `bash scripts/cuadrilla/entorno-db.sh --borrar`, que borra solo las bases `app_wt_*` de este worktree.
- **Del checkout principal:** puertos 8080, 8081 y 3000; bases `app` y `app_test`.
- **En fila:** el simulador iOS → `bash scripts/cuadrilla/fila.sh app-simulador -- scripts/cuadrilla/wt pnpm test:e2e`

## Compuertas

1. `wt pnpm typecheck`
2. `wt pnpm lint`
3. `wt pnpm test:api`, sobre la base de test del worktree
4. `wt pnpm test:mobile`
5. e2e de la app, en fila

**Fallas conocidas:** ninguna.

## Prueba local

- API: `wt pnpm dev:api`, en el puerto `API` del worktree.
- Landing: `wt pnpm --filter landing dev -- --port <WEB>`; mírala también sin JS.
- Jobs del pipeline: primero en seco (`--dry-run`) y acotados (`--limit 20`), sobre la base del worktree.

## Rutas y revisores

| Tipo | Rutas | Revisores | Docs del área |
|---|---|---|---|
| app, web | `apps/mobile/`, `apps/landing/`, `apps/web/` | `superficies`, `correctitud` | `docs/invariantes/superficies.md` |
| api | `apps/api/`, `packages/` (salvo `packages/db/`) | `correctitud`, `seguridad`, `datos`, `costos` | `docs/technical/api.md` |
| datos | `packages/db/` | `datos`, `correctitud`, `seguridad` | `docs/invariantes/datos.md` |
| pipeline | `scraper/`, `scripts/*.ts` | `pipeline` (propio), `datos`, `costos` | `docs/invariantes/pipeline.md` |
| infra | `.github/`, `infra/`, `scripts/*.sh`, `docker-compose.yml` | `infra`, `seguridad`, `costos` | |
| docs | `docs/`, `*.md` | `superficies` | |
| generado | `pnpm-lock.yaml`, `packages/db/drizzle/meta/`, `dist/` | (no cuentan) | |

**Revisores propios:** `.claude/cuadrilla/revisores/pipeline.md`.

## Flujos críticos

- Fechas del catálogo: una fecha falsa es el peor error. Se prueba con el test del parser y el pipeline en seco.
- Login y consentimiento en la app: se prueba con el e2e de la app.
- Push y correo, con sus topes y deduplicación: se prueba con los tests de la API y el envío a un fake.
- Migraciones y roles de Postgres: se prueban con la migración sobre la base del worktree.

## Producción

- **Acceso:** solo lectura y solo agregados. Lo mide el orquestador, nunca las tareas.
- **Herramienta y envoltorio:** `run_sql_transaction` con `["SET TRANSACTION READ ONLY", "SET LOCAL statement_timeout = '15s'", "<SELECT count(*) …>"]`.
- **Nunca:** filas de `user`, `session` ni `account`; escrituras; `EXPLAIN ANALYZE` sobre tablas grandes.

## Al mergear

La API y la landing se despliegan solas. La app necesita un OTA o un build de tienda, que publica el dueño.

## Prohibido para las tareas

`.env*`, `infra/template.yaml`, publicar OTA o builds, y mandar push o correos reales.
