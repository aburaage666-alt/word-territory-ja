# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import sys
from pathlib import Path


def pick(row, *keys, default=""):
    for k in keys:
        if k in row and row[k] != "":
            return row[k]
    return default


def main(argv):
    if len(argv) < 2:
        print("usage: bot_balance_gate_v4.py results.csv")
        return 2

    rows = list(csv.DictReader(Path(argv[1]).open("r", encoding="utf-8-sig", newline="")))
    if not rows:
        print("no rows")
        return 2

    n = len(rows)
    winners = {"RED": 0, "BLUE": 0, "DRAW": 0}
    gaps = []
    close6 = 0
    blow12 = 0
    blow15 = 0
    ratios = []
    best_lens = []

    for r in rows:
        w = str(pick(r, "winner", "Winner", default="DRAW")).upper()
        if "RED" in w:
            winners["RED"] += 1
        elif "BLUE" in w:
            winners["BLUE"] += 1
        else:
            winners["DRAW"] += 1

        g = abs(float(pick(r, "score_gap", "gap", default="0") or 0))
        gaps.append(g)
        if g <= 6:
            close6 += 1
        if g >= 12:
            blow12 += 1
        if g >= 15:
            blow15 += 1

        tr = pick(r, "three_letter_ratio", "3_letter_ratio", "three_ratio", default="")
        try:
            if tr != "":
                ratios.append(float(tr))
        except Exception:
            pass

        bw = str(pick(r, "best_word", "bestWord", "best", default=""))
        bw = bw.split("+")[0].strip()
        bw = "".join(ch for ch in bw if "\u3040" <= ch <= "\u309f" or ch == "ー")
        if bw:
            best_lens.append(len(bw))

    red = winners["RED"] * 100 / n
    blue = winners["BLUE"] * 100 / n
    close = close6 * 100 / n
    avg_gap = sum(gaps) / len(gaps)
    b12 = blow12 * 100 / n
    b15 = blow15 * 100 / n
    avg3 = sum(ratios) / len(ratios) if ratios else 0
    best4 = sum(1 for x in best_lens if x >= 4) * 100 / len(best_lens) if best_lens else 0
    avg_best = sum(best_lens) / len(best_lens) if best_lens else 0

    print("BOT_BALANCE_GATE_V4")
    print("rows:", n)
    print("winners:", winners)
    print("RED%:", round(red, 1))
    print("BLUE%:", round(blue, 1))
    print("close<=6%:", round(close, 1))
    print("avg_gap:", round(avg_gap, 2))
    print("blowout>=12%:", round(b12, 1))
    print("blowout>=15%:", round(b15, 1))
    print("avg_3ratio:", round(avg3, 3))
    print("best4+%:", round(best4, 1))
    print("avg_best_len:", round(avg_best, 2))

    fails = []

    if not (35 <= red <= 65):
        fails.append("RED% outside 35-65")
    if blue < 30:
        fails.append("BLUE% < 30")
    if close < 50:
        fails.append("close<=6 < 50")
    if avg_gap > 7.5:
        fails.append("avg_gap > 7.5")
    if b12 > 30:
        fails.append("blowout>=12 > 30")
    if b15 > 18:
        fails.append("blowout>=15 > 18")
    if avg3 > 0.74:
        fails.append("3-letter ratio > 0.74")
    if best4 < 45:
        fails.append("best4+ < 45")

    if fails:
        print("RESULT: FAIL")
        for f in fails:
            print(" -", f)
        return 1

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
