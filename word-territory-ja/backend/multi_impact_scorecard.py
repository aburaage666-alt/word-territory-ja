# WT_MULTI_IMPACT_SCORECARD_V4
# Run from project root:
#   cd C:\Users\info\Downloads\word-territory-ja-clean\word-territory-ja
#   py -3 .\backend\multi_impact_scorecard.py --games 60 --bot-level normal --max-turns 40
#   py -3 .\backend\multi_impact_scorecard.py --games 30 --bot-level normal --max-turns 40 --paired
#
# Diagnostic tool. It measures true gameplay peaks after Multi-Impact v4.
# It does not change game rules.

import os
os.environ.setdefault("WT_LANG", "ja")

import argparse
import random
import sys
from collections import Counter, defaultdict

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


def build_state(bot_level, start_player):
    try:
        state = build_initial_state(bot_level=bot_level)
    except TypeError:
        state = build_initial_state(bot_level)
    try:
        if start_player in ("RED", "BLUE"):
            state.currentPlayer = start_player
    except Exception:
        pass
    return state


def run_match(i, seed, bot_level, max_turns, start_player):
    random.seed(seed)
    state = build_state(bot_level, start_player)

    safety = 0
    while not getattr(state, "winner", None) and safety < max_turns:
        state = safe_bot(state)
        safety += 1

    moves = list(getattr(state, "moveHistory", []) or [])
    tier_counts = Counter()
    capture_turns = 0
    major_capture_turns = 0
    major_reverse_turns = 0
    existing_reverse_labels = 0
    bot_adjust_labels = 0
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
            has_peak = any(x in ls for x in ("二重の手", "三重の手", "四重の手", "大逆転の一手"))
            has_basic_effect = cap > 0 or gain >= 2 or any(("多重:" in x or x in ("橋渡し", "分断", "大奪取")) for x in ls)
            if not has_peak and not has_basic_effect:
                deadish_turns += 1

        if "二重の手" in ls:
            tier_counts["double"] += 1
        if "三重の手" in ls:
            tier_counts["triple"] += 1
        if "四重の手" in ls:
            tier_counts["quad"] += 1
        if cap > 0:
            capture_turns += 1
        if cap >= 3:
            major_capture_turns += 1
        if "大逆転の一手" in ls:
            major_reverse_turns += 1
        if any(x == "逆転の一手" or x == "逆転" for x in ls):
            existing_reverse_labels += 1
        if "Bot調整" in ls:
            bot_adjust_labels += 1
        if gain > best_gain:
            best_gain = gain
            best_word = word
            best_labels = ls

    red = total_score(state, "RED")
    blue = total_score(state, "BLUE")
    winner = "RED" if red > blue else "BLUE" if blue > red else "DRAW"
    first_player_won = winner == start_player

    return {
        "match": i,
        "start_player": start_player,
        "winner": winner,
        "first_player_won": bool(first_player_won),
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
        "major_capture_turns": major_capture_turns,
        "major_reverse_turns": major_reverse_turns,
        "existing_reverse_labels": existing_reverse_labels,
        "bot_adjust_labels": bot_adjust_labels,
        "deadish_turns": deadish_turns,
        "deadish_ratio": round(deadish_turns / word_turns, 3) if word_turns else 0,
        "best_word": best_word,
        "best_gain": best_gain if best_gain != -999 else 0,
        "best_labels": " / ".join(best_labels),
    }


def avg(rows, key):
    return round(sum(r[key] for r in rows) / len(rows), 3) if rows else 0


def breakdown_by_start(rows):
    out = {}
    for sp in ("RED", "BLUE"):
        sub = [r for r in rows if r["start_player"] == sp]
        if not sub:
            continue
        out[sp] = {
            "games": len(sub),
            "winners": dict(Counter(r["winner"] for r in sub)),
            "first_wins": sum(1 for r in sub if r["first_player_won"]),
            "avg_gap": avg(sub, "gap"),
        }
    return out


def print_summary(rows, title):
    print()
    print(title)
    print("games:", len(rows))
    print("winners:", dict(Counter(r["winner"] for r in rows)))
    print("start_players:", dict(Counter(r["start_player"] for r in rows)))
    print("by_start:", breakdown_by_start(rows))
    print("first_player_wins:", sum(1 for r in rows if r["first_player_won"]), "/", len(rows))
    print("avg_gap:", avg(rows, "gap"))
    print("avg_multi_total:", avg(rows, "multi_total"))
    print("avg_double:", avg(rows, "double"))
    print("avg_triple:", avg(rows, "triple"))
    print("avg_quad:", avg(rows, "quad"))
    print("games_with_multi:", sum(1 for r in rows if r["multi_total"] > 0), "/", len(rows))
    print("games_with_triple_plus:", sum(1 for r in rows if r["triple"] + r["quad"] > 0), "/", len(rows))
    print("avg_capture_turns:", avg(rows, "capture_turns"))
    print("avg_major_capture_turns:", avg(rows, "major_capture_turns"))
    print("games_with_major_reverse:", sum(1 for r in rows if r["major_reverse_turns"] > 0), "/", len(rows))
    print("avg_existing_reverse_labels:", avg(rows, "existing_reverse_labels"))
    print("avg_bot_adjust_labels:", avg(rows, "bot_adjust_labels"))
    print("avg_deadish_ratio:", avg(rows, "deadish_ratio"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42000)
    ap.add_argument("--bot-level", default="normal", choices=["easy", "normal", "strong"])
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--start-player", default="RED", choices=["RED", "BLUE"])
    ap.add_argument("--paired", action="store_true")
    args = ap.parse_args()

    rows = []
    for i in range(args.games):
        if args.paired:
            pair = [("RED", args.seed + i * 2), ("BLUE", args.seed + i * 2 + 1)]
        else:
            pair = [(args.start_player, args.seed + i)]
        for start_player, seed in pair:
            row = run_match(len(rows) + 1, seed, args.bot_level, args.max_turns, start_player)
            rows.append(row)
            print(
                f"{len(rows):03d} start={row['start_player']} {row['winner']} gap={row['gap']} "
                f"multi={row['multi_total']} D/T/Q={row['double']}/{row['triple']}/{row['quad']} "
                f"cap={row['capture_turns']} majorcap={row['major_capture_turns']} "
                f"majorrev={row['major_reverse_turns']} oldrev={row['existing_reverse_labels']} "
                f"botadj={row['bot_adjust_labels']} dead={row['deadish_ratio']} "
                f"best={row['best_word']} +{row['best_gain']} [{row['best_labels']}]"
            )

    print_summary(rows, "=== MULTI-IMPACT SUMMARY V4 ===")
    print()
    print("Targets:")
    print("- avg_multi_total: 2 to 5")
    print("- avg_double: 1 to 3")
    print("- avg_triple: 0.3 to 1.2")
    print("- avg_quad: 0.0 to 0.3")
    print("- games_with_major_reverse: 5 to 15 per 60 games")
    print("- avg_deadish_ratio: 0.05 to 0.30")
    print("- paired first_player_wins should be near 50 percent")


if __name__ == "__main__":
    main()
