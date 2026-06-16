# WT_MULTI_IMPACT_SCORECARD_V1
# Run from project root:
#   cd C:\Users\info\Downloads\word-territory-ja-clean\word-territory-ja
#   py -3 .\backend\multi_impact_scorecard.py --games 60 --bot-level normal --max-turns 40
#
# This is a diagnostic tool. It measures whether WT has enough dense turns.
# It does not change game rules.

import os
os.environ.setdefault("WT_LANG", "ja")

import argparse
import random
import sys
from collections import Counter

sys.path.insert(0, "backend")

from engine import build_initial_state, apply_bot_move, pass_turn


def safe_bot(state):
    try:
        nxt = apply_bot_move(state)
        return nxt if nxt is not None else pass_turn(state)
    except Exception:
        try:
            return pass_turn(state)
        except Exception:
            return state


def labels(move):
    return [str(x) for x in (getattr(move, "comboLabels", None) or [])]


def total_score(state, player):
    s = getattr(state, "scores", None)
    if not s:
        return 0
    if player == "RED":
        return int(getattr(s, "redTerritory", 0) or 0) + int(getattr(s, "redWord", 0) or 0)
    return int(getattr(s, "blueTerritory", 0) or 0) + int(getattr(s, "blueWord", 0) or 0)


def run_match(i, seed, bot_level, max_turns):
    random.seed(seed)
    try:
        state = build_initial_state(bot_level=bot_level)
    except TypeError:
        state = build_initial_state(bot_level)

    safety = 0
    while not getattr(state, "winner", None) and safety < max_turns:
        state = safe_bot(state)
        safety += 1

    moves = list(getattr(state, "moveHistory", []) or [])
    tier_counts = Counter()
    capture_turns = 0
    reverse_turns = 0
    deadish_turns = 0
    word_turns = 0
    best_word = ""
    best_gain = -999
    best_labels = []

    for m in moves:
        ls = labels(m)
        word = str(getattr(m, "word", "") or "")
        move_type = str(getattr(m, "moveType", "") or "")
        gain = int(getattr(m, "territoryGained", 0) or 0)
        cap = int(getattr(m, "captureCount", 0) or 0)

        if move_type == "WORD" and word:
            word_turns += 1
            if gain <= 0 and cap <= 0 and not any(x in ls for x in ("二重の手", "三重の手", "四重の手", "橋渡し", "分断", "ENCIRCLE PRESSURE", "OPEN詰め")):
                deadish_turns += 1

        if "二重の手" in ls:
            tier_counts["double"] += 1
        if "三重の手" in ls:
            tier_counts["triple"] += 1
        if "四重の手" in ls:
            tier_counts["quad"] += 1
        if cap > 0:
            capture_turns += 1
        if "逆転の一手" in ls or "逆転" in ls:
            reverse_turns += 1
        if gain > best_gain:
            best_gain = gain
            best_word = word
            best_labels = ls

    red = total_score(state, "RED")
    blue = total_score(state, "BLUE")
    winner = "RED" if red > blue else "BLUE" if blue > red else "DRAW"

    return {
        "match": i,
        "winner": winner,
        "red": red,
        "blue": blue,
        "gap": abs(red - blue),
        "moves": len(moves),
        "word_turns": word_turns,
        "double": tier_counts["double"],
        "triple": tier_counts["triple"],
        "quad": tier_counts["quad"],
        "multi_total": tier_counts["double"] + tier_counts["triple"] + tier_counts["quad"],
        "capture_turns": capture_turns,
        "reverse_turns": reverse_turns,
        "deadish_turns": deadish_turns,
        "deadish_ratio": round(deadish_turns / word_turns, 3) if word_turns else 0,
        "best_word": best_word,
        "best_gain": best_gain if best_gain != -999 else 0,
        "best_labels": " / ".join(best_labels),
    }


def avg(rows, key):
    return round(sum(r[key] for r in rows) / len(rows), 3) if rows else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42000)
    ap.add_argument("--bot-level", default="normal", choices=["easy", "normal", "strong"])
    ap.add_argument("--max-turns", type=int, default=40)
    args = ap.parse_args()

    rows = []
    for i in range(args.games):
        row = run_match(i + 1, args.seed + i, args.bot_level, args.max_turns)
        rows.append(row)
        print(
            f"{i+1:03d} {row['winner']} gap={row['gap']} "
            f"multi={row['multi_total']} D/T/Q={row['double']}/{row['triple']}/{row['quad']} "
            f"cap={row['capture_turns']} rev={row['reverse_turns']} dead={row['deadish_ratio']} "
            f"best={row['best_word']} +{row['best_gain']} [{row['best_labels']}]"
        )

    print("\n=== MULTI-IMPACT SUMMARY ===")
    print("games:", len(rows))
    print("winners:", dict(Counter(r["winner"] for r in rows)))
    print("avg_gap:", avg(rows, "gap"))
    print("avg_multi_total:", avg(rows, "multi_total"))
    print("avg_double:", avg(rows, "double"))
    print("avg_triple:", avg(rows, "triple"))
    print("avg_quad:", avg(rows, "quad"))
    print("games_with_multi:", sum(1 for r in rows if r["multi_total"] > 0), "/", len(rows))
    print("games_with_triple_plus:", sum(1 for r in rows if r["triple"] + r["quad"] > 0), "/", len(rows))
    print("avg_capture_turns:", avg(rows, "capture_turns"))
    print("games_with_reverse:", sum(1 for r in rows if r["reverse_turns"] > 0), "/", len(rows))
    print("avg_deadish_ratio:", avg(rows, "deadish_ratio"))
    print("\nTargets for Quick 5x5 later:")
    print("- double: 1 to 3 per game")
    print("- triple: at least once every 2 to 3 games")
    print("- quad: about once every 10 games")
    print("- deadish_ratio: lower is better; watch if above 0.30")


if __name__ == "__main__":
    main()
