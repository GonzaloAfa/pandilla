#!/usr/bin/env python3
"""Tablero local de cuadrilla. Lee events.jsonl (lo escribe hook.py) y sirve la vista en http://localhost:7788.

Solo escucha en 127.0.0.1. CUADRILLA_DIR cambia la carpeta de eventos y CUADRILLA_PUERTO el puerto."""
import json, os, subprocess, time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

STATIC_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.expanduser(os.environ.get("CUADRILLA_DIR", "~/.claude/cuadrilla"))
EVENTS = os.path.join(DATA_DIR, "events.jsonl")
PORT = int(os.environ.get("CUADRILLA_PUERTO", "7788"))

state = {"offset": 0, "inode": None, "sessions": {}, "feed": deque(maxlen=120)}
branch_cache = {}


def branch_of(cwd):
    if not cwd:
        return None
    if cwd not in branch_cache:
        try:
            branch_cache[cwd] = subprocess.run(["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, timeout=2).stdout.strip() or None
        except Exception:
            branch_cache[cwd] = None
    return branch_cache[cwd]


def session_for(event):
    sid = event.get("session") or "?"
    sessions = state["sessions"]
    if sid not in sessions:
        cwd = event.get("cwd") or ""
        sessions[sid] = {
            "id": sid, "cwd": cwd, "label": os.path.basename(cwd.rstrip("/")) or cwd,
            "branch": branch_of(cwd), "first": event["ts"], "last": event["ts"], "status": "trabajando",
            "activity": None, "tools": 0, "prompt": None, "agents": {}, "pending": [],
        }
    return sessions[sid]


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
            "start": event["ts"], "end": None, "status": "trabajando", "activity": "arrancando",
            "tools": 0, "tokens": None, "findings": None, "verdict": None, "errors": 0,
        }
        return
    if kind == "SubagentStop" and agent:
        agent.update(end=event["ts"], status="terminó", activity=event.get("last_message"),
                     tokens=event.get("tokens"), findings=event.get("findings"), verdict=event.get("verdict"),
                     headline=event.get("headline"))
        return

    target = agent or s
    if kind == "PreToolUse":
        target["tools"] += 1
        target["activity"] = f'{event.get("tool")}: {event.get("summary") or ""}'
        target["status"] = "trabajando"
        if not agent and event.get("tool") == "Agent":
            s["pending"].append({"type": event.get("subagent_type"), "description": event.get("agent_description")})
    elif kind == "PostToolUseFailure":
        target["errors"] = target.get("errors", 0) + 1
    elif kind == "UserPromptSubmit":
        if not is_system_prompt(event.get("prompt")):
            s["prompt"] = event.get("prompt")
        s["status"] = "trabajando"
    elif kind == "Stop" and not agent:
        s["status"], s["activity"] = "esperando", event.get("last_message")
    elif kind == "SessionEnd":
        s["status"] = "cerrada"
    elif kind == "SessionStart":
        s["status"] = "esperando"


def is_system_prompt(prompt):
    return (prompt or "").lstrip().startswith(("<task-notification", "<system", "[SYSTEM", "<command-", "Delegated task", "Act as the implementation"))


def refresh():
    if not os.path.exists(EVENTS):
        return
    inode = os.stat(EVENTS).st_ino
    if inode != state["inode"]:
        state.update(inode=inode, offset=0)
    with open(EVENTS) as f:
        f.seek(state["offset"])
        for line in f:
            if not line.endswith("\n"):
                break
            state["offset"] += len(line.encode())
            try:
                event = json.loads(line)
            except Exception:
                continue
            apply(event)
            if event.get("event") == "UserPromptSubmit" and is_system_prompt(event.get("prompt")):
                continue
            if event.get("event") in ("PreToolUse", "SubagentStart", "SubagentStop", "UserPromptSubmit", "Stop", "PostToolUseFailure"):
                state["feed"].appendleft({k: event.get(k) for k in ("ts", "event", "session", "agent_type", "tool", "summary", "prompt", "verdict", "headline")})


def snapshot(hours):
    refresh()
    cutoff = time.time() - hours * 3600
    sessions = []
    for s in state["sessions"].values():
        if s["last"] < cutoff:
            continue
        item = {k: v for k, v in s.items() if k not in ("agents", "pending")}
        item["agents"] = sorted(s["agents"].values(), key=lambda a: a["start"])
        sessions.append(item)
    sessions.sort(key=lambda s: s["last"], reverse=True)
    labels = {s["id"]: s["label"] for s in state["sessions"].values()}
    feed = [dict(e, label=labels.get(e["session"])) for e in state["feed"] if e["ts"] >= cutoff][:80]
    return {"now": time.time(), "sessions": sessions, "feed": feed}


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
            if "h=" in self.path:
                try:
                    hours = float(self.path.split("h=")[1].split("&")[0])
                except ValueError:
                    pass
            self.send(json.dumps(snapshot(hours), ensure_ascii=False), "application/json")
        else:
            self.send(open(os.path.join(STATIC_DIR, "index.html")).read(), "text/html; charset=utf-8")


if __name__ == "__main__":
    print(f"Tablero de cuadrilla en http://localhost:{PORT}")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
