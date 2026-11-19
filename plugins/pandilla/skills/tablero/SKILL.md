---
name: tablero
description: >-
  Abre el tablero local de pandilla (http://localhost:7788): cada sesión de Claude Code como una mesa, con sus subagentes, qué herramienta usa cada uno, cuántos tokens lleva, los hallazgos y veredictos del panel, y un registro en vivo. Usar con "/pandilla:tablero", "abre el tablero", "¿cómo van los agentes?".
---

# /tablero

El hook del plugin anota cada evento de las sesiones (inicio, pedido, herramienta, subagente, fin) en `~/.claude/pandilla/events.jsonl` (o en `$PANDILLA_DIR`). Este tablero lo lee y lo muestra. Todo queda en este computador: el servidor solo escucha en `127.0.0.1`.

1. ¿Ya está arriba? `curl -s -o /dev/null -w '%{http_code}' http://localhost:${PANDILLA_PUERTO:-7788}/api/state`.
2. Si no, levántalo desacoplado de esta sesión. El servidor está en la carpeta `tablero/` del plugin, dos niveles arriba de esta skill:
   `nohup python3 <plugin>/tablero/board.py > ~/.claude/pandilla/board.log 2>&1 & disown`
   (crea `~/.claude/pandilla/` antes si no existe).
3. Dale al usuario la URL: http://localhost:7788. Si el puerto está ocupado por otra cosa, usa `PANDILLA_PUERTO=<otro>`.

Para cerrarlo: `pkill -f "pandilla.*tablero/board.py"`.

Qué guarda el hook: el tipo de evento, la sesión, la carpeta, la herramienta y un resumen corto de su entrada (archivo, comando o descripción), los primeros 200 caracteres de cada pedido y los primeros 300 de la última respuesta de cada agente. El archivo rota a los 20 MB. Para borrar el historial, borra `~/.claude/pandilla/events.jsonl`.
