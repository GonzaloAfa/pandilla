#!/usr/bin/env bash
# Busca código copiado que este diff agrega: bloques de las líneas nuevas que ya existen
# en la misma carpeta, en la carpeta padre o en otro archivo del diff. Usa jscpd vía npx.
# Uso: duplicados.sh <base> [--min-lineas N]   (por defecto 6)
# Salida: una línea por duplicado y, al final, «DUPLICADOS: <n>». Sale con 1 si hay alguno.
set -euo pipefail

BASE="${1:?uso: duplicados.sh <base> [--min-lineas N]}"
MIN=6
[ "${2:-}" = "--min-lineas" ] && MIN="${3:?falta N}"

RAIZ=$(git rev-parse --show-toplevel)
cd "$RAIZ"
MB=$(git merge-base "$BASE" HEAD)
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

git diff --name-only --diff-filter=AM "$MB" -- \
  ':!**/__generated__/**' ':!**/*.lock' ':!**/package-lock.json' ':!**/dist/**' ':!**/build/**' \
  | grep -E '\.(ts|tsx|js|jsx|mjs|py|go|rb|java|kt|swift|vue|svelte)$' > "$TMP/archivos" || true
if [ ! -s "$TMP/archivos" ]; then echo "DUPLICADOS: 0 (sin archivos de código en el diff)"; exit 0; fi

N=$(wc -l < "$TMP/archivos" | tr -d ' ')
if [ "$N" -gt 60 ]; then echo "DUPLICADOS: no se revisó ($N archivos de código en el diff; el máximo es 60)"; exit 0; fi

# Alcance: la carpeta de cada archivo cambiado y su carpeta padre. La duplicación contra
# paquetes lejanos la busca el revisor «diseno» por concepto; escanear paquetes enteros no escala.
while read -r f; do d=$(dirname "$f"); echo "$d"; dirname "$d"; done < "$TMP/archivos" \
  | grep -vx '\.' | sort -u > "$TMP/carpetas"
# Quita las carpetas que ya están dentro de otra de la lista.
python3 - "$TMP/carpetas" > "$TMP/paquetes" <<'PY'
import sys
c = sorted(set(open(sys.argv[1]).read().split()), key=len)
fin = []
for d in c:
    if not any(d == p or d.startswith(p + "/") for p in fin): fin.append(d)
print("\n".join(fin))
PY
[ -s "$TMP/paquetes" ] || echo "." > "$TMP/paquetes"

# Líneas agregadas por archivo, para quedarnos solo con duplicados que tocan código nuevo.
git diff -U0 "$MB" -- $(cat "$TMP/archivos") > "$TMP/diff"

PAQS=()
while IFS= read -r p; do PAQS+=("$p"); done < "$TMP/paquetes"
NODE_OPTIONS=--max-old-space-size=4096 npx -y jscpd@4 --silent --min-lines "$MIN" --min-tokens 50 --reporters json --output "$TMP/jscpd" \
  --ignore "**/node_modules/**,**/__generated__/**,**/dist/**,**/build/**,**/.next/**,**/coverage/**,**/*.d.ts,**/*.min.js" \
  "${PAQS[@]}" > /dev/null 2>&1 || true

python3 - "$TMP/jscpd/jscpd-report.json" "$TMP/diff" "$TMP/archivos" <<'EOF'
import json, re, sys, os
reporte, diff_path, archivos_path = sys.argv[1:4]
if not os.path.exists(reporte):
    print("DUPLICADOS: no se pudo correr jscpd"); sys.exit(0)
archivos = set(open(archivos_path).read().split())
nuevas, actual = {}, None
for linea in open(diff_path, encoding="utf-8", errors="replace"):
    if linea.startswith("+++ b/"): actual = linea[6:].strip(); nuevas.setdefault(actual, set())
    m = re.match(r"@@ -\S+ \+(\d+)(?:,(\d+))? @@", linea)
    if m and actual:
        ini, n = int(m.group(1)), int(m.group(2) or 1)
        nuevas[actual].update(range(ini, ini + n))
def toca(f, ini, fin):
    f = os.path.relpath(f) if os.path.isabs(f) else os.path.normpath(f)
    return f in archivos and any(l in nuevas.get(f, ()) for l in range(ini, fin + 1)), f
vistos, n = set(), 0
for d in json.load(open(reporte)).get("duplicates", []):
    a, b = d["firstFile"], d["secondFile"]
    ta, fa = toca(a["name"], a["start"], a["end"])
    tb, fb = toca(b["name"], b["start"], b["end"])
    if not (ta or tb): continue
    nuevo, otro = ((fa, a), (fb, b)) if ta else ((fb, b), (fa, a))
    clave = (nuevo[0], nuevo[1]["start"], otro[0], otro[1]["start"])
    if clave in vistos: continue
    vistos.add(clave); n += 1
    print(f"{nuevo[0]}:{nuevo[1]['start']}-{nuevo[1]['end']} repite {otro[0]}:{otro[1]['start']}-{otro[1]['end']} ({d['lines']} líneas)")
print(f"DUPLICADOS: {n}")
sys.exit(1 if n else 0)
EOF
