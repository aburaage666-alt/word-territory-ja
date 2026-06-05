
from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
from pathlib import Path

RELEASE_MARKER = "JP_V28_FULL_ENGINE_CLEAN_V18_RELEASE"
BAD_SIGNATURES = ["-14.0", "_JP_V26_BANNED_WORDS"]


def log(msg: str) -> None:
    print(msg, flush=True)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def is_contaminated(text: str) -> bool:
    return any(sig in text for sig in BAD_SIGNATURES)


def find_repo() -> Path:
    userprofile = Path(os.environ.get("USERPROFILE", str(Path.home())))
    default = userprofile / "Downloads" / "word-territory-new" / "word-territory"
    env_repo = os.environ.get("WORD_TERRITORY_REPO")
    if env_repo and (Path(env_repo) / "backend").exists():
        return Path(env_repo)
    if (default / "backend").exists():
        return default

    downloads = userprofile / "Downloads"
    candidates = []
    if downloads.exists():
        for p in downloads.rglob("word-territory"):
            if p.is_dir() and (p / "backend").exists():
                candidates.append(p)
    if candidates:
        candidates.sort(key=lambda p: (len(str(p)), str(p)))
        return candidates[0]

    raise FileNotFoundError(
        "repo not found. Set WORD_TERRITORY_REPO to your word-territory folder, "
        "or place repo at Downloads\\word-territory-new\\word-territory"
    )


def run(cmd, cwd: Path, env=None, allow_fail=False) -> int:
    log("RUN: " + " ".join(str(c) for c in cmd))
    p = subprocess.run(cmd, cwd=str(cwd), env=env)
    if p.returncode != 0 and not allow_fail:
        raise RuntimeError(f"command failed with exit code {p.returncode}: {cmd}")
    return p.returncode


def copy_tree_contents(src: Path, dst: Path) -> None:
    if not src.exists():
        raise FileNotFoundError(f"source missing: {src}")
    dst.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dst / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def summarize_csv(path: Path) -> dict:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    seed = sum(int(float(r.get("seed_uses") or 0)) for r in rows)
    passes = sum(int(float(r.get("pass_uses") or 0)) for r in rows)
    moves = sum(int(float(r.get("moves") or 0)) for r in rows)
    word_moves = sum(int(float(r.get("word_moves") or 0)) for r in rows)
    three = sum(int(float(r.get("three_letter_words") or 0)) for r in rows)
    gaps = [float(r.get("score_gap") or 0) for r in rows]
    close = sum(1 for r in rows if int(float(r.get("close_le_6") or 0)) == 1)
    winners = {"RED": 0, "BLUE": 0, "DRAW": 0}
    for r in rows:
        winners[r.get("winner", "")] = winners.get(r.get("winner", ""), 0) + 1
    return {
        "games": len(rows),
        "seed": seed,
        "pass": passes,
        "word_pct": word_moves / moves * 100 if moves else 0,
        "three_pct": three / word_moves * 100 if word_moves else 0,
        "avg_gap": sum(gaps) / len(gaps) if gaps else 0,
        "close_pct": close / len(rows) * 100 if rows else 0,
        "winners": winners,
    }


def main() -> int:
    release = Path(__file__).resolve().parent
    repo = find_repo()
    src_backend = release / "backend"
    src_frontend = release / "frontend"

    log("=== Word Territory JP v28 FULL ENGINE no-PowerShell installer ===")
    log(f"release: {release}")
    log(f"repo:    {repo}")

    source_engine = src_backend / "engine.py"
    if not source_engine.exists():
        raise FileNotFoundError(f"release engine.py missing: {source_engine}")
    # v31 release completeness: JP profile must be bundled for blank checkouts.
    for required in [
        src_backend / "language_profiles" / "__init__.py",
        src_backend / "language_profiles" / "ja.py",
    ]:
        if not required.exists():
            raise FileNotFoundError(f"release language profile missing: {required}")
    source_text = read_text(source_engine)
    log(f"source marker: {RELEASE_MARKER in source_text}")
    log(f"source contaminated: {is_contaminated(source_text)}")
    if RELEASE_MARKER not in source_text or is_contaminated(source_text):
        raise RuntimeError("release engine.py is not clean v28 FULL ENGINE")

    repo_backend = repo / "backend"
    current_engine = repo_backend / "engine.py"
    if current_engine.exists():
        current_text = read_text(current_engine)
        log(f"before copy contaminated: {is_contaminated(current_text)}")
        backup = repo_backend / "engine_BEFORE_V28_FULL_ENGINE_BACKUP.py"
        shutil.copy2(current_engine, backup)
        log(f"backup saved: {backup}")

    log("copying backend...")
    copy_tree_contents(src_backend, repo_backend)
    if src_frontend.exists():
        log("copying frontend...")
        copy_tree_contents(src_frontend, repo / "frontend")
    if (release / "scorecard.py").exists():
        shutil.copy2(release / "scorecard.py", repo / "scorecard.py")

    copied_text = read_text(repo_backend / "engine.py")
    log(f"after copy marker: {RELEASE_MARKER in copied_text}")
    log(f"after copy contaminated: {is_contaminated(copied_text)}")
    if RELEASE_MARKER not in copied_text or is_contaminated(copied_text):
        raise RuntimeError("repo engine.py is still not clean after copy")

    # remove caches
    for cache in repo_backend.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)

    env = os.environ.copy()
    env["WT_LANG"] = "ja"

    # Compile/import check.  This catches missing backend/language_profiles on a blank checkout.
    compile_files = [
        "engine.py", "dictionary.py", "models.py", "main.py",
        "spectator_seed.py", "bot_match_test_ja.py",
        "language_profiles/__init__.py", "language_profiles/ja.py",
    ]
    run([sys.executable, "-m", "py_compile", *compile_files], cwd=repo_backend, env=env)
    run([sys.executable, "-c", "import os; os.environ['WT_LANG']='ja'; import language_profiles.ja; import dictionary; import engine; print('JP language profile import OK')"], cwd=repo_backend, env=env)

    # Dictionary validation from release directory
    if (release / "validate_jp_v28_dictionary.py").exists():
        run([sys.executable, str(release / "validate_jp_v28_dictionary.py")], cwd=release, env=env)

    # Remove old result files
    for name in [
        "bot_match_results_ja_v28_full_engine.csv",
        "bot_match_results_ja_v28_full_engine.json",
        "bot_match_summary_ja_v28_full_engine.csv",
        "bot_match_results_ja_v28_full_engine_FAILED.csv",
        "bot_match_results_ja_v28_full_engine_FAILED.json",
        "bot_match_summary_ja_v28_full_engine_FAILED.csv",
    ]:
        p = repo_backend / name
        if p.exists():
            p.unlink()

    csv_name = "bot_match_results_ja_v28_full_engine.csv"
    json_name = "bot_match_results_ja_v28_full_engine.json"
    summary_name = "bot_match_summary_ja_v28_full_engine.csv"

    # Run match test
    run([
        sys.executable, "bot_match_test_ja.py",
        "--games", "90",
        "--mode", "normal",
        "--bot-level", "normal",
        "--force-synergy", "active3",
        "--csv", csv_name,
        "--json", json_name,
        "--summary-csv", summary_name,
    ], cwd=repo_backend, env=env)

    csv_path = repo_backend / csv_name
    stats = summarize_csv(csv_path)
    log("=== quick summary ===")
    log(str(stats))

    # Scorecard
    if (repo / "scorecard.py").exists():
        run([sys.executable, "scorecard.py", str(csv_path)], cwd=repo, env=env, allow_fail=True)

    # Strict validation. On failure, rename outputs to FAILED and exit 1.
    strict = release / "validate_jp_v28_results_strict.py"
    rc = 0
    if strict.exists():
        rc = run([sys.executable, str(strict), str(csv_path)], cwd=repo, env=env, allow_fail=True)

    if rc != 0:
        log("STRICT VALIDATION FAILED. Renaming outputs to *_FAILED.*")
        mapping = {
            csv_name: "bot_match_results_ja_v28_full_engine_FAILED.csv",
            json_name: "bot_match_results_ja_v28_full_engine_FAILED.json",
            summary_name: "bot_match_summary_ja_v28_full_engine_FAILED.csv",
        }
        for old, new in mapping.items():
            oldp = repo_backend / old
            if oldp.exists():
                newp = repo_backend / new
                if newp.exists():
                    newp.unlink()
                oldp.rename(newp)
        log("Upload FAILED files for diagnosis:")
        for new in mapping.values():
            log(str(repo_backend / new))
        return 1

    log("SUCCESS: v28 FULL ENGINE clean run complete.")
    log("Upload these files:")
    log(str(repo_backend / csv_name))
    log(str(repo_backend / summary_name))
    log(str(repo_backend / json_name))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        raise SystemExit(1)
