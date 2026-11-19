#!/usr/bin/env python3
"""Limpia los worktrees que ya cumplieron: su PR está mergeado o cerrado (o, en repos sin PR, su rama ya está en la
base), no tienen cambios ni commits que solo existan ahí, nadie está corriendo adentro y nadie los tocó hace rato.

Solo borra la carpeta del worktree (`git worktree remove`, sin --force): la rama y sus commits quedan en el repo.
Lo que no cumple todo queda en el informe con su motivo, para que lo decida una persona.

  limpiar_worktrees.py [--repo RUTA ...] [--base main] [--horas 1] [--aplicar] [--json]

Sin --repo revisa cada repo de ~/Documents/GitHub que tenga worktrees. Sin --aplicar no borra nada.
"""
import argparse, glob, json, os, subprocess, time

MERGED_STATES = ("MERGED", "CLOSED")


def run(args, cwd=None):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else None


def worktrees(repo):
    out = run(["git", "-C", repo, "worktree", "list", "--porcelain"]) or ""
    items, current = [], None
    for line in out.splitlines():
        if line.startswith("worktree "):
            current = {"path": line[9:], "branch": None, "head": None}
            items.append(current)
        elif line.startswith("HEAD ") and current:
            current["head"] = line[5:]
        elif line.startswith("branch ") and current:
            current["branch"] = line[7:].replace("refs/heads/", "")
    return items[1:]


def pull_requests(repo):
    out = run(["gh", "pr", "list", "--state", "all", "--limit", "500",
               "--json", "number,state,headRefName,headRefOid"], cwd=repo)
    if out is None:
        return None
    by_branch = {}
    for pr in json.loads(out):
        by_branch.setdefault(pr["headRefName"], []).append(pr)
    return by_branch


def busy_paths():
    out = run(["lsof", "-a", "-d", "cwd", "-Fn"]) or ""
    return {line[1:] for line in out.splitlines() if line.startswith("n")}


def last_touch(path):
    candidates = [path, os.path.join(path, ".git")]
    gitdir = run(["git", "-C", path, "rev-parse", "--absolute-git-dir"])
    if gitdir:
        candidates += [os.path.join(gitdir, "index"), os.path.join(gitdir, "HEAD"), os.path.join(gitdir, "logs", "HEAD")]
    times = [os.path.getmtime(c) for c in candidates if os.path.exists(c)]
    return max(times) if times else 0


def size_gb(path):
    out = run(["du", "-sk", path])
    return round(int(out.split()[0]) / 1024 / 1024, 1) if out else None


def is_ancestor(repo, commit, of):
    return subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", commit, of],
                          capture_output=True).returncode == 0


def review(repo, base, max_idle_hours, busy):
    prs = pull_requests(repo)
    rows = []
    for wt in worktrees(repo):
        path, branch, head = wt["path"], wt["branch"], wt["head"]
        row = {"repo": os.path.basename(repo), "path": path, "branch": branch or "(sin rama)", "pr": None, "verdict": "revisar"}
        if not os.path.isdir(path):
            row.update(verdict="huérfano", reason="la carpeta ya no existe (git worktree prune lo limpia)")
            rows.append(row)
            continue
        dirty = run(["git", "-C", path, "status", "--porcelain"]) or ""
        idle_h = (time.time() - last_touch(path)) / 3600
        row["idle_h"] = round(idle_h, 1)
        candidates = (prs or {}).get(branch or "", [])
        closed = [p for p in candidates if p["state"] in MERGED_STATES]
        open_prs = [p for p in candidates if p["state"] == "OPEN"]
        if candidates:
            row["pr"] = ", ".join(f"#{p['number']} {p['state'].lower()}" for p in candidates)
        merged_locally = bool(base and head and run(["git", "-C", repo, "rev-parse", "--verify", base])
                              and is_ancestor(repo, head, base))
        covered = any(head and (head == p["headRefOid"] or is_ancestor(repo, head, p["headRefOid"])) for p in closed)
        reasons = []
        if open_prs:
            reasons.append("PR abierto")
        elif not closed and not merged_locally:
            reasons.append("sin PR cerrado ni rama en la base" if prs is not None else "sin PR (no se pudo consultar GitHub) y rama fuera de la base")
        if dirty:
            reasons.append(f"cambios sin guardar ({len(dirty.splitlines())} archivos)")
        if closed and not covered and not merged_locally:
            reasons.append("tiene commits que no están en el PR")
        if any(p == path or p.startswith(path + os.sep) for p in busy):
            reasons.append("hay procesos corriendo adentro")
        if idle_h < max_idle_hours:
            reasons.append(f"se tocó hace {idle_h:.1f} h")
        if reasons:
            row["reason"] = "; ".join(reasons)
        else:
            row["verdict"] = "borrar"
            row["reason"] = ("PR " + ", ".join(f"#{p['number']}" for p in closed) + " cerrado") if closed else f"rama ya en {base}"
        rows.append(row)
    return rows


def discover():
    repos = []
    for git_dir in glob.glob(os.path.expanduser("~/Documents/GitHub/*/.git")):
        repo = os.path.dirname(git_dir)
        if os.path.isdir(git_dir) and len(worktrees(repo)) > 0:
            repos.append(repo)
    return sorted(repos)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", action="append")
    parser.add_argument("--base", help="rama base para repos sin PR (por defecto: la del remoto, o main)")
    parser.add_argument("--horas", type=float, default=1.0, help="horas sin tocar antes de poder borrar")
    parser.add_argument("--aplicar", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.aplicar and not args.json:
        print(time.strftime("== %Y-%m-%d %H:%M ==="))
    busy = busy_paths()
    rows = []
    for repo in args.repo or discover():
        base = args.base
        if not base:
            remote_head = run(["git", "-C", repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD"])
            base = remote_head.split("/", 1)[1] if remote_head else "main"
        rows += review(repo, base, args.horas, busy)

    freed = 0.0
    for row in rows:
        if row["verdict"] != "borrar":
            continue
        row["gb"] = size_gb(row["path"])
        if not args.aplicar:
            continue
        repo = next(r for r in (args.repo or discover()) if os.path.basename(r) == row["repo"])
        result = subprocess.run(["git", "-C", repo, "worktree", "remove", row["path"]], capture_output=True, text=True)
        if result.returncode == 0:
            row["verdict"] = "borrado"
            freed += row["gb"] or 0
        else:
            row["verdict"] = "revisar"
            row["reason"] = "git worktree remove falló: " + result.stderr.strip().splitlines()[-1]
    if args.aplicar:
        for repo in args.repo or discover():
            run(["git", "-C", repo, "worktree", "prune"])

    if args.json:
        print(json.dumps({"rows": rows, "freed_gb": round(freed, 1)}, ensure_ascii=False, indent=2))
        return
    order = {"borrado": 0, "borrar": 1, "huérfano": 2, "revisar": 3}
    for row in sorted(rows, key=lambda r: (order[r["verdict"]], r["repo"], r["branch"])):
        size = f" · {row['gb']} GB" if row.get("gb") else ""
        print(f"[{row['verdict']}] {row['repo']} · {row['branch']}{size} — {row.get('reason', '')}")
    count = sum(1 for r in rows if r["verdict"] in ("borrar", "borrado"))
    total = sum(r.get("gb") or 0 for r in rows if r["verdict"] in ("borrar", "borrado"))
    verb = "Borrados" if args.aplicar else "Se pueden borrar"
    print(f"\n{verb}: {count} worktrees, {total:.1f} GB. Por revisar: {sum(1 for r in rows if r['verdict'] == 'revisar')}.")


if __name__ == "__main__":
    main()
