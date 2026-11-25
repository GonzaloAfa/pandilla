#!/usr/bin/env python3
"""UserPromptSubmit: avisa cuando el contexto de la sesión pasa un umbral.

Lee el tamaño del último turno del transcript (input + caché) y, al cruzar
PANDILLA_AVISO_CONTEXTO (por defecto 300000 tokens) y después cada 50000 más,
le deja a Claude un aviso para proponer /compact o un traspaso a una sesión
nueva. Un aviso por escalón y por sesión. Nunca bloquea el prompt.
"""
import json
import os
import sys

UMBRAL = int(os.environ.get("PANDILLA_AVISO_CONTEXTO", "300000"))
PASO = 50000
DIR = os.path.join(os.environ.get("PANDILLA_DIR", os.path.expanduser("~/.claude/pandilla")), "contexto")


def contexto_actual(ruta):
    """Tokens de entrada del último turno con usage, leyendo solo el final del archivo."""
    with open(ruta, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 2_000_000))
        lineas = f.read().decode("utf-8", "replace").splitlines()
    for linea in reversed(lineas):
        try:
            mensaje = json.loads(linea).get("message") or {}
        except ValueError:
            continue
        uso = mensaje.get("usage") if isinstance(mensaje, dict) else None
        if uso:
            return (uso.get("input_tokens", 0) + uso.get("cache_read_input_tokens", 0)
                    + uso.get("cache_creation_input_tokens", 0))
    return 0


def main():
    try:
        entrada = json.load(sys.stdin)
        ruta, sesion = entrada.get("transcript_path"), entrada.get("session_id", "sin-id")
        if not ruta or not os.path.exists(ruta):
            return
        tokens = contexto_actual(ruta)
    except Exception:
        return
    if tokens < UMBRAL:
        return
    escalon = UMBRAL + (tokens - UMBRAL) // PASO * PASO
    os.makedirs(DIR, exist_ok=True)
    marca = os.path.join(DIR, sesion)
    try:
        ultimo = int(open(marca).read().strip() or 0)
    except (OSError, ValueError):
        ultimo = 0
    if escalon <= ultimo:
        return
    with open(marca, "w") as f:
        f.write(str(escalon))
    aviso = (
        f"pandilla: el contexto de esta sesión va en {tokens // 1000}k tokens. Con más de ~300k la calidad baja "
        "(olvida instrucciones del principio). Antes de seguir con el pedido, dile al usuario en una línea que conviene "
        "compactar o traspasar: si la tarea sigue, guarda el estado en su informe y propone `/compact <foco>`; si empieza "
        "otra tarea, propone `/clear` o una sesión nueva. Luego atiende el pedido."
    )
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": aviso}},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
