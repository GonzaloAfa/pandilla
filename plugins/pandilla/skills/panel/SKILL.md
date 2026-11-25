---
name: panel
description: >-
  Panel local de revisión multi-agente. Elige revisores según las rutas que toca el diff (tabla del perfil del proyecto), los corre en paralelo, verifica adversarialmente sus hallazgos con un verificador y entrega APROBADO o CAMBIOS REQUERIDOS. Usar con "/panel", "revisa con el panel", "re-revisa", o antes de commitear una tarea de /lote o /entrega. Solo local: no comenta en GitHub, no commitea y no consulta producción.
---

# /panel

Todo corre en este computador. El panel no comenta en GitHub, no commitea, no hace push y no consulta producción.

Lee primero el perfil del proyecto. **Dónde está el perfil.** En orden: `<raíz>/.claude/pandilla.md` (versionado en el repo), o `~/.claude/pandilla/perfiles/<repo>.md` (local, para repos donde no se puede commitear; `<repo>` es el nombre de la carpeta del checkout principal: `basename "$(dirname "$(cd "$(git rev-parse --git-common-dir)" && pwd)")"`, así funciona igual desde un worktree). Los revisores propios están junto al perfil: `<raíz>/.claude/pandilla/revisores/` o `~/.claude/pandilla/perfiles/<repo>/revisores/`. En adelante, «el perfil» es el que encontraste. Si no hay ninguno, avisa que falta y propone `/pandilla:iniciar`; mientras tanto usa la base `main` (o `origin/HEAD`) y el ruteo por defecto de §3.

## Argumentos

`/panel [--base <ref>] [--pr <n>] [--ref <sha>] [--pedido "<texto>"] [--capturas <dir>] [--re-revision <informe.md>] [--panel a,b,c]`

- Sin argumentos: la rama actual contra la base del perfil, incluidos los cambios sin commitear.
- `--pr <n>`: un PR de GitHub (abierto o mergeado). `--ref <sha>`: un commit. Sirven también para calibrar con cambios viejos que después tuvieron un bug conocido.
- `--pedido`: el pedido o el ticket. Sin él, el contexto sale del brief de la tarea, del PR o de los commits.
- `--capturas`: capturas de la prueba local, para `superficies`.
- `--re-revision`: informe anterior. La re-revisión es incremental (§3b) y el verificador marca cada hallazgo previo como RESUELTO, NO RESUELTO o YA NO APLICA.
- `--panel`: fuerza la lista de revisores.

## 1. Diff

- **Rama actual:** si la base es remota (`origin/<x>`), primero `git fetch origin <x> --quiet`. `BASE=$(git merge-base <base> HEAD)`. Con cambios sin commitear, el diff es `git diff $BASE`; sin ellos, `git diff $BASE...HEAD`.
- **`--pr <n>`:** `gh pr view <n> --json state,baseRefName,headRefOid,mergeCommit,files`. Mergeado: `HEAD=<mergeCommit>`, `BASE=<mergeCommit>^`. Abierto: `git fetch origin pull/<n>/head` y `BASE=$(git merge-base <base> <headRefOid>)`.
- **`--ref <sha>`:** `HEAD=<sha>`, `BASE=<sha>^`.
- Si HEAD no es el árbol de trabajo, los revisores leen con `git show <HEAD>:<ruta>`.
- Si el diff está vacío, termina diciéndolo.
- **Pisadas:** `git diff --numstat $BASE`. Un archivo ajeno al pedido con muchas líneas borradas (lockfile, `package.json`, `CLAUDE.md`, migraciones existentes) va arriba del informe como C, sin pasar por el verificador. Es el error típico de commitear desde un checkout sucio.
- **Secretos y datos reales:** archivos `.env*`, llaves, o fixtures con datos de personas reales van arriba como C.
- **Logs de depuración:** una línea agregada con `[DEBUG-` (`git diff $BASE | grep -n '^+.*\[DEBUG-'`) va arriba como C, sin pasar por el verificador.

## 2. Contexto compartido (una sola vez)

- El pedido, con su bloque de «Decisiones» si viene de una alineación (brief de la tarea o informe de /entrega). Las decisiones tomadas no son hallazgos: un revisor las reporta solo si el código las contradice.
- Las reglas del proyecto: `CLAUDE.md`, la sección «Reglas del proyecto» del perfil, y las páginas de docs, specs o ADR del área que el perfil indique para cada tipo.
- No pegues el diff en los prompts: cada revisor lo lee con git.

## 3. Ruteo

Usa la tabla «Rutas y revisores» del perfil: tipo → rutas → revisores. Los revisores del plugin son `correctitud`, `sistemas`, `seguridad`, `datos`, `superficies`, `infra`, `costos` y `diseno`; el perfil puede agregar revisores propios (§4).

Sin perfil, este ruteo por defecto:

| Tipo | Rutas típicas | Revisores |
|---|---|---|
| ui | `*.tsx`, `*.vue`, `*.svelte`, `app/`, `pages/`, `components/`, `messages/`, `locales/` | `superficies`, `correctitud`, `diseno` |
| backend | `api/`, `server/`, `src/` (sin UI), `lib/`, `packages/` | `correctitud`, `sistemas`, `seguridad`, `datos`, `diseno` |
| datos | `migrations/`, `schema.*`, `prisma/`, `drizzle/`, `db/` | `datos`, `seguridad`, `correctitud` |
| infra | `.github/`, `infra/`, `terraform/`, `Dockerfile*`, `*.yml` de despliegue, `scripts/*.sh` | `infra`, `seguridad` |
| docs | `docs/`, `*.md` | `superficies` |
| generado | lockfiles, código generado, `dist/`, `coverage/` | no cuentan |

Reglas que valen siempre (además de las del perfil):

- **Unión sin duplicados:** cada revisor entra una vez y recibe todos sus archivos.
- `seguridad` se suma en cualquier tipo si el diff contiene `auth`, `session`, `token`, `password`, `permission`, `role`, `redirect`, `cookie`, `cors`, `webhook`, `secret`, `dangerouslySetInnerHTML`, `eval` o consultas armadas con strings.
- `superficies` se suma si cambia algo que ve una persona: textos, correos, notificaciones, mensajes de error.
- `costos` entra solo con señales de gasto, en cualquier tipo: llamadas a APIs pagadas o de IA (`openai`, `anthropic`, `bedrock`, `gemini`, SDKs de terceros que cobran por uso), envíos (correo, SMS, push, WhatsApp), jobs programados o colas (`cron`, `schedule`, `queue`, `job`), recorridos o consultas sobre colecciones completas, almacenamiento o logs nuevos por evento, o infraestructura que cambia tamaño o cantidad de recursos. Sin señales, no entra. En el uso real, `costos` en todo el backend dio 4 W en 22 corridas.
- `infra` entra solo si el diff toca rutas de infra (tabla) o variables de entorno y configuración de despliegue.
- **Diff chico** (≤ 30 líneas, ≤ 2 archivos, sin migración ni infra): `correctitud` y el especialista más pertinente.
- `diseno` entra si el diff agrega código (no solo borra o cambia textos) en ui o backend. Recibe la ruta de `<plugin>/referencias/diseno-simple.md`, el «Mapa de reutilización» de la tarea si existe y la salida de `<plugin>/scripts/duplicados.sh <base>`.

Muestra el panel en una línea, con la razón de cada revisor, y sigue sin esperar confirmación.

## 3b. Re-revisión incremental

Con `--re-revision`, no repitas el panel completo:

1. Lee las «Huellas» del informe anterior (§6) y calcula las del diff actual. **Archivos cambiados** = los del diff actual cuya huella es distinta o que no estaban antes.
2. **Revisores de esta vuelta** = el ruteo de §3 aplicado solo a los archivos cambiados, más los revisores que dejaron un C o W vigente en el informe anterior. Cada uno recibe como «Tus archivos» solo los archivos cambiados que le tocan; la lista completa del diff va como contexto.
3. Si no hay archivos cambiados, no lances revisores: el verificador decide con el informe anterior y el código actual.
4. El verificador corre siempre, con el informe anterior.
5. Excepción: si los archivos cambiados son más de la mitad del diff, o la vuelta anterior pidió un rediseño, corre el panel completo.

Muestra en una línea qué revisores repiten y por qué.

## 4. Revisores en paralelo

Lanza todos en **un solo mensaje**, con varias llamadas a `Agent` y `run_in_background: false`:

- `subagent_type: "pandilla:revisor-<nombre>"` (los del plugin; usan Sonnet);
- un revisor propio del proyecto (`<carpeta de revisores>/<nombre>.md`): `subagent_type: "general-purpose"`, `model: "sonnet"`, y el brief empieza con «Primero lee `<carpeta de revisores>/<nombre>.md`: define tu rol, tus reglas y tu formato de salida».
- Si un revisor del plugin tiene un archivo con el mismo nombre en la carpeta de revisores del proyecto, pásale también esa ruta: lo complementa.
- Complementos de diseño: si el diff toca UI, pásale a `superficies` también la ruta de `emil-ui-review` (o, si no está, la de `accessibility-auditor`) según `<plugin>/referencias/complementos.md`. Obtén la ruta con `<plugin>/scripts/complementos.sh --ruta <nombre>` (`<plugin>` es la carpeta dos niveles arriba de esta skill).

Brief de cada uno:

```
Checkout: <ruta absoluta>
Perfil: <ruta del perfil> (o "no hay")
Diff: BASE=<sha> HEAD=<sha | árbol de trabajo> (si HEAD es un sha: lee con git show HEAD:ruta)
Tus archivos: <lista>
Todos los archivos del diff: <lista> (puedes abrirlos si los necesitas)
Pedido: <resumen, máx. 15 líneas>
Decisiones: <bloque de la alineación o "no hay">. No las reportes como hallazgo salvo que el código las contradiga.
Reglas y docs del área: <rutas>
Complemento del proyecto: <ruta en la carpeta de revisores o "no hay">
Capturas: <rutas o "no hay">
Re-revisión: <ruta del informe anterior o "no">
Otros revisores de este panel: <nombre: foco en pocas palabras, por cada uno>. Lo que sea del foco de otro no lo reportes: lo ve ese revisor.
Sugerencias (S): máximo 3, las de más valor.
Sigue tu formato de salida exacto.
```

## 5. Verificación

Con todas las salidas, lanza un solo `Agent` con `subagent_type: "pandilla:verificador"` (usa Opus). Pásale el mismo encabezado, las salidas completas de los revisores y el informe anterior si es re-revisión. No filtres ni reescribas hallazgos antes del verificador: su trabajo es descartar los falsos. El verificador comprueba contra el código solo los C y W; los S pasan sin verificar (solo se unen duplicados), porque no bloquean y verificarlos era la mayor parte de su gasto.

## 6. Informe

Guarda el resultado en `<checkout>/tmp/panel/<rama-o-pr>-<AAAAMMDD-HHMM>.md` (o la carpeta de informes que diga el perfil; tiene que estar ignorada por git). Al inicio: base, head, panel usado y, si es re-revisión, archivos cambiados. Al final: revisores, hallazgos brutos frente a confirmados, y descartados.

Cierra el informe con las **Huellas**, para que la siguiente re-revisión sepa qué cambió: por cada archivo del diff, `<ruta> <hash>`, con `git hash-object <ruta>` si HEAD es el árbol de trabajo o `git rev-parse <HEAD>:<ruta>` si es un sha (un archivo borrado se anota `<ruta> borrado`).

Al usuario: el veredicto, la tabla de hallazgos vigentes y la ruta del informe. No repitas los descartados.

## 7. Regla de commit

- **CAMBIOS REQUERIDOS:** corrige los C y W confirmados o plausibles (los S a criterio, avisando cuáles quedaron). Repite las compuertas que correspondan y corre `/panel --re-revision <informe>`. Máximo 3 vueltas; si en la tercera sigue habiendo C o W, para y pregunta.
- **APROBADO:** recién entonces se commitea, si el usuario autorizó el commit de esta tarea (directamente, o vía /lote o /entrega). Lo que sigue (PR o commit local) lo dice el perfil en «Publicación».
- Si el panel se usó para calibrar (`--pr` o `--ref` de algo ya mergeado), no hay commit: solo informe. Para medir si el panel sirve, junta los resultados en `tmp/panel/calibracion.md`: por cada bug conocido, ¿el panel lo habría visto? (sí, parcial o no).
