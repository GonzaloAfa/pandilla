---
name: iniciar
description: >-
  Conecta un repositorio a pandilla: lee el proyecto (stack, scripts de test, CI, puertos, bases de datos, despliegue), pregunta lo que solo el dueño puede decidir y escribe el perfil .claude/pandilla.md, copia los scripts de entorno a scripts/pandilla/ y deja los informes fuera de git. Usar con "/pandilla:iniciar", "configura pandilla en este repo", o cuando /lote, /panel o /entrega no encuentran el perfil.
---

# /iniciar

Deja el repo listo para `/pandilla:lote`, `/pandilla:panel` y `/pandilla:entrega`. El resultado es un perfil versionado en el repo, que el dueño controla y edita.

## 1. Leer el proyecto

Sin preguntar todavía, averigua:

- **Base y ramas:** `git remote show origin` (rama por defecto), ramas de release, convención de nombres de rama y de commits (`git log --oneline -30`).
- **Stack y gestor de paquetes:** `package.json` + lockfile, `pyproject.toml`, `go.mod`, `Cargo.toml`, `Gemfile`, monorepo o no. Versión de runtime (`.nvmrc`, `.tool-versions`, `.python-version`).
- **Compuertas:** lo que corre la CI (`.github/workflows/`, `.gitlab-ci.yml`, etc.) y los scripts del proyecto (formato, lint, tipos, unit, integración, e2e). Anota cuánto tarda cada uno si se nota.
- **Qué choca entre worktrees:** puertos fijos (scripts `dev`, configs de e2e, `.env.example`), bases de datos locales compartidas (docker-compose, URLs en los `.env`), carpetas de salida fijas, simuladores o emuladores, servicios que solo admiten una instancia. Mira si los tests de integración levantan su propia base (Testcontainers, bases en memoria) o usan una compartida.
- **Archivos sin versionar que hacen falta para correr** (por ejemplo `.env` locales). No leas su contenido: solo anota los nombres.
- **Producción:** dónde están los datos (base, proveedor), qué herramientas o MCP tiene el usuario conectados que la alcanzan, y si hay datos sensibles (salud, pagos, menores).
- **Despliegue:** qué pasa al mergear (despliegue automático, apps que necesitan publicación manual).
- **Reglas existentes:** `CLAUDE.md`, `AGENTS.md`, `CONTRIBUTING.md`, docs de arquitectura. El perfil las referencia; no las copia.
- **Revisión de PR:** si el repo ya tiene una skill de revisión o de PR (`.claude/skills/`), úsala en el perfil.

## 2. Preguntar lo que no se deduce

Con `AskUserQuestion`, en una sola tanda y con una recomendación marcada:

- **Publicación:** cada tarea termina en un PR, o en un commit local sin push (por ejemplo, para no gastar minutos de CI).
- **Producción:** ningún acceso; o mediciones solo de lectura y solo agregados que corre el orquestador (nunca las tareas), y con qué herramienta.
- **Prohibido para las tareas**, además de lo de siempre (prod, publicar, secretos): por ejemplo ciertas carpetas o archivos de infraestructura.
- **Pedidos:** texto, o tickets de qué gestor.

## 3. Escribir

- `.claude/pandilla.md` con la plantilla [`plantilla-perfil.md`](plantilla-perfil.md), completa con lo que leíste. Nada inventado: si algo no se sabe, márcalo «por definir».
- `scripts/pandilla/`: copia `entorno.sh`, `wt` y `fila.sh` desde la carpeta `scripts/` del plugin (dos niveles arriba de esta skill). Así las tareas tienen una ruta estable y el dueño puede adaptarlos.
- La sección «Entorno» del perfil con el comando completo de `scripts/pandilla/entorno.sh` para este repo: instalación, un `--puerto` por cada puerto que choca, las `--var` que los usan (URLs, `PORT`), `--copiar` para los archivos sin versionar que hacen falta, y `--negar` para cada herramienta que alcanza producción (por ejemplo `mcp__<servidor>`). Si el repo necesita algo que el script no cubre (copiar una base por worktree, levantar contenedores), escribe un script propio en `scripts/pandilla/` y documéntalo.
- `.gitignore`: la carpeta de informes (`/tmp/` o la que elijas), `/.wt-env` y `/.claude/settings.local.json`.
- Si el usuario usa T3 Code: propone un script del proyecto con `runOnWorktreeCreate` que corra la preparación, y otro con `runOnSettle` que libere el entorno.

## 4. Probar

En un worktree temporal (`git worktree add --detach ../<repo>-pandilla-prueba <base>`):

- corre la preparación y verifica `.wt-env`;
- corre con `wt` una compuerta rápida y, si se puede, el servidor de desarrollo en su puerto;
- prepara un segundo worktree y comprueba que no repite puertos;
- libera ambos con `--borrar` y bórralos.

Muestra el perfil al usuario y lo que no se pudo probar. El commit lo decide el usuario (o va en el mismo PR si pidió uno).
