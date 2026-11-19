#!/usr/bin/env bash
# Prepara un worktree para que varios agentes trabajen en paralelo sin pisarse.
#
# Uso (desde el worktree):
#   bash entorno.sh [--instalar "<comando>"] [--puerto NOMBRE=BASE ...] [--var NOMBRE=VALOR ...]
#                   [--negar <herramienta> ...] [--copiar <archivo> ...] [--borrar]
#
#   --instalar "pnpm install --frozen-lockfile"  comando de instalación (corre en la raíz del worktree)
#   --puerto DEV=23000 --puerto E2E=24000         un puerto libre por nombre: BASE, BASE+1, … (no repite
#                                                 los de otros worktrees aunque estén apagados)
#   --var 'API_URL=http://localhost:$DEV'         variables extra; $NOMBRE se reemplaza por el puerto asignado
#   --negar mcp__Neon                             herramientas negadas en .claude/settings.local.json del worktree
#   --copiar .env                                 archivos sin versionar que se copian del checkout principal
#   --borrar                                      cierra lo que escucha en sus puertos y borra .wt-env
#
# Escribe .wt-env con `export NOMBRE=puerto` y las variables; cada comando se corre con `wt <comando>`.
# Volver a correrlo conserva los puertos ya asignados.
set -euo pipefail

raiz="$(git rev-parse --show-toplevel)"
comun="$(cd "$(git rev-parse --git-common-dir)" && pwd)"
principal="$(dirname "$comun")"
wtenv="$raiz/.wt-env"

instalar=""; puertos=(); vars=(); negar=(); copiar=(); borrar=0
while [ $# -gt 0 ]; do
  case "$1" in
    --instalar) instalar="$2"; shift 2 ;;
    --puerto) puertos+=("$2"); shift 2 ;;
    --var) vars+=("$2"); shift 2 ;;
    --negar) negar+=("$2"); shift 2 ;;
    --copiar) copiar+=("$2"); shift 2 ;;
    --borrar) borrar=1; shift ;;
    *) echo "argumento desconocido: $1" >&2; exit 2 ;;
  esac
done

[ "$raiz" != "$principal" ] || { echo "corre esto en un worktree, no en el checkout principal ($principal)" >&2; exit 2; }

valor_de() { sed -n "s/^export $2=//p" "$1/.wt-env" 2>/dev/null || true; }
nombres_de_puertos() { sed -n 's/^# puertos: //p' "$1/.wt-env" 2>/dev/null || true; }

if [ "$borrar" = 1 ]; then
  for nombre in $(nombres_de_puertos "$raiz"); do
    p="$(valor_de "$raiz" "$nombre")"
    pids="$(lsof -ti tcp:"$p" -sTCP:LISTEN 2>/dev/null || true)"
    [ -z "$pids" ] || { echo "cierro lo que escucha en :$p ($pids)"; kill $pids 2>/dev/null || true; }
  done
  rm -f "$wtenv"
  echo "worktree limpio: puertos libres y .wt-env borrado (la rama y sus commits quedan)"
  exit 0
fi

for patron in '/.wt-env' '/.claude/settings.local.json'; do
  grep -qxF "$patron" "$comun/info/exclude" 2>/dev/null || echo "$patron" >> "$comun/info/exclude"
done

for archivo in "${copiar[@]+"${copiar[@]}"}"; do
  if [ -f "$principal/$archivo" ] && [ ! -f "$raiz/$archivo" ]; then
    mkdir -p "$(dirname "$raiz/$archivo")"; cp "$principal/$archivo" "$raiz/$archivo"; echo "copiado $archivo"
  fi
done

[ -z "$instalar" ] || { echo "instalando: $instalar"; (cd "$raiz" && bash -c "$instalar"); }

if [ ${#negar[@]} -gt 0 ]; then
  mkdir -p "$raiz/.claude"
  python3 - "$raiz/.claude/settings.local.json" "${negar[@]}" <<'PY'
import json, os, sys
ruta, reglas = sys.argv[1], sys.argv[2:]
datos = json.load(open(ruta)) if os.path.exists(ruta) else {}
deny = datos.setdefault("permissions", {}).setdefault("deny", [])
deny.extend(r for r in reglas if r not in deny)
with open(ruta, "w") as f:
    json.dump(datos, f, indent=2)
    f.write("\n")
PY
fi

tomados=" "
while read -r linea; do
  ruta="${linea#worktree }"
  [ "$ruta" = "$raiz" ] && continue
  for nombre in $(nombres_de_puertos "$ruta"); do tomados+="$(valor_de "$ruta" "$nombre") "; done
done < <(git -C "$raiz" worktree list --porcelain | grep '^worktree ')
libre() { [[ "$tomados" != *" $1 "* ]] && ! lsof -ti tcp:"$1" -sTCP:LISTEN >/dev/null 2>&1; }

asignados=(); nombres=""
for par in "${puertos[@]+"${puertos[@]}"}"; do
  nombre="${par%%=*}"; base="${par##*=}"
  actual="$(valor_de "$raiz" "$nombre")"
  if [ -n "$actual" ] && [[ "$tomados" != *" $actual "* ]]; then
    p="$actual"
  else
    p=""
    for n in $(seq 0 199); do libre $((base + n)) && { p=$((base + n)); break; }; done
    [ -n "$p" ] || { echo "no hay puerto libre para $nombre desde $base" >&2; exit 1; }
  fi
  tomados+="$p "; asignados+=("$nombre=$p"); nombres+="$nombre "
done

{
  echo "# Generado por pandilla/scripts/entorno.sh. Úsalo con: wt <comando>"
  echo "# puertos: ${nombres% }"
  for a in "${asignados[@]+"${asignados[@]}"}"; do echo "export $a"; done
  for v in "${vars[@]+"${vars[@]}"}"; do
    valor="${v#*=}"
    for a in "${asignados[@]+"${asignados[@]}"}"; do valor="${valor//\$${a%%=*}/${a##*=}}"; done
    echo "export ${v%%=*}=\"$valor\""
  done
} > "$wtenv"

echo "listo: ${asignados[*]+"${asignados[*]}"}"
