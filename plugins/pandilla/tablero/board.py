#!/usr/bin/env python3
"""Tablero local de pandilla. Lee events.jsonl (lo escribe hook.py) y pizarron.json (lo escribe /pandilla:lote) y
sirve la vista en http://localhost:7788.

Solo escucha en 127.0.0.1. PANDILLA_DIR cambia la carpeta de datos y PANDILLA_PUERTO el puerto."""
import json, os, re, subprocess, time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.expanduser(os.environ.get("PANDILLA_DIR", "~/.claude/pandilla"))
EVENTS = os.path.join(DATA_DIR, "events.jsonl")
BOARD = os.path.join(DATA_DIR, "pizarron.json")
PORT = int(os.environ.get("PANDILLA_PUERTO", "7788"))
ROOMS = 4
WAITING = 2

PHASES = ["investigando", "desarrollando", "verificando", "panel", "probando", "regresion", "entregando"]

state = {"offset": 0, "inode": None, "sessions": {}, "milestones": deque(maxlen=40)}
git_cache = {}

SYSTEM_PREFIXES = ("<task-notification", "<system", "[SYSTEM", "<command-", "<agent-message", "<local-command",
                   "Delegated task", "Caveat:", "This session is being continued")
NOISE = re.compile(r"^(cd|ls|pwd|echo|sleep|true|clear|which|export)\b")


def git_info(cwd):
    if not cwd:
        return None, None
    if cwd not in git_cache:
        def run(*args):
            try:
                return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=2).stdout.strip()
            except Exception:
                return ""
        common = run("rev-parse", "--path-format=absolute", "--git-common-dir")
        repo = os.path.basename(os.path.dirname(common)) if common else os.path.basename(cwd.rstrip("/"))
        git_cache[cwd] = (repo or None, run("rev-parse", "--abbrev-ref", "HEAD") or None)
    return git_cache[cwd]


def is_system_prompt(prompt):
    return (prompt or "").lstrip().startswith(SYSTEM_PREFIXES)


def title_from_prompt(prompt):
    text = " ".join((prompt or "").split())
    if not text:
        return None
    quoted = re.search(r"«([^»]{3,90})»", text)
    if quoted:
        return quoted.group(1)
    pedido = re.search(r"--pedido\s+['\"]([^'\"]{3,90})", text)
    if pedido:
        return pedido.group(1)
    return text[:80] + ("…" if len(text) > 80 else "")


def phase_of(tool, summary, subagent_type):
    s = (summary or "").lower()
    st = (subagent_type or "").lower()
    if tool == "Skill":
        if "panel" in s:
            return "panel"
        if "entrega" in s or "create-pr" in s:
            return "entregando"
        return None
    if tool == "Agent":
        if "revisor" in st or "verificador" in st or "revisor" in s or "verificador" in s or "panel" in s:
            return "panel"
        if "regresi" in s:
            return "regresion"
        if st in ("explore", "plan") or "investig" in s or "busca" in s:
            return "investigando"
        return None
    if tool in ("Read", "Grep", "Glob", "WebFetch", "WebSearch"):
        return "investigando"
    if tool in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
        return "desarrollando"
    if tool == "Bash":
        if re.search(r"gh pr create|git push|git commit|commitear|abrir (el )?pr|push", s):
            return "entregando"
        if "regresi" in s:
            return "regresion"
        if re.search(r"e2e|playwright|fila\.sh|queue\.sh|dev5|pnpm dev|yarn dev|levantar|servidor|localhost|test:integration|integraci", s):
            return "probando"
        if re.search(r"tsc|typecheck|lint|biome|prettier|format|jest|vitest|test|pytest|compuerta|depcruise", s):
            return "verificando"
        if re.search(r"git (log|show|diff|grep|blame|fetch)|grep|rg |buscar|leer|revisar|ver |listar", s):
            return "investigando"
    return None


def humanize(tool, summary):
    s = " ".join((summary or "").split())
    base = lambda p: (p or "").rstrip("/").split("/")[-1]
    if tool == "Read":
        return f"Leyendo {base(s)}"
    if tool in ("Edit", "MultiEdit", "Write"):
        return f"Editando {base(s)}"
    if tool == "Grep":
        return f"Buscando «{s[:50]}»"
    if tool == "Glob":
        return f"Buscando archivos {s[:50]}"
    if tool == "Agent":
        return f"Llamó a: {s[:70]}"
    if tool == "Skill":
        return f"Usando la skill {s[:50]}"
    if tool in ("WebFetch", "WebSearch"):
        return f"Consultando la web: {s[:60]}"
    if tool == "Bash":
        return s[:90]
    return f"{tool}: {s[:70]}" if tool else s[:90]


def session_for(event):
    sid = event.get("session") or "?"
    sessions = state["sessions"]
    if sid not in sessions:
        cwd = event.get("cwd") or ""
        repo, branch = git_info(cwd)
        sessions[sid] = {
            "id": sid, "cwd": cwd, "repo": repo, "branch": branch, "first": event["ts"], "last": event["ts"],
            "status": "trabajando", "title": None, "prompt": None, "phase": None, "reached": [], "now": None,
            "tools": 0, "agents": {}, "pending": [], "verdict": None, "result": None,
        }
    return sessions[sid]


def milestone(s, ts, text, kind):
    state["milestones"].appendleft({"ts": ts, "session": s["id"], "text": text, "kind": kind})


def apply(event):
    s = session_for(event)
    s["last"] = event["ts"]
    kind, agent_id = event.get("event"), event.get("agent_id")
    agent = s["agents"].get(agent_id) if agent_id else None

    if kind == "SubagentStart":
        description = None
        for i, pending in enumerate(s["pending"]):
            if pending["type"] in (event.get("agent_type"), None) or event.get("agent_type") == "general-purpose":
                description = s["pending"].pop(i)["description"]
                break
        s["agents"][agent_id] = {
            "id": agent_id, "type": event.get("agent_type") or "agente", "description": description,
            "start": event["ts"], "end": None, "status": "trabajando", "now": "entrando",
            "tools": 0, "tokens": None, "findings": None, "verdict": None, "headline": None,
        }
        return
    if kind == "SubagentStop" and agent:
        agent.update(end=event["ts"], status="terminó", tokens=event.get("tokens"), findings=event.get("findings"),
                     verdict=event.get("verdict"), headline=event.get("headline"))
        agent["now"] = "terminó" + (f": {event['headline']}" if event.get("headline") else "")
        if event.get("verdict"):
            s["verdict"] = event["verdict"]
            milestone(s, event["ts"], f"Panel: {event['verdict']}", "panel")
        return

    if kind == "PreToolUse":
        tool, summary = event.get("tool"), event.get("summary")
        if agent:
            agent["tools"] += 1
            agent["now"] = humanize(tool, summary)
            agent["status"] = "trabajando"
            return
        s["tools"] += 1
        s["status"] = "trabajando"
        if tool == "Agent":
            s["pending"].append({"type": event.get("subagent_type"), "description": event.get("agent_description")})
        phase = phase_of(tool, summary, event.get("subagent_type"))
        if phase:
            s["phase"] = phase
            if phase not in s["reached"]:
                s["reached"].append(phase)
                if phase == "entregando" and re.search(r"gh pr create|abrir (el )?pr", (summary or "").lower()):
                    milestone(s, event["ts"], "Abriendo el PR", "pr")
        if not (tool == "Bash" and NOISE.match((summary or "").strip())):
            s["now"] = humanize(tool, summary)
    elif kind == "PostToolUseFailure" and not agent:
        s["errors"] = s.get("errors", 0) + 1
    elif kind == "UserPromptSubmit":
        prompt = event.get("prompt")
        if not is_system_prompt(prompt):
            if not s["title"]:
                s["title"] = title_from_prompt(prompt)
            s["prompt"] = prompt
        s["status"] = "trabajando"
    elif kind == "Stop" and not agent:
        s["status"] = "esperando"
        message = (event.get("last_message") or "").strip()
        last_line = message.splitlines()[-1] if message else ""
        if re.match(r"(PR |RAMA |BLOQUEADO)", last_line):
            s["result"] = last_line
            milestone(s, event["ts"], last_line[:120], "bloqueado" if last_line.startswith("BLOQUEADO") else "listo")
        if event.get("verdict"):
            s["verdict"] = event["verdict"]
    elif kind == "SessionEnd":
        s["status"] = "cerrada"
    elif kind == "SessionStart":
        s["status"] = "esperando"
        milestone(s, event["ts"], "Sesión nueva", "inicio")


def refresh():
    if not os.path.exists(EVENTS):
        return
    inode = os.stat(EVENTS).st_ino
    if inode != state["inode"]:
        state.update(inode=inode, offset=0, sessions={})
        state["milestones"].clear()
    with open(EVENTS) as f:
        f.seek(state["offset"])
        for line in f:
            if not line.endswith("\n"):
                break
            state["offset"] += len(line.encode())
            try:
                apply(json.loads(line))
            except Exception:
                continue


def read_board():
    try:
        with open(BOARD) as f:
            return json.load(f)
    except Exception:
        return {"lotes": []}


def matches(task, session):
    if task.get("worktree") and session["cwd"].startswith(task["worktree"].rstrip("/")):
        return True
    if task.get("rama") and session.get("branch") == task["rama"]:
        return True
    prompt = (session.get("prompt") or "") + " " + (session.get("title") or "")
    return any(key and key in prompt for key in (task.get("id"), task.get("titulo")))


def room_from_session(s, task=None):
    agents = sorted(s["agents"].values(), key=lambda a: a["start"])
    shown = [a for a in agents if a["status"] == "trabajando" or (a["end"] and a["end"] >= s["last"] - 600)]
    status = s["status"]
    if task and task.get("estado") in ("lista", "bloqueada"):
        status = task["estado"]
    return {
        "session": s["id"], "id": task.get("id") if task else None,
        "title": (task or {}).get("titulo") or s["title"] or s["branch"] or s["repo"],
        "repo": s["repo"], "branch": (task or {}).get("rama") or s["branch"], "status": status, "phase": s["phase"], "reached": s["reached"],
        "now": s["now"], "start": s["first"], "last": s["last"], "verdict": s["verdict"],
        "result": (task or {}).get("pr") or s["result"],
        "tokens": sum(a.get("tokens") or 0 for a in agents),
        "agents": [{k: a.get(k) for k in ("type", "description", "status", "now", "findings", "verdict")} for a in shown[-8:]],
        "findings": total_findings(agents),
    }


def total_findings(agents):
    verifier = [a for a in agents if "verificador" in (a.get("type") or "") and a.get("findings")]
    source = verifier[-1:] if verifier else [a for a in agents if a.get("findings")]
    total = {"C": 0, "W": 0, "S": 0}
    for a in source:
        for k in total:
            total[k] += (a.get("findings") or {}).get(k, 0)
    return total


def snapshot(hours):
    refresh()
    cutoff = time.time() - hours * 3600
    sessions = [s for s in state["sessions"].values() if s["last"] >= cutoff]
    sessions.sort(key=lambda s: s["last"], reverse=True)
    board = read_board()
    lotes, used = [], set()
    for lote in board.get("lotes", []):
        if lote.get("cerrado") and lote.get("cerrado") < cutoff:
            continue
        rooms, queue, done = [], [], []
        for task in lote.get("tareas", []):
            estado = task.get("estado", "cola")
            if estado == "cola":
                queue.append(task)
                continue
            session = next((s for s in sessions if s["id"] not in used and matches(task, s)), None)
            if session:
                used.add(session["id"])
                room = room_from_session(session, task)
            else:
                room = {"id": task.get("id"), "title": task.get("titulo"), "status": estado, "phase": None,
                        "reached": [], "now": "esperando que arranque" if estado == "activa" else None,
                        "result": task.get("pr"), "agents": [], "findings": {"C": 0, "W": 0, "S": 0},
                        "branch": task.get("rama"), "repo": lote.get("repo")}
            (done if estado in ("lista", "bloqueada") else rooms).append(room)
        lotes.append({"titulo": lote.get("titulo"), "repo": lote.get("repo"), "inicio": lote.get("inicio"),
                      "rooms": rooms[:ROOMS], "queue": queue, "done": done, "extra": rooms[ROOMS:]})
    loose = [s for s in sessions if s["id"] not in used]
    active = [s for s in loose if s["status"] == "trabajando"]
    idle = [s for s in loose if s["status"] != "trabajando"]
    free_rooms = [room_from_session(s) for s in active][:ROOMS] if not lotes else []
    hallway = [{"session": s["id"], "title": s["title"] or s["branch"], "repo": s["repo"], "branch": s["branch"],
                "status": s["status"], "phase": s["phase"], "now": s["now"], "last": s["last"]}
               for s in (active[ROOMS:] if not lotes else active) + idle][:12]
    titles = {s["id"]: (s["title"] or s["branch"] or s["repo"]) for s in state["sessions"].values()}
    milestones = [dict(m, title=titles.get(m["session"])) for m in state["milestones"]
                  if m["ts"] >= cutoff and m["kind"] != "inicio"][:6]
    return {"now": time.time(), "phases": PHASES, "rooms": ROOMS, "waiting": WAITING, "lotes": lotes,
            "free_rooms": free_rooms, "hallway": hallway, "milestones": milestones}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, body, content_type):
        data = body.encode()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/api/state"):
            hours = 3.0
            match = re.search(r"h=([0-9.]+)", self.path)
            if match:
                hours = float(match.group(1))
            self.send(json.dumps(snapshot(hours), ensure_ascii=False), "application/json")
        else:
            with open(os.path.join(STATIC_DIR, "index.html")) as f:
                self.send(f.read(), "text/html; charset=utf-8")


if __name__ == "__main__":
    print(f"Tablero de pandilla en http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
