# Perfil de pandilla: ejemplo de app Next.js con datos sensibles, todo local

Ejemplo ficticio: app Next.js multi-tenant con datos de salud, arquitectura hexagonal (ports y adapters), adapters en memoria para el desarrollo y Postgres por Testcontainers en los tests de integración. No se usa la CI por ahora, así que cada tarea termina en un commit local. Producción no se toca nunca.

## Proyecto

- **Base:** `main` (local)
- **Ramas:** `<tipo>/<slug>`
- **Commits:** convencionales en inglés
- **Publicación:** `local`
- **Revisión independiente:** `/code-review high`
- **Pedidos:** texto o una sección de `specs/`
- **Máximo de tareas activas:** 4
- **Carpeta de informes:** `tmp/`

## Entorno

- **Preparar:**
  ```
  bash scripts/pandilla/entorno.sh \
    --instalar "pnpm install --frozen-lockfile" \
    --puerto DEV=23000 --puerto E2E_PORT=24000 --puerto E2E_DEMO_PORT=25000 \
    --var 'PORT=$DEV' --var 'APP_URL=http://localhost:$DEV' \
    --var 'PATH=$HOME/.nvm/versions/node/v24.22.1/bin:$PATH' \
    --negar mcp__Neon --negar mcp__plugin_vercel_vercel
  ```
- **Correr:** `scripts/pandilla/wt <comando>`
- **Liberar:** `bash scripts/pandilla/entorno.sh --borrar`
- **Del checkout principal:** puertos 3000, 3100, 3101 y 3200.
- **En fila:** e2e (build + 2 servidores + Chromium) → `bash scripts/pandilla/fila.sh app-e2e -- scripts/pandilla/wt pnpm test:e2e`

No hay bases que copiar: el desarrollo corre con adapters en memoria, y cada corrida de integración levanta su propio Postgres. Necesita Docker.

## Compuertas

1. `wt pnpm format:check`
2. `wt pnpm lint`
3. `wt pnpm typecheck`
4. `wt pnpm depcruise`: límites entre capas y módulos
5. `wt pnpm test:unit --coverage`
6. `wt pnpm test:ui`
7. `wt pnpm test:integration` (lenta)
8. e2e en fila (lenta)

**Fallas conocidas:** un e2e que depende de la hora del día, y un test de accesibilidad inestable.

## Prueba local

- `wt pnpm dev -p <DEV>` sobre `http://<tenant>.localhost:<DEV>`, con el personal sintético sembrado.
- Para probar con volumen: `SEED_DEMO_DATA=true`, un conjunto sintético y determinista.
- Evidencia: solo datos sintéticos.

## Rutas y revisores

| Tipo | Rutas | Revisores | Docs del área |
|---|---|---|---|
| dominio | `src/modules/*/domain/`, `src/modules/*/application/` | `correctitud`, `arquitectura` (propio) | `specs/`, `docs/architecture/adr/` |
| datos | `src/platform/db/`, `src/modules/*/infrastructure/` | `datos`, `seguridad`, `correctitud` | ADR de multi-tenancy y RLS |
| adapters | `src/ports/`, `src/adapters/` | `arquitectura`, `correctitud`, `seguridad` | `docs/architecture/ports-and-adapters.md` |
| clínico | `src/modules/clinical-record/`, `src/modules/patients/` | `clinico` (propio), `correctitud`, `seguridad`, `datos` | `docs/regulatorio.md` |
| ui | `src/app/` (salvo `api/`), `src/design-system/`, `messages/` | `superficies`, `correctitud` | ADR del sistema de diseño |
| api | `src/app/api/` | `seguridad`, `correctitud`, `infra` | |
| infra | `.github/`, `vercel.json`, `next.config.ts`, `package.json` | `infra`, `seguridad` | |

**Reglas adicionales:** `seguridad` entra siempre que el diff toque acceso clínico, transacciones por tenant, sesiones, PIN o TOTP, webhooks o logs. `clinico` entra si cambia la ficha, el consentimiento, la bitácora o la retención.

**Revisores propios:** `.claude/pandilla/revisores/arquitectura.md` y `.claude/pandilla/revisores/clinico.md`.

## Flujos críticos

- Reservar: autoagenda y recepción, sin doble reserva (`pnpm test:stress`).
- Llegar y atender: estados de la cita.
- Firmar: lo firmado no se edita, solo se agregan adendas.
- Permisos y bitácora: acceso solo por relación de atención, break-glass, un centro nunca ve datos de otro.
- Ingreso del personal: contraseña, TOTP y PIN.

## Producción

- **Acceso:** ninguno. Son datos de salud. Si el riesgo depende de cuántos casos reales hay, se anota como pregunta para el dueño.

## Al mergear

Nada se despliega solo mientras la CI está apagada.

## Prohibido para las tareas

Push, PR, GitHub Actions, prod y staging, y datos reales de pacientes en el repo, los fixtures, los logs, las capturas o los prompts.

## Reglas del proyecto

- Código en inglés; la UI en español vía i18n.
- Proveedores solo detrás de su adapter, con un fake y un test de contrato.
- Dinero en unidades menores enteras; zonas horarias IANA de la sucursal.
