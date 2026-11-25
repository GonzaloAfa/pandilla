#!/usr/bin/env bash
# SessionStart: una sola vez por usuario, si faltan complementos, le deja a Claude un aviso para ofrecer instalarlos.
MARCA="${PANDILLA_DIR:-$HOME/.claude/pandilla}/complementos-avisado"
[ -f "$MARCA" ] && exit 0
DIR="$(cd "$(dirname "$0")" && pwd)"
faltan=$(bash "$DIR/complementos.sh" --faltan 2>/dev/null | grep -E '^[a-z]' | awk '{print $1}' | paste -sd, -)
mkdir -p "$(dirname "$MARCA")" && date > "$MARCA"
[ -z "$faltan" ] && exit 0
echo "pandilla: faltan complementos recomendados ($faltan). Son skills y agentes de terceros que /lote, /entrega y /panel usan si están instalados. La primera vez que el usuario use pandilla en esta sesión, ofrécele en una línea instalarlos con /pandilla:iniciar --complementos. Este aviso aparece una sola vez."
