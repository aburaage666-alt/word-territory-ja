# -*- coding: utf-8 -*-
"""
Word Territory 日本語版 健全性チェック v1
Read-only checker. Run from either:
  - repository git root, or
  - the nested word-territory-ja folder.

It checks:
- expected files exist
- forbidden dictionary words are absent
- frontend index.js has no obvious English label residue
- no node_modules/.next are staged accidentally by presence check
- Next.js 5x5 risk patterns / threat safety patterns
- optional backend compile/import and frontend build commands
"""
from __future__ import annotations
import argparse, os, re, subprocess, sys
from pathlib import Path

FORBIDDEN_WORDS = {"おこ", "こいえ"}
ENGLISH_LABELS = [
    "MAJOR CAPTURE", "BEACHHEAD", "FRONTLINE PUSH", "Territory Swing",
    "Capture threat", "Fortified ground", "Tap a green square first.",
    "Move failed", "Seed failed", "Pass failed", "Current Word", "Word Score",
]
RISK_7_FIXED = [
    "7 * 7", "viewBox=\"0 0 7 7\"", "r < 7", "col < 7", "c < 7",
]

def find_root(start: Path) -> Path:
    p = start.resolve()
    candidates = [p, p / "word-territory-ja"]
    for c in candidates:
        if (c / "frontend" / "pages" / "index.js").exists() and (c / "backend").exists():
            return c
    for parent in [p, *p.parents]:
        if (parent / "frontend" / "pages" / "index.js").exists() and (parent / "backend").exists():
            return parent
        nested = parent / "word-territory-ja"
        if (nested / "frontend" / "pages" / "index.js").exists() and (nested / "backend").exists():
            return nested
    raise SystemExit("ERROR: frontend/pages/index.js と backend が見つかりません。リポジトリ本体で実行してください。")

def run(cmd, cwd):
    print(f"\n$ {' '.join(cmd)}")
    try:
        r = subprocess.run(cmd, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
        print(r.stdout)
        return r.returncode == 0
    except Exception as e:
        print(f"ERROR running command: {e}")
        return False

def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true", help="frontendで npm.cmd run build まで実行")
    ap.add_argument("--backend", action="store_true", help="backend compile/import確認まで実行")
    args = ap.parse_args()

    root = find_root(Path.cwd())
    print(f"ROOT: {root}")
    ok = True

    idx = root / "frontend" / "pages" / "index.js"
    s = read(idx)
    print("\n[1] expected files")
    for rel in ["frontend/pages/index.js", "frontend/package.json", "backend/main.py", "backend/engine.py"]:
        exists = (root / rel).exists()
        print(("OK  " if exists else "NG  ") + rel)
        ok = ok and exists

    print("\n[2] dictionary forbidden words")
    dict_paths = [root/"backend"/"dictionaries"/"ja_words.txt", root/"backend"/"dictionaries"/"ja_words_ui.txt", root/"backend"/"ja_words.txt", root/"backend"/"ja_words_ui.txt"]
    for dp in dict_paths:
        if not dp.exists():
            print(f"SKIP missing {dp.relative_to(root)}")
            continue
        words = {line.strip() for line in read(dp).splitlines() if line.strip()}
        bad = sorted(words & FORBIDDEN_WORDS)
        if bad:
            print(f"NG  {dp.relative_to(root)} contains {bad}"); ok = False
        else:
            print(f"OK  {dp.relative_to(root)}")

    print("\n[3] English label residue")
    found = [x for x in ENGLISH_LABELS if x in s]
    if found:
        print("WARN English-like labels remain:", found)
    else:
        print("OK  no target English labels found")

    print("\n[4] 5x5 safety risk patterns")
    risks = [x for x in RISK_7_FIXED if x in s]
    if risks:
        print("WARN possible 7x7 fixed patterns:", risks)
        print("     5x5が実機で動けば致命傷ではありませんが、次のUI整理でboardSize化推奨。")
    else:
        print("OK  no obvious 7x7 hard-code patterns")

    print("\n[5] threat safety")
    if "Array.isArray" in s and "threat" in s.lower():
        print("OK/WARN Array.isArray appears with threat-related code; manual check still recommended")
    elif "getThreat" in s or "threats" in s:
        print("WARN threat code exists but Array.isArray guard not obvious")
    else:
        print("SKIP no threat code detected")

    print("\n[6] generated folders")
    for rel in ["frontend/.next", "frontend/node_modules"]:
        p = root / rel
        print(("WARN exists " if p.exists() else "OK absent ") + rel)

    if args.backend:
        print("\n[7] backend compile/import")
        ok = run([sys.executable, "-m", "compileall", "backend"], root) and ok
        ok = run([sys.executable, "-c", "from main import app; print('backend import OK')"], root / "backend") and ok

    if args.build:
        print("\n[8] frontend build")
        npm = "npm.cmd" if os.name == "nt" else "npm"
        ok = run([npm, "install"], root / "frontend") and ok
        ok = run([npm, "run", "build"], root / "frontend") and ok

    print("\nRESULT:", "PASS (with possible WARNs)" if ok else "FAIL")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
