#!/usr/bin/env python3
"""Word Territory balance scorecard: Intelligibility Core v1.

Reads bot_match_results_*.csv and applies 6 fixed acceptance gates.
Synergy/card activation gates are intentionally removed because hidden scoring
is no longer part of the core evaluation.

Usage:
  py -3 scorecard.py bot_match_results_*.csv
"""
import csv
import sys
import statistics
from collections import defaultdict

GATES = {
    "RED% in 40-60":       "First/second player fairness",
    "style 30-70 all":     "Every bot style stays in a playable band",
    "word% >= 90":         "Most moves are real word moves, not seed/pass",
    "3-letter <= 70 (JP)": "JP depth: avoid shallow 3-kana dominance",
    "close >= 55":         "At least 55% of games are gap<=6",
    "gap <= 6.0":          "Average score gap is not a blowout",
}

def load(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def _num(row, key, default=0):
    try:
        return float(row.get(key, default) or default)
    except Exception:
        return float(default)

def _int(row, key, default=0):
    return int(_num(row, key, default))

def score(rows):
    n = len(rows)
    if n <= 0:
        raise ValueError("empty csv")

    red_wins = sum(1 for r in rows if r.get("winner") == "RED")
    redpct = red_wins / n * 100.0

    style = defaultdict(lambda: [0, 0])
    for r in rows:
        s = r.get("bot_style") or r.get("botStyle") or "UNKNOWN"
        style[s][0] += 1
        if r.get("winner") == "RED":
            style[s][1] += 1

    style_detail = {}
    style_ok = True
    for s, (games, redwins) in style.items():
        pct = redwins / games * 100.0 if games else 0.0
        style_detail[s] = round(pct)
        if not (30 <= pct <= 70):
            style_ok = False

    word_moves = sum(_int(r, "word_moves") for r in rows)
    moves = sum(_int(r, "moves") for r in rows)
    wordpct = word_moves / moves * 100.0 if moves else 0.0

    three_ratio = statistics.mean(_num(r, "three_letter_ratio") for r in rows) * 100.0

    close = sum(_int(r, "close_le_6") for r in rows) / n * 100.0

    gaps = []
    for r in rows:
        if "score_gap" in r:
            gaps.append(abs(_num(r, "score_gap")))
        elif "gap" in r:
            gaps.append(abs(_num(r, "gap")))
    avg_gap = statistics.mean(gaps) if gaps else 999.0

    results = {
        "RED% in 40-60":       (40 <= redpct <= 60, f"{redpct:.1f}%"),
        "style 30-70 all":     (style_ok, str(style_detail)),
        "word% >= 90":         (wordpct >= 90, f"{wordpct:.1f}%"),
        "3-letter <= 70 (JP)": (three_ratio <= 70, f"{three_ratio:.1f}%"),
        "close >= 55":         (close >= 55, f"{close:.1f}%"),
        "gap <= 6.0":          (avg_gap <= 6.0, f"{avg_gap:.2f}"),
    }

    sc = sum(1 for ok, _ in results.values() if ok)
    return sc, results

def label(path):
    import os
    import re
    b = os.path.basename(path)
    b = re.sub(r"^bot_match_(results|summary)_(ja_)?", "", b)
    b = re.sub(r"\.csv$", "", b)
    return b or path

def four_plus_share(rows):
    vals = []
    for r in rows:
        w = r.get("best_word") or r.get("bestWord") or ""
        vals.append(1 if len(str(w)) >= 4 else 0)
    return sum(vals) / len(vals) * 100.0 if vals else 0.0

def main(argv):
    files = argv[1:]
    if not files:
        print("usage: scorecard.py results_*.csv")
        return 1

    all_results = {}
    all_depth = {}

    for p in files:
        rows = load(p)
        sc, res = score(rows)
        name = label(p)
        all_results[name] = (sc, res)
        all_depth[name] = four_plus_share(rows)

    gates = list(GATES.keys())
    width = max(len(g) for g in gates)
    cols = list(all_results.keys())

    print(f"{'GATE':<{width}} | " + " | ".join(f"{c:^16}" for c in cols))
    print("-" * (width + 3 + len(cols) * 19))

    for gate in gates:
        cells = []
        for c in cols:
            ok, val = all_results[c][1][gate]
            cells.append(f"{'PASS' if ok else 'FAIL'} {val:>9}")
        print(f"{gate:<{width}} | " + " | ".join(f"{x:^16}" for x in cells))

    print("-" * (width + 3 + len(cols) * 19))
    print(f"{'SC = x/6':<{width}} | " + " | ".join(f"{all_results[c][0]}/6".center(16) for c in cols))

    print("-" * (width + 3 + len(cols) * 19))
    print(f"{'(info) 4+ best-word share':<{width}} | " + " | ".join(f"{all_depth[c]:.1f}%".center(16) for c in cols))

    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
