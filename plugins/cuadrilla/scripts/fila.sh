#!/usr/bin/env bash
# Fila para un recurso que solo admite un worktree a la vez (un simulador, un e2e pesado, una base compartida).
# Uso: bash "${CLAUDE_PLUGIN_ROOT}/scripts/fila.sh" <recurso> -- <comando...>
# Espera a que el recurso quede libre, corre el comando y lo libera al salir (aunque falle).
# Un candado cuyo dueño murió, o que quedó sin dueño más de un minuto, se recupera solo.
# Correrlo como comando en segundo plano.
set -euo pipefail

recurso="${1:?falta el recurso}"; shift
case "$recurso" in
  *[!a-z0-9-]*) echo "recurso inválido: solo a-z, 0-9 y guion" >&2; exit 2 ;;
esac
[ "${1:-}" = "--" ] && shift
[ $# -gt 0 ] || { echo "falta el comando" >&2; exit 2; }

candado="/tmp/cuadrilla-fila-${recurso}.lock"
yo="$$ $(git rev-parse --show-toplevel 2>/dev/null || pwd)"

liberar_si_abandonado() {
  local duenio pid edad
  duenio="$(cat "$candado/duenio" 2>/dev/null || true)"
  pid="${duenio%% *}"
  if [ -n "$pid" ]; then
    kill -0 "$pid" 2>/dev/null && return 1
  else
    # Sin dueño: quien lo tomó murió entre el mkdir y escribir su nombre.
    edad=$(( $(date +%s) - $(stat -f %m "$candado" 2>/dev/null || stat -c %Y "$candado" 2>/dev/null || date +%s) ))
    [ "$edad" -gt 60 ] || return 1
  fi
  # mv es atómico: si dos procesos ven el mismo candado abandonado, solo uno lo retira.
  if mv "$candado" "$candado.abandonado.$$" 2>/dev/null; then
    if [ "$(cat "$candado.abandonado.$$/duenio" 2>/dev/null || true)" != "$duenio" ]; then
      # Entre la revisión y el mv otro proceso tomó el recurso: se lo devuelvo.
      mv "$candado.abandonado.$$" "$candado" 2>/dev/null || true
      return 1
    fi
    echo "candado abandonado (${duenio:-sin dueño}): lo libero"
    rm -rf "$candado.abandonado.$$"
  fi
  return 0
}

while ! mkdir "$candado" 2>/dev/null; do
  liberar_si_abandonado && continue
  echo "$(date +%H:%M:%S) ${recurso} ocupado por: $(cat "$candado/duenio" 2>/dev/null || echo '?'); espero…"
  sleep 20
done
echo "$yo" > "$candado/duenio"
trap 'rm -rf "$candado"' EXIT
echo "$(date +%H:%M:%S) ${recurso} tomado por ${yo}"
"$@"
