# -*- coding: utf-8 -*-
r"""
Cardless scorecard for Word Territory JA.

Usage:
  py -3 scorecard_cardless.py bot_match_results_cardless_90.csv

This scorecard removes card-specific gates:
- synergy >0
- no dead card

It focuses on actual basic-mode play:
- RED win rate
- BLUE win rate
- word rate
- 3-letter ratio
- close game rate
- average score gap
- 4+ best-word share
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path


def num(row, *keys, default=0.0):
    for k in keys:
        if k in row and str(row[k]).strip() != "":
            try:
                return float(row[k])
            except Exception:
                pass
    return default


def txt(row, *keys, default=""):
    for k in keys:
        if k in row and str(row[k]).strip() != "":
            return str(row[k]).strip()
    return default


def pct(n, d):
    return 0.0 if not d else 100.0 * n / d


def passfail(cond):
    return "PASS" if cond else "FAIL"


def main(argv):
    if len(argv) != 2:
        print("usage: scorecard_cardless.py bot_match_results_cardless_90.csv")
        return 2

    path = Path(argv[1])
    rows = list(csv.DictReader(path.open("r", encoding="utf-8-sig", newline="")))
    if not rows:
        print("No rows.")
        return 1

    n = len(rows)
    winners = {}
    for r in rows:
        w = txt(r, "winner", "Winner", default="").upper()
        winners[w] = winners.get(w, 0) + 1

    red_pct = pct(winners.get("RED", 0), n)
    blue_pct = pct(winners.get("BLUE", 0), n)

    gaps = [abs(num(r, "score_gap", "gap", "Score Gap", default=0)) for r in rows]
    avg_gap = sum(gaps) / n
    close_rate = pct(sum(1 for g in gaps if g <= 6), n)

    word_vals = []
    three_vals = []
    four_best_count = 0
    four_best_known = 0

    for r in rows:
        if "word_ratio" in r or "word_pct" in r or "word_percent" in r:
            word_vals.append(num(r, "word_ratio", "word_pct", "word_percent", default=0))
        elif "word_turns" in r and "turns" in r:
            turns = num(r, "turns", "turn_count", default=0)
            word_turns = num(r, "word_turns", default=0)
            if turns:
                word_vals.append(word_turns / turns)
        elif "word_move_rate" in r:
            word_vals.append(num(r, "word_move_rate", default=0))

        if "three_letter_ratio" in r:
            three_vals.append(num(r, "three_letter_ratio", default=0))
        elif "3_letter_ratio" in r:
            three_vals.append(num(r, "3_letter_ratio", default=0))
        elif "three_ratio" in r:
            three_vals.append(num(r, "three_ratio", default=0))

        bw = txt(r, "best_word", "bestWord", "best_word_text", default="")
        if bw:
            four_best_known += 1
            if len(bw) >= 4:
                four_best_count += 1
        else:
            bl = num(r, "best_word_len", "bestWordLen", default=-1)
            if bl >= 0:
                four_best_known += 1
                if bl >= 4:
                    four_best_count += 1

    word_rate = 100.0 * (sum(word_vals) / len(word_vals)) if word_vals and max(word_vals) <= 1.5 else (sum(word_vals) / len(word_vals) if word_vals else 100.0)
    three_rate = 100.0 * (sum(three_vals) / len(three_vals)) if three_vals and max(three_vals) <= 1.5 else (sum(three_vals) / len(three_vals) if three_vals else 0.0)
    four_share = pct(four_best_count, four_best_known) if four_best_known else None

    gates = []
    gates.append(("RED% in 40-60", 40 <= red_pct <= 60, f"{red_pct:.0f}%"))
    gates.append(("BLUE% >= 35", blue_pct >= 35, f"{blue_pct:.0f}%"))
    gates.append(("word% >= 90", word_rate >= 90, f"{word_rate:.0f}%"))
    gates.append(("3-letter <= 70 (JP)", three_rate <= 70, f"{three_rate:.0f}%"))
    gates.append(("close >= 55", close_rate >= 55, f"{close_rate:.0f}%"))
    gates.append(("gap <= 6.0", avg_gap <= 6.0, f"{avg_gap:.2f}"))
    if four_share is not None:
        gates.append(("4+ best-word >= 55", four_share >= 55, f"{four_share:.0f}%"))

    passed = sum(1 for _, ok, _ in gates if ok)

    label = path.stem.replace("bot_match_results_", "")
    print(f"GATE                | {label}")
    print("---------------------------------------")
    for name, ok, val in gates:
        print(f"{name:<20}| {passfail(ok):<9} {val:>6}")
    print("---------------------------------------")
    print(f"SC_CARDLESS = x/{len(gates):<2} |      {passed}/{len(gates)}")
    print("---------------------------------------")
    print(f"Winners: {winners}")
    print(f"Rows: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
