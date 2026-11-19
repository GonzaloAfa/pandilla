#!/usr/bin/env python3
"""Hook de cuadrilla: registra eventos de sesiones y subagentes en un archivo local para el tablero.

Todo queda en este computador (por defecto ~/.claude/cuadrilla/events.jsonl; CUADRILLA_DIR lo cambia).
Guarda resúmenes cortos: herramienta, archivo o comando, y los primeros 200 caracteres de cada pedido."""
import json, os, sys, time

BOARD_DIR = os.path.expanduser(os.environ.get("CUADRILLA_DIR", "~/.claude/cuadrilla"))
EVENTS = os.path.join(BOARD_DIR, "events.jsonl")
MAX_BYTES = 20 * 1024 * 1024


def short(value, limit=160):
    if value is None:
        return None
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(text.split())
    return text[:limit] + ("…" if len(text) > limit else "")


def summarize_tool(tool_input):
    if not isinstance(tool_input, dict):
        return None
    for key in ("description", "file_path", "command", "pattern", "query", "url", "skill", "prompt"):
        if tool_input.get(key):
            return short(tool_input[key])
    return short(tool_input)


def count_findings(message):
    counts = {"C": 0, "W": 0, "S": 0}
    for line in message.splitlines():
        line = line.strip().lstrip("-").strip()
        if line.startswith("severidad:"):
            sev = line.split(":", 1)[1].strip()[:1]
            if sev in counts:
                counts[sev] += 1
        elif line.startswith("| ") and line.count("|") > 4:
            cell = line.split("|")[2].strip()
            if cell in counts:
                counts[cell] += 1
    return counts if any(counts.values()) else None


def headline(message):
    for line in message.splitlines():
        line = line.strip().lstrip("-").strip()
        if line.startswith("titulo:"):
            return short(line.split(":", 1)[1].strip(), 120)
        if line.startswith("#### "):
            return short(line[5:].replace("·", "—"), 120)
    return None


def transcript_tokens(path):
    if not path or not os.path.exists(path):
        return None
    output, context = 0, 0
    try:
        with open(path) as f:
            for line in f:
                usage = (json.loads(line).get("message") or {}).get("usage") or {}
                if not usage:
                    continue
                output += usage.get("output_tokens") or 0
                context = sum(usage.get(k) or 0 for k in ("input_tokens", "cache_read_input_tokens", "cache_creation_input_tokens"))
    except Exception:
        return None
    return context + output


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except Exception:
        return
    tool_input = data.get("tool_input")
    record = {
        "ts": time.time(),
        "event": data.get("hook_event_name"),
        "session": data.get("session_id"),
        "agent_id": data.get("agent_id"),
        "agent_type": data.get("agent_type"),
        "cwd": data.get("cwd"),
        "tool": data.get("tool_name"),
        "tool_use_id": data.get("tool_use_id"),
        "summary": summarize_tool(tool_input),
        "subagent_type": tool_input.get("subagent_type") if isinstance(tool_input, dict) else None,
        "agent_description": tool_input.get("description") if isinstance(tool_input, dict) and data.get("tool_name") == "Agent" else None,
        "prompt": short(data.get("prompt"), 200),
    }
    if record["event"] in ("SubagentStop", "Stop"):
        message = data.get("last_assistant_message") or ""
        record["last_message"] = short(message, 300)
        record["findings"] = count_findings(message)
        record["headline"] = headline(message)
        if "Veredicto: APROBADO" in message:
            record["verdict"] = "APROBADO"
        elif "CAMBIOS REQUERIDOS" in message:
            record["verdict"] = "CAMBIOS REQUERIDOS"
    if record["event"] == "SubagentStop":
        record["tokens"] = transcript_tokens(data.get("agent_transcript_path"))
    os.makedirs(BOARD_DIR, exist_ok=True)
    if os.path.exists(EVENTS) and os.path.getsize(EVENTS) > MAX_BYTES:
        os.replace(EVENTS, EVENTS + ".1")
    with open(EVENTS, "a") as f:
        f.write(json.dumps({k: v for k, v in record.items() if v is not None}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
