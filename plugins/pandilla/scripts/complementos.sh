#!/usr/bin/env bash
# Complementos de pandilla: skills y agentes de terceros que pandilla usa si están instalados.
# Uso:
#   complementos.sh                 tabla: nombre · tipo · estado · ruta
#   complementos.sh --faltan        solo los que faltan, con su comando de instalación
#   complementos.sh --ruta <nombre> imprime la ruta del SKILL.md o del agente instalado (vacío si falta)
# Busca en el usuario (~/.claude) y en el repo actual (.claude/). No instala nada.
set -u

RAIZ_REPO=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
EMIL_CMD='npx skills@latest add emilkowalski/skills -g -a claude-code -y'
AGENCY_CMD='d=$(mktemp -d) && git clone --depth 1 -q https://github.com/msitarzewski/agency-agents "$d" && mkdir -p ~/.claude/agents/testing ~/.claude/agents/product && cp "$d"/testing/testing-{reality-checker,evidence-collector,api-tester,accessibility-auditor}.md ~/.claude/agents/testing/ && cp "$d"/product/product-manager.md ~/.claude/agents/product/ && rm -rf "$d"'

# nombre|tipo|nombres alternativos (skill: carpeta; agente: valor de name:)|fuente|instalación
CATALOGO=$(cat <<EOF
emil-design-foundations|skill|emil-design-foundations|Emil Kowalski (serie emil-*)|manual: desde la fuente donde la conseguiste
emil-ui-polish|skill|emil-ui-polish|Emil Kowalski (serie emil-*)|manual: desde la fuente donde la conseguiste
emil-ui-review|skill|emil-ui-review|Emil Kowalski (serie emil-*)|manual: desde la fuente donde la conseguiste
prototype|skill|emil-prototype prototype|Emil Kowalski (emilkowalski/skills, MIT)|$EMIL_CMD --skill prototype
break-ui|skill|break-ui emil-break-ui|Emil Kowalski (emilkowalski/skills, MIT)|$EMIL_CMD --skill break-ui
mobile-native|skill|mobile-native emil-mobile-native|Emil Kowalski (emilkowalski/skills, MIT)|$EMIL_CMD --skill mobile-native
product-manager|agente|Product Manager|agency-agents (msitarzewski/agency-agents, MIT)|$AGENCY_CMD
reality-checker|agente|Reality Checker|agency-agents (msitarzewski/agency-agents, MIT)|$AGENCY_CMD
evidence-collector|agente|Evidence Collector|agency-agents (msitarzewski/agency-agents, MIT)|$AGENCY_CMD
api-tester|agente|API Tester|agency-agents (msitarzewski/agency-agents, MIT)|$AGENCY_CMD
accessibility-auditor|agente|Accessibility Auditor|agency-agents (msitarzewski/agency-agents, MIT)|$AGENCY_CMD
EOF
)

buscar_skill() {
  local alt
  for alt in $1; do
    for base in "$RAIZ_REPO/.claude/skills" "$HOME/.claude/skills" "$HOME/.agents/skills"; do
      [ -f "$base/$alt/SKILL.md" ] && { echo "$base/$alt/SKILL.md"; return; }
    done
  done
}

buscar_agente() {
  local nombre="$1" dir f
  for dir in "$RAIZ_REPO/.claude/agents" "$HOME/.claude/agents"; do
    [ -d "$dir" ] || continue
    f=$(grep -rlx --include='*.md' "name: $nombre" "$dir" 2>/dev/null | head -1)
    [ -n "$f" ] && { echo "$f"; return; }
  done
}

ruta_de() {
  local tipo="$1" alts="$2"
  if [ "$tipo" = skill ]; then buscar_skill "$alts"; else buscar_agente "$alts"; fi
}

modo="${1:-tabla}"
if [ "$modo" = "--ruta" ]; then
  objetivo="${2:?falta el nombre}"
  while IFS='|' read -r nombre tipo alts fuente cmd; do
    [ "$nombre" = "$objetivo" ] && { ruta_de "$tipo" "$alts"; exit 0; }
  done <<< "$CATALOGO"
  exit 1
fi

faltan=0
while IFS='|' read -r nombre tipo alts fuente cmd; do
  ruta=$(ruta_de "$tipo" "$alts")
  if [ -n "$ruta" ]; then
    [ "$modo" = "--faltan" ] || printf '%-24s %-7s instalado  %s\n' "$nombre" "$tipo" "$ruta"
  else
    faltan=$((faltan + 1))
    if [ "$modo" = "--faltan" ]; then
      printf '%-24s %-7s %s\n    %s\n' "$nombre" "$tipo" "$fuente" "$cmd"
    else
      printf '%-24s %-7s FALTA\n' "$nombre" "$tipo"
    fi
  fi
done <<< "$CATALOGO"
[ "$modo" = "--faltan" ] && [ "$faltan" -eq 0 ] && echo "Todos los complementos están instalados."
exit 0
