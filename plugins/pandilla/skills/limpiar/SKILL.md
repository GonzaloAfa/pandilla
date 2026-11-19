---
name: limpiar
description: >-
  Limpia los worktrees que ya cumplieron (PR mergeado o cerrado, o rama ya en la base), sin cambios ni commits que solo existan ahí, sin procesos corriendo adentro y sin tocar hace un rato; reporta el resto con su motivo. También instala la limpieza automática dos veces al día. Usar con "/pandilla:limpiar", "limpia los worktrees", "¿cuánto disco ocupan los worktrees?", "borra los worktrees de PRs cerrados".
---

# /limpiar

Cada tarea de `/pandilla:lote` deja un worktree con sus dependencias instaladas. Sin limpieza, se acumulan y llenan el disco.

El script está en `<plugin>/scripts/limpiar_worktrees.py` (`<plugin>` es la carpeta dos niveles arriba de esta skill).

## Reglas (no se negocian)

Borra un worktree **solo** si cumple todo esto:

- su PR está mergeado o cerrado, o, en repos sin PR, su rama ya está en la base;
- no tiene cambios sin guardar (`git status` vacío);
- no tiene commits que solo existan ahí: su `HEAD` es el del PR o un ancestro de él, o ya está en la base;
- ningún proceso tiene su directorio actual adentro (dev5, servidores, sesiones);
- nadie lo tocó en la última hora (`--horas` lo cambia).

También borra, aunque no tenga PR, el worktree que no tiene cambios ni commits propios (todo su contenido ya está en el remoto o en la base) y lleva 3 días sin tocarse (`--dias-sin-uso` lo cambia): restos de T3, worktrees de regresión, ramas temporales ya subidas.

Borra solo la carpeta, con `git worktree remove` y sin `--force`. La rama y sus commits quedan en el repo. Lo que no cumple todo va al informe con su motivo: eso lo decide una persona, nunca el script.

## Pasos

1. En seco: `python3 <plugin>/scripts/limpiar_worktrees.py` (todos los repos de `~/Documents/GitHub` con worktrees; `--repo <ruta>` para uno solo).
2. Muestra el resultado: cuántos se pueden borrar, cuántos GB según `du` (con dependencias clonadas por APFS, el espacio real liberado es menor) y la lista «por revisar» con sus motivos.
3. Si el usuario pidió limpiar, aplica: `--aplicar`. Mide `df` antes y después para dar el espacio real.
4. «Por revisar» no se borra. Si el usuario quiere borrar alguno, pregunta uno por uno y revisa antes qué cambios o commits se perderían.

## Limpieza automática

Para que corra sola (macOS), instala un LaunchAgent que llame al script con `--aplicar --horas 2` a las 10:00 y a las 18:30, con log en `~/.claude/pandilla/limpieza.log`:

- usa rutas absolutas: el `python3` del sistema o de Homebrew (no el de un entorno virtual) y un `PATH` que incluya `git` y `gh`;
- el script queda en la ruta del plugin instalado o de un clon estable del repo;
- prueba con `launchctl kickstart gui/$(id -u)/<label>` y revisa el log.

Pregunta antes de instalarlo: es una tarea programada en la máquina del usuario.
