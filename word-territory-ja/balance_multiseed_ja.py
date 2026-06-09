# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path
from statistics import mean


SEEDS_DEFAULT = [20260608, 20260609, 20260610]
SIZES_DEFAULT = [5, 7]


def run(cmd: list[str], cwd: Path, timeout: int = 420) -> tuple[int, str]:
    print("$ " + " ".join(cmd))
    p = subprocess.run(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    print(p.stdout)
    return p.returncode, p.stdout


def read_help(project: Path) -> str:
    code, out = run([sys.executable, "backend/bot_match_test_ja.py", "--help"], project, timeout=120)
    if code != 0:
        raise SystemExit("bot_match_test_ja.py --help に失敗しました")
    return out


def detect_size_arg(help_text: str) -> str | None:
    for flag in ["--board-size", "--size", "--grid-size", "--board"]:
        if flag in help_text:
            return flag
    return None


def detect_blue_komi(help_text: str) -> bool:
    return "--blue-komi" in help_text


def safe_float(x, default=0.0) -> float:
    try:
        if x is None or x == "":
            return default
        return float(x)
    except Exception:
        return default


def safe_int(x, default=0) -> int:
    try:
        if x is None or x == "":
            return default
        return int(float(x))
    except Exception:
        return default


def row_winner(row: dict) -> str:
    for k in ["winner", "Winner", "winning_player", "winningPlayer"]:
        v = row.get(k)
        if v:
            return str(v).upper()
    return ""


def row_gap(row: dict) -> float:
    for k in ["score_gap", "scoreGap", "gap", "final_gap"]:
        if k in row:
            return abs(safe_float(row.get(k)))

    red = None
    blue = None
    for k in ["red_score", "redScore", "RED", "score_red"]:
        if k in row:
            red = safe_float(row.get(k))
            break
    for k in ["blue_score", "blueScore", "BLUE", "score_blue"]:
        if k in row:
            blue = safe_float(row.get(k))
            break

    if red is not None and blue is not None:
        return abs(red - blue)

    return 0.0


def row_three_ratio(row: dict) -> float | None:
    for k in ["three_letter_ratio", "threeLetterRatio", "3_letter_ratio", "avg_3_letter_ratio"]:
        if k in row and row.get(k) not in ("", None):
            return safe_float(row.get(k))
    return None


def row_best_word_len(row: dict) -> int | None:
    for k in ["best_word_len", "bestWordLen", "best_len"]:
        if k in row and row.get(k) not in ("", None):
            return safe_int(row.get(k))

    for k in ["best_word", "bestWord", "best"]:
        v = row.get(k)
        if v:
            s = str(v).strip()
            s = re.sub(r"\s+\+\d+.*$", "", s)
            s = re.sub(r"[^ぁ-んァ-ンー一-龥A-Za-z]", "", s)
            if s:
                return len(s)

    return None


def summarize_csv(path: Path, label: str) -> dict:
    rows = list(csv.DictReader(path.open("r", encoding="utf-8-sig", newline="")))

    if not rows:
        raise SystemExit("CSVが空です: " + str(path))

    winners = {"RED": 0, "BLUE": 0, "DRAW": 0, "OTHER": 0}
    gaps = []
    close = 0
    ratios = []
    best_lens = []

    for row in rows:
        w = row_winner(row)
        if w in winners:
            winners[w] += 1
        elif "RED" in w:
            winners["RED"] += 1
        elif "BLUE" in w:
            winners["BLUE"] += 1
        elif "DRAW" in w or "TIE" in w:
            winners["DRAW"] += 1
        else:
            winners["OTHER"] += 1

        g = row_gap(row)
        gaps.append(g)
        if g <= 6:
            close += 1

        r = row_three_ratio(row)
        if r is not None:
            ratios.append(r)

        bl = row_best_word_len(row)
        if bl is not None:
            best_lens.append(bl)

    n = len(rows)
    best4 = sum(1 for x in best_lens if x >= 4)

    return {
        "label": label,
        "rows": n,
        "red_pct": round(winners["RED"] * 100 / n),
        "blue_pct": round(winners["BLUE"] * 100 / n),
        "draw_pct": round(winners["DRAW"] * 100 / n),
        "close_pct": round(close * 100 / n),
        "avg_gap": round(mean(gaps), 2) if gaps else 0.0,
        "avg_3_letter_ratio": round(mean(ratios), 3) if ratios else None,
        "best4_pct": round(best4 * 100 / len(best_lens)) if best_lens else None,
        "winners": winners,
    }


def pass_fail(summary: dict) -> tuple[int, list[str]]:
    checks = []
    checks.append(("RED 40-60", 40 <= summary["red_pct"] <= 60))
    checks.append(("BLUE >=35", summary["blue_pct"] >= 35))
    checks.append(("close >=45", summary["close_pct"] >= 45))
    checks.append(("gap <=9", summary["avg_gap"] <= 9.0))

    if summary["avg_3_letter_ratio"] is not None:
        checks.append(("3文字率 <=0.72", summary["avg_3_letter_ratio"] <= 0.72))

    if summary["best4_pct"] is not None:
        checks.append(("4文字以上 >=55", summary["best4_pct"] >= 55))

    passed = sum(1 for _, ok in checks if ok)
    lines = [f"{name}: {'PASS' if ok else 'FAIL'}" for name, ok in checks]
    return passed, lines


def run_suite(project: Path, size: int, seed: int, games: int, size_flag: str | None, has_komi: bool) -> dict:
    label = f"size{size}_seed{seed}_games{games}"
    csv_name = f"balance_multiseed_{label}.csv"
    json_name = f"balance_multiseed_{label}.json"
    summary_name = f"balance_multiseed_{label}_summary.csv"

    cmd = [
        sys.executable,
        "backend/bot_match_test_ja.py",
        "--force-synergy", "none",
        "--games", str(games),
        "--bot-level", "normal",
        "--seed", str(seed),
        "--csv", csv_name,
        "--json", json_name,
        "--summary-csv", summary_name,
    ]

    if has_komi:
        cmd.extend(["--blue-komi", "4"])

    if size_flag:
        cmd.extend([size_flag, str(size)])

    code, out = run(cmd, project, timeout=420)
    if code != 0:
        raise SystemExit("balance suite failed: " + label)

    csv_path = project / csv_name
    if not csv_path.exists():
        raise SystemExit("CSVが生成されませんでした: " + csv_name)

    summary = summarize_csv(csv_path, label)
    summary["size"] = size
    summary["seed"] = seed
    summary["games"] = games
    summary["size_flag"] = size_flag or "未対応: 現行CLIの既定盤面"
    return summary


def write_report(project: Path, summaries: list[dict], size_flag: str | None) -> Path:
    path = project / "balance_multiseed_ja_report.txt"

    lines = []
    lines.append("Word Territory 日本語版 複数seedバランステスト")
    lines.append("")
    lines.append("盤面サイズ指定: " + (size_flag if size_flag else "bot_match_test_ja.py側にサイズ指定CLIが未検出"))
    lines.append("")

    total_pass = 0
    total_checks = 0

    for s in summaries:
        passed, check_lines = pass_fail(s)
        total_pass += passed
        total_checks += len(check_lines)

        lines.append("---- " + s["label"])
        lines.append(f"size={s['size']} seed={s['seed']} rows={s['rows']}")
        lines.append(f"RED={s['red_pct']}% BLUE={s['blue_pct']}% DRAW={s['draw_pct']}% close={s['close_pct']}% gap={s['avg_gap']}")
        lines.append(f"3文字率={s['avg_3_letter_ratio']} 4文字以上={s['best4_pct']}")
        for cl in check_lines:
            lines.append("  " + cl)
        lines.append("")

    lines.append("総合:")
    lines.append(f"PASS {total_pass}/{total_checks}")

    if size_flag is None:
        lines.append("")
        lines.append("注意:")
        lines.append("現行 bot_match_test_ja.py に 5x5/7x7 を直接指定するCLI引数が見つかりませんでした。")
        lines.append("この場合、テストは現行CLIの既定盤面で実行されます。")
        lines.append("次の改善で --board-size を bot_match_test_ja.py に追加してください。")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def cleanup_generated(project: Path) -> None:
    for pat in [
        "balance_multiseed_size*_seed*_games*.csv",
        "balance_multiseed_size*_seed*_games*.json",
        "balance_multiseed_size*_seed*_games*_summary.csv",
        "balance_multiseed_ja_report.txt",
    ]:
        for p in project.glob(pat):
            try:
                p.unlink()
            except Exception:
                pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=18)
    parser.add_argument("--seeds", default=",".join(str(x) for x in SEEDS_DEFAULT))
    parser.add_argument("--sizes", default=",".join(str(x) for x in SIZES_DEFAULT))
    parser.add_argument("--keep-report", action="store_true")
    args = parser.parse_args()

    project = Path.cwd()
    help_text = read_help(project)
    size_flag = detect_size_arg(help_text)
    # WT_JA_REQUIRE_REAL_BOARD_SIZE_V1
    if size_flag is None:
        raise SystemExit("bot_match_test_ja.py に --board-size が無いため、5x5/7x7別テストを実行できません。先にboard-size CLIを追加してください。")
    has_komi = detect_blue_komi(help_text)

    seeds = [int(x.strip()) for x in args.seeds.split(",") if x.strip()]
    sizes = [int(x.strip()) for x in args.sizes.split(",") if x.strip()]

    print("検出: board size flag =", size_flag)
    print("検出: blue komi =", has_komi)
    print("seeds =", seeds)
    print("sizes =", sizes)
    print("games =", args.games)

    summaries = []

    for size in sizes:
        for seed in seeds:
            summaries.append(run_suite(project, size, seed, args.games, size_flag, has_komi))

    report = write_report(project, summaries, size_flag)

    print("")
    print("REPORT:")
    print(report.read_text(encoding="utf-8"))

    if not args.keep_report:
        cleanup_generated(project)

    print("DONE balance_multiseed_ja")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
