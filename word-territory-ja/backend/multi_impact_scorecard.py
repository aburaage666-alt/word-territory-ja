# WT_MULTI_IMPACT_SCORECARD_V5_SECOND_KOMI
# Run from project root:
#   cd C:\Users\info\Downloads\word-territory-ja-clean\word-territory-ja
#   py -3 .\backend\multi_impact_scorecard.py --games 60 --bot-level normal --max-turns 40
#   py -3 .\backend\multi_impact_scorecard.py --games 30 --bot-level normal --max-turns 40 --paired
#   py -3 .\backend\multi_impact_scorecard.py --games 30 --bot-level normal --max-turns 40 --paired --sweep-second-komi 0,2,4,6,8,10,12
#
# Diagnostic tool. It measures true gameplay peaks and virtual second-player komi.
# It does not change game rules.

import os
os.environ.setdefault("WT_LANG", "ja")

import argparse
import random
import sys
from collections import Counter

sys.path.insert(0, "backend")

from engine import build_initial_state, apply_bot_move, pass_turn


def other_player(player):
    return "BLUE" if player == "RED" else "RED"


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


def winner_from_scores(red, blue):
    if red > blue:
        return "RED"
    if blue > red:
        return "BLUE"
    return "DRAW"


def adjusted_scores(row, second_komi):
    red = int(row["red"])
    blue = int(row["blue"])
    second = other_player(row["start_player"])
    if second == "RED":
        red += second_komi
    else:
        blue += second_komi
    return red, blue


def adjusted_winner(row, second_komi):
    red, blue = adjusted_scores(row, second_komi)
    return winner_from_scores(red, blue)


def adjusted_first_player_won(row, second_komi):
    w = adjusted_winner(row, second_komi)
    return bool(w == row["start_player"])


def adjusted_gap(row, second_komi):
    red, blue = adjusted_scores(row, second_komi)
    return abs(red - blue)


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
    winner = winner_from_scores(red, blue)
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


def avg_adjusted_gap(rows, second_komi):
    return round(sum(adjusted_gap(r, second_komi) for r in rows) / len(rows), 3) if rows else 0


def breakdown_by_start(rows, second_komi=0):
    out = {}
    for sp in ("RED", "BLUE"):
        sub = [r for r in rows if r["start_player"] == sp]
        if not sub:
            continue
        out[sp] = {
            "games": len(sub),
            "raw_winners": dict(Counter(r["winner"] for r in sub)),
            "adj_winners": dict(Counter(adjusted_winner(r, second_komi) for r in sub)),
            "raw_first_wins": sum(1 for r in sub if r["first_player_won"]),
            "adj_first_wins": sum(1 for r in sub if adjusted_first_player_won(r, second_komi)),
            "raw_avg_gap": avg(sub, "gap"),
            "adj_avg_gap": avg_adjusted_gap(sub, second_komi),
        }
    return out


def print_summary(rows, title, second_komi):
    print()
    print(title)
    print("games:", len(rows))
    print("second_komi:", second_komi)
    print("raw_winners:", dict(Counter(r["winner"] for r in rows)))
    print("adjusted_winners:", dict(Counter(adjusted_winner(r, second_komi) for r in rows)))
    print("start_players:", dict(Counter(r["start_player"] for r in rows)))
    print("by_start:", breakdown_by_start(rows, second_komi))
    print("raw_first_player_wins:", sum(1 for r in rows if r["first_player_won"]), "/", len(rows))
    print("adjusted_first_player_wins:", sum(1 for r in rows if adjusted_first_player_won(r, second_komi)), "/", len(rows))
    print("raw_avg_gap:", avg(rows, "gap"))
    print("adjusted_avg_gap:", avg_adjusted_gap(rows, second_komi))
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


def parse_komi_list(text):
    vals = []
    for raw in str(text or "").split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            vals.append(int(raw))
        except ValueError:
            raise SystemExit("invalid komi value: " + raw)
    return vals


def print_komi_sweep(rows, komi_values):
    if not komi_values:
        return
    print()
    print("=== SECOND-KOMI SWEEP ===")
    print("komi, adjusted_winners, adjusted_first_player_wins, adjusted_avg_gap")
    for k in komi_values:
        winners = dict(Counter(adjusted_winner(r, k) for r in rows))
        first = sum(1 for r in rows if adjusted_first_player_won(r, k))
        gap = avg_adjusted_gap(rows, k)
        print(f"{k}: winners={winners} first_wins={first}/{len(rows)} avg_gap={gap}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42000)
    ap.add_argument("--bot-level", default="normal", choices=["easy", "normal", "strong"])
    ap.add_argument("--max-turns", type=int, default=40)
    ap.add_argument("--start-player", default="RED", choices=["RED", "BLUE"])
    ap.add_argument("--paired", action="store_true")
    ap.add_argument("--second-komi", type=int, default=0)
    ap.add_argument("--sweep-second-komi", default="")
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
            adj_w = adjusted_winner(row, args.second_komi)
            print(
                f"{len(rows):03d} start={row['start_player']} raw={row['winner']} adj={adj_w} "
                f"rawgap={row['gap']} adjgap={adjusted_gap(row, args.second_komi)} "
                f"multi={row['multi_total']} D/T/Q={row['double']}/{row['triple']}/{row['quad']} "
                f"cap={row['capture_turns']} majorcap={row['major_capture_turns']} "
                f"majorrev={row['major_reverse_turns']} oldrev={row['existing_reverse_labels']} "
                f"botadj={row['bot_adjust_labels']} dead={row['deadish_ratio']} "
                f"best={row['best_word']} +{row['best_gain']} [{row['best_labels']}]"
            )

    print_summary(rows, "=== MULTI-IMPACT SUMMARY V5 SECOND-KOMI ===", args.second_komi)
    print_komi_sweep(rows, parse_komi_list(args.sweep_second_komi))
    print()
    print("Targets:")
    print("- paired adjusted_first_player_wins should move toward 50 percent")
    print("- choose the smallest second_komi that avoids clear first-player dominance")
    print("- after choosing komi, implement it in actual scoring only if gameplay still feels fair")
    print("- avg_quad 0.0 to 0.3 remains acceptable")


if __name__ == "__main__":
    main()
