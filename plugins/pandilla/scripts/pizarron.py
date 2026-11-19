#!/usr/bin/env python3
"""Pizarrón del tablero: qué lote corre en cada repo, sus pedidos y en qué estado está cada uno.

Lo escribe el orquestador de /pandilla:lote; el tablero lo lee. Un lote por repo: uno nuevo reemplaza al anterior.

  pizarron.py lote   --repo <repo> --titulo "<título>" --tarea "ID|título" [--tarea ...]
  pizarron.py tarea  --repo <repo> --id <ID> [--estado cola|activa|lista|bloqueada] [--rama R] [--worktree P] [--pr TEXTO]
  pizarron.py cerrar --repo <repo>
  pizarron.py ver
"""
import argparse, json, os, tempfile, time

DATA_DIR = os.path.expanduser(os.environ.get("PANDILLA_DIR", "~/.claude/pandilla"))
BOARD = os.path.join(DATA_DIR, "pizarron.json")
STATES = ("cola", "activa", "lista", "bloqueada")


def load():
    try:
        with open(BOARD) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"lotes": []}


def save(board):
    os.makedirs(DATA_DIR, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=DATA_DIR, prefix=".pizarron-")
    with os.fdopen(fd, "w") as f:
        json.dump(board, f, ensure_ascii=False, indent=2)
    os.replace(tmp, BOARD)


def find(board, repo):
    return next((l for l in board["lotes"] if l["repo"] == repo), None)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    new = sub.add_parser("lote")
    new.add_argument("--repo", required=True)
    new.add_argument("--titulo", required=True)
    new.add_argument("--tarea", action="append", default=[], help='"ID|título"')
    task = sub.add_parser("tarea")
    task.add_argument("--repo", required=True)
    task.add_argument("--id", required=True)
    task.add_argument("--titulo")
    task.add_argument("--estado", choices=STATES)
    task.add_argument("--rama")
    task.add_argument("--worktree")
    task.add_argument("--pr")
    close = sub.add_parser("cerrar")
    close.add_argument("--repo", required=True)
    sub.add_parser("ver")
    args = parser.parse_args()

    board = load()
    if args.cmd == "ver":
        print(json.dumps(board, ensure_ascii=False, indent=2))
        return
    if args.cmd == "lote":
        tasks = []
        for raw in args.tarea:
            task_id, _, title = raw.partition("|")
            tasks.append({"id": task_id.strip(), "titulo": title.strip() or task_id.strip(), "estado": "cola"})
        board["lotes"] = [l for l in board["lotes"] if l["repo"] != args.repo]
        board["lotes"].append({"repo": args.repo, "titulo": args.titulo, "inicio": time.time(), "tareas": tasks})
    elif args.cmd == "tarea":
        lote = find(board, args.repo)
        if not lote:
            raise SystemExit(f"no hay lote para {args.repo}: crea uno con `pizarron.py lote`")
        item = next((t for t in lote["tareas"] if t["id"] == args.id), None)
        if not item:
            item = {"id": args.id, "titulo": args.titulo or args.id, "estado": "cola"}
            lote["tareas"].append(item)
        for key in ("titulo", "estado", "rama", "worktree", "pr"):
            value = getattr(args, key)
            if value:
                item[key] = value
        item["actualizado"] = time.time()
    elif args.cmd == "cerrar":
        lote = find(board, args.repo)
        if lote:
            lote["cerrado"] = time.time()
    save(board)


if __name__ == "__main__":
    main()
