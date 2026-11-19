---
name: panel
description: >-
  Panel local de revisión multi-agente. Elige revisores según las rutas que toca el diff (tabla del perfil del proyecto), los corre en paralelo, verifica adversarialmente sus hallazgos con un verificador y entrega APROBADO o CAMBIOS REQUERIDOS. Usar con "/panel", "revisa con el panel", "re-revisa", o antes de commitear una tarea de /lote o /entrega. Solo local: no comenta en GitHub, no commitea y no consulta producción.
---

# /panel

Todo corre en este computador. El panel no comenta en GitHub, no commitea, no hace push y no consulta producción.

Lee primero el perfil del proyecto: `<raíz>/.claude/pandilla.md`. Si no existe, avisa que falta y propone `/pandilla:iniciar`; mientras tanto usa la base `main` (o `origin/HEAD`) y el ruteo por defecto de §3.

## Argumentos

`/panel [--base <ref>] [--pr <n>] [--ref <sha>] [--pedido "<texto>"] [--capturas <dir>] [--re-revision <informe.md>] [--panel a,b,c]`

- Sin argumentos: la rama actual contra la base del perfil, incluidos los cambios sin commitear.
- `--pr <n>`: un PR de GitHub (abierto o mergeado). `--ref <sha>`: un commit. Sirven también para calibrar con cambios viejos que después tuvieron un bug conocido.
- `--pedido`: el pedido o el ticket. Sin él, el contexto sale del brief de la tarea, del PR o de los commits.
- `--capturas`: capturas de la prueba local, para `superficies`.
- `--re-revision`: informe anterior. El verificador marca cada hallazgo previo como RESUELTO, NO RESUELTO o YA NO APLICA.
- `--panel`: fuerza la lista de revisores.

## 1. Diff

- **Rama actual:** si la base es remota (`origin/<x>`), primero `git fetch origin <x> --quiet`. `BASE=$(git merge-base <base> HEAD)`. Con cambios sin commitear, el diff es `git diff $BASE`; sin ellos, `git diff $BASE...HEAD`.
- **`--pr <n>`:** `gh pr view <n> --json state,baseRefName,headRefOid,mergeCommit,files`. Mergeado: `HEAD=<mergeCommit>`, `BASE=<mergeCommit>^`. Abierto: `git fetch origin pull/<n>/head` y `BASE=$(git merge-base <base> <headRefOid>)`.
- **`--ref <sha>`:** `HEAD=<sha>`, `BASE=<sha>^`.
- Si HEAD no es el árbol de trabajo, los revisores leen con `git show <HEAD>:<ruta>`.
- Si el diff está vacío, termina diciéndolo.
- **Pisadas:** `git diff --numstat $BASE`. Un archivo ajeno al pedido con muchas líneas borradas (lockfile, `package.json`, `CLAUDE.md`, migraciones existentes) va arriba del informe como C, sin pasar por el verificador. Es el error típico de commitear desde un checkout sucio.
- **Secretos y datos reales:** archivos `.env*`, llaves, o fixtures con datos de personas reales van arriba como C.

## 2. Contexto compartido (una sola vez)

- El pedido.
- Las reglas del proyecto: `CLAUDE.md`, la sección «Reglas del proyecto» del perfil, y las páginas de docs, specs o ADR del área que el perfil indique para cada tipo.
- No pegues el diff en los prompts: cada revisor lo lee con git.

## 3. Ruteo

Usa la tabla «Rutas y revisores» del perfil: tipo → rutas → revisores. Los revisores del plugin son `correctitud`, `sistemas`, `seguridad`, `datos`, `superficies`, `infra` y `costos`; el perfil puede agregar revisores propios (§4).

Sin perfil, este ruteo por defecto:

| Tipo | Rutas típicas | Revisores |
|---|---|---|
| ui | `*.tsx`, `*.vue`, `*.svelte`, `app/`, `pages/`, `components/`, `messages/`, `locales/` | `superficies`, `correctitud` |
| backend | `api/`, `server/`, `src/` (sin UI), `lib/`, `packages/` | `correctitud`, `sistemas`, `seguridad`, `datos`, `costos` |
| datos | `migrations/`, `schema.*`, `prisma/`, `drizzle/`, `db/` | `datos`, `seguridad`, `correctitud` |
| infra | `.github/`, `infra/`, `terraform/`, `Dockerfile*`, `*.yml` de despliegue, `scripts/*.sh` | `infra`, `seguridad`, `costos` |
| docs | `docs/`, `*.md` | `superficies` |
| generado | lockfiles, código generado, `dist/`, `coverage/` | no cuentan |

Reglas que valen siempre (además de las del perfil):

- **Unión sin duplicados:** cada revisor entra una vez y recibe todos sus archivos.
- `seguridad` se suma en cualquier tipo si el diff contiene `auth`, `session`, `token`, `password`, `permission`, `role`, `redirect`, `cookie`, `cors`, `webhook`, `secret`, `dangerouslySetInnerHTML`, `eval` o consultas armadas con strings.
- `superficies` se suma si cambia algo que ve una persona: textos, correos, notificaciones, mensajes de error.
- **Diff chico** (≤ 30 líneas, ≤ 2 archivos, sin migración ni infra): `correctitud` y el especialista más pertinente.

Muestra el panel en una línea, con la razón de cada revisor, y sigue sin esperar confirmación.

## 4. Revisores en paralelo

Lanza todos en **un solo mensaje**, con varias llamadas a `Agent` y `run_in_background: false`:

- `subagent_type: "pandilla:revisor-<nombre>"` (los del plugin; usan Sonnet);
- un revisor propio del proyecto (`.claude/pandilla/revisores/<nombre>.md`): `subagent_type: "general-purpose"`, `model: "sonnet"`, y el brief empieza con «Primero lee `<raíz>/.claude/pandilla/revisores/<nombre>.md`: define tu rol, tus reglas y tu formato de salida».
- Si un revisor del plugin tiene un archivo con el mismo nombre en `.claude/pandilla/revisores/`, pásale también esa ruta: lo complementa.

Brief de cada uno:

```
Checkout: <ruta absoluta>
Perfil: <raíz>/.claude/pandilla.md (o "no hay")
Diff: BASE=<sha> HEAD=<sha | árbol de trabajo> (si HEAD es un sha: lee con git show HEAD:ruta)
Tus archivos: <lista>
Todos los archivos del diff: <lista> (puedes abrirlos si los necesitas)
Pedido: <resumen, máx. 15 líneas>
Reglas y docs del área: <rutas>
Complemento del proyecto: <ruta en .claude/pandilla/revisores/ o "no hay">
Capturas: <rutas o "no hay">
Re-revisión: <ruta del informe anterior o "no">
Sigue tu formato de salida exacto.
```

## 5. Verificación

Con todas las salidas, lanza un solo `Agent` con `subagent_type: "pandilla:verificador"` (usa Opus). Pásale el mismo encabezado, las salidas completas de los revisores y el informe anterior si es re-revisión. No filtres ni reescribas hallazgos antes del verificador: su trabajo es descartar los falsos.

## 6. Informe

Guarda el resultado en `<checkout>/tmp/panel/<rama-o-pr>-<AAAAMMDD-HHMM>.md` (o la carpeta de informes que diga el perfil; tiene que estar ignorada por git). Al inicio: base, head y panel usado. Al final: revisores, hallazgos brutos frente a confirmados, y descartados.

Al usuario: el veredicto, la tabla de hallazgos vigentes y la ruta del informe. No repitas los descartados.

## 7. Regla de commit

- **CAMBIOS REQUERIDOS:** corrige los C y W confirmados o plausibles (los S a criterio, avisando cuáles quedaron). Repite las compuertas que correspondan y corre `/panel --re-revision <informe>`. Máximo 3 vueltas; si en la tercera sigue habiendo C o W, para y pregunta.
- **APROBADO:** recién entonces se commitea, si el usuario autorizó el commit de esta tarea (directamente, o vía /lote o /entrega). Lo que sigue (PR o commit local) lo dice el perfil en «Publicación».
- Si el panel se usó para calibrar (`--pr` o `--ref` de algo ya mergeado), no hay commit: solo informe. Para medir si el panel sirve, junta los resultados en `tmp/panel/calibracion.md`: por cada bug conocido, ¿el panel lo habría visto? (sí, parcial o no).
