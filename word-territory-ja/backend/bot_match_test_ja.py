# JP_BOT_MATCH_TEST_V1
import os
os.environ.setdefault('WT_LANG', 'ja')
# BALANCE_TEST_V18_ACTIVE3_AND_ALLCARDS
# BALANCE_TEST_V19_2PI2_BLUE_EXPANDER_BUILDER
# BALANCE_TEST_V20_V19_RECURSION_FIX
# BALANCE_TEST_V21_BORDER_LORD_UNDERDOG
# BALANCE_TEST_V23_RELEASE_V21_LOCKED
import argparse
import csv
import json
import random
from collections import Counter, defaultdict

from engine import build_initial_state, apply_demo_bot_move, apply_bot_move, pass_turn


ACTIVE3_30 = [
    "BORDER_LORD",
    "FORTIFIER",
    "COMEBACK_SPARK",
] * 10

ALL_CARDS_20 = [
    "BORDER_LORD",
    "FORTIFIER",
    "COMEBACK_SPARK",
    "CUT_SPECIALIST",
    "ENCIRCLER",
    "FRONTLINE_TACTICIAN",
    "BRIDGE_MASTER",
    "TRAP_SETTER",
    "SHORT_TACTICIAN",
    "CUT_HUNTER",
] * 2

ACTIVE_SCORING = {"BORDER_LORD", "FORTIFIER", "COMEBACK_SPARK"}
RETIRED_OR_SCORE_NEUTRAL = {
    "SHORT_TACTICIAN",
    "BRIDGE_MASTER",
    "FRONTLINE_TACTICIAN",
    "TRAP_SETTER",
    "ENCIRCLER",
    "CUT_SPECIALIST",
    "CUT_HUNTER",
}


def safe_apply_bot(state, mode="normal"):
    try:
        next_state = apply_demo_bot_move(state) if mode == "demo" else apply_bot_move(state)
        return next_state if next_state is not None else pass_turn(state)
    except Exception as e:
        print(f"[fallback] bot move failed: {type(e).__name__}: {e}")
        try:
            return pass_turn(state)
        except Exception:
            return state


def labels_of(move):
    return [str(x) for x in (getattr(move, "comboLabels", None) or [])]


def select_synergy_for_match(state, match_id, force_synergy="active3"):
    if force_synergy == "none":
        return state, getattr(state, "selectedSynergy", "") or ""

    if force_synergy == "active3":
        chosen = ACTIVE3_30[(match_id - 1) % len(ACTIVE3_30)]
    elif force_synergy == "allcards":
        chosen = ALL_CARDS_20[(match_id - 1) % len(ALL_CARDS_20)]
    elif force_synergy == "cycle":
        options = list(getattr(state, "synergyOptions", []) or [])
        if not options:
            options = list(ACTIVE_SCORING)
        chosen = options[(match_id - 1) % len(options)]
    elif force_synergy == "random":
        options = list(getattr(state, "synergyOptions", []) or [])
        if not options:
            options = list(ACTIVE_SCORING)
        chosen = random.choice(options)
    else:
        chosen = force_synergy

    state.selectedSynergy = chosen
    if hasattr(state, "synergyState"):
        state.synergyState = {}
    return state, chosen


def summarize_match(state, match_id, selected_synergy=""):
    red = getattr(state.scores, "redTerritory", 0)
    blue = getattr(state.scores, "blueTerritory", 0)
    moves = list(getattr(state, "moveHistory", []) or [])

    captures = bridges = locks = wilds = seeds = passes = 0
    capture_cell_turns = 0
    reclaim_turns = 0
    major_capture_turns = 0
    frontline_pressure_turns = 0
    encircle_pressure_turns = 0
    cut_turns = 0
    second_player_initiative = 0

    word_moves = three_letter_words = 0
    strict_synergies = 0
    combo_label_hits = 0
    synergy_labels = []
    combo_labels = []
    best_swing = -999
    best_word = ""
    best_labels = []

    for m in moves:
        word = str(getattr(m, "word", "") or "")
        move_type = str(getattr(m, "moveType", "") or "")
        territory = int(getattr(m, "territoryGained", 0) or 0)
        labels = labels_of(m)

        cap_count = int(getattr(m, "captureCount", 0) or 0)
        captures += cap_count
        if cap_count > 0:
            capture_cell_turns += 1
        locks += int(getattr(m, "fortifiedCellsGained", 0) or 0)
        bridges += 1 if any("BRIDGE" in x for x in labels) else 0

        # Strict separator.
        syn_labels = [l for l in labels if l.startswith("SYNERGY:")]
        cmb_labels = [l for l in labels if not l.startswith("SYNERGY:")]

        if syn_labels:
            strict_synergies += 1
            synergy_labels.extend(syn_labels)
        if cmb_labels:
            combo_label_hits += 1
            combo_labels.extend(cmb_labels)

        if any("RECLAIM" in x for x in labels):
            reclaim_turns += 1
        if any("MAJOR CAPTURE" in x for x in labels):
            major_capture_turns += 1
        if any("FRONTLINE PRESSURE" in x for x in labels):
            frontline_pressure_turns += 1
        if any("ENCIRCLE PRESSURE" in x for x in labels):
            encircle_pressure_turns += 1
        if any(x == "CUT" for x in labels):
            cut_turns += 1
        if any("SECOND PLAYER INITIATIVE" in x for x in labels):
            second_player_initiative += 1

        wilds += 1 if any("WILD" in x for x in labels) else 0
        seeds += 1 if move_type == "SEED" or word in ("SEED", "LAST STAND") else 0
        passes += 1 if move_type == "PASS" else 0

        if word and word not in ("SEED", "LAST STAND", "PASS"):
            word_moves += 1
            if len(word) == 3:
                three_letter_words += 1

        if territory > best_swing:
            best_swing = territory
            best_word = word
            best_labels = labels

    winner = "RED" if red > blue else "BLUE" if blue > red else "DRAW"

    return {
        "match_id": match_id,
        "selected_synergy": selected_synergy,
        "card_status": "active_scoring" if selected_synergy in ACTIVE_SCORING else "retired_or_score_neutral",
        "winner": winner,
        "red_cells": red,
        "blue_cells": blue,
        "score_gap": abs(red - blue),
        "close_le_6": 1 if abs(red - blue) <= 6 else 0,
        "turns": getattr(state, "turn", 0),
        "moves": len(moves),
        "captures": captures,
        "capture_cell_turns": capture_cell_turns,
        "reclaim_turns": reclaim_turns,
        "major_capture_turns": major_capture_turns,
        "frontline_pressure_turns": frontline_pressure_turns,
        "encircle_pressure_turns": encircle_pressure_turns,
        "cut_turns": cut_turns,
        "second_player_initiative": second_player_initiative,
        "bridges": bridges,
        "locks": locks,
        "synergies": strict_synergies,
        "synergy_labels": " / ".join(sorted(set(synergy_labels))),
        "combo_label_hits": combo_label_hits,
        "combo_labels": " / ".join(sorted(set(combo_labels))),
        "wild_uses": wilds,
        "seed_uses": seeds,
        "pass_uses": passes,
        "word_moves": word_moves,
        "three_letter_words": three_letter_words,
        "three_letter_ratio": round(three_letter_words / word_moves, 3) if word_moves else 0,
        "best_swing": best_swing if best_swing != -999 else 0,
        "best_word": best_word,
        "best_labels": " / ".join(best_labels),
        "opening": getattr(state, "openingName", ""),
        "bot_style": getattr(state, "botStyle", ""),
    }


def run_match(match_id, mode="normal", bot_level="normal", max_turns=60, seed=None, force_synergy="active3"):
    if seed is not None:
        random.seed(seed)
    state = build_initial_state(bot_level=bot_level)
    state, selected = select_synergy_for_match(state, match_id, force_synergy)
    safety = 0
    while not getattr(state, "winner", None) and safety < max_turns:
        state = safe_apply_bot(state, mode=mode)
        safety += 1
    return summarize_match(state, match_id, selected)


def avg(rows, key):
    return round(sum(r[key] for r in rows) / len(rows), 2)


def grouped_summary(rows):
    groups = defaultdict(list)
    for r in rows:
        groups[r["selected_synergy"]].append(r)

    out = []
    for card, items in sorted(groups.items()):
        out.append({
            "selected_synergy": card,
            "games": len(items),
            "wins_RED": sum(1 for r in items if r["winner"] == "RED"),
            "wins_BLUE": sum(1 for r in items if r["winner"] == "BLUE"),
            "draws": sum(1 for r in items if r["winner"] == "DRAW"),
            "avg_gap": round(sum(r["score_gap"] for r in items) / len(items), 2),
            "close_le_6": sum(r["close_le_6"] for r in items),
            "avg_synergies": round(sum(r["synergies"] for r in items) / len(items), 2),
            "avg_captures": round(sum(r["captures"] for r in items) / len(items), 2),
            "avg_reclaim": round(sum(r["reclaim_turns"] for r in items) / len(items), 2),
            "avg_three_letter_ratio": round(sum(r["three_letter_ratio"] for r in items) / len(items), 3),
        })
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", type=int, default=30)
    parser.add_argument("--mode", choices=["demo", "normal"], default="normal")
    parser.add_argument("--bot-level", choices=["normal", "strong"], default="normal")
    parser.add_argument("--max-turns", type=int, default=60)
    parser.add_argument("--seed", type=int, default=1000)
    parser.add_argument("--force-synergy", default="active3",
                        help="active3 for 30-match active-card suite, allcards for 20-card regression, cycle/random/none/exact card id.")
    parser.add_argument("--csv", default="bot_match_results_synergy_active3_30.csv")
    parser.add_argument("--json", default="bot_match_results_synergy_active3_30.json")
    parser.add_argument("--summary-csv", default="bot_match_summary_by_card_active3_30.csv")
    args = parser.parse_args()

    rows = []
    for i in range(args.games):
        row = run_match(i + 1, args.mode, args.bot_level, args.max_turns, args.seed + i, args.force_synergy)
        rows.append(row)
        print(
            f"Match {i+1}: {row['winner']} RED {row['red_cells']} - BLUE {row['blue_cells']} "
            f"gap={row['score_gap']} card={row['selected_synergy']} status={row['card_status']} "
            f"syn={row['synergies']} comboTurns={row['combo_label_hits']} best={row['best_word']} +{row['best_swing']}"
        )

    with open(args.csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    summary_rows = grouped_summary(rows)
    with open(args.summary_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
        writer.writeheader()
        writer.writerows(summary_rows)

    print("\n=== Summary ===")
    print("Winners:", dict(Counter(r["winner"] for r in rows)))
    print("Selected synergies:", dict(Counter(r["selected_synergy"] for r in rows)))
    print("Avg turns:", avg(rows, "turns"))
    print("Avg score gap:", avg(rows, "score_gap"))
    print("Close <= 6:", sum(r["close_le_6"] for r in rows), "/", len(rows))
    print("Avg captured cells:", avg(rows, "captures"))
    print("Avg capture turns:", avg(rows, "capture_cell_turns"))
    print("Avg reclaim turns:", avg(rows, "reclaim_turns"))
    print("Avg major capture turns:", avg(rows, "major_capture_turns"))
    print("Avg frontline pressure turns:", avg(rows, "frontline_pressure_turns"))
    print("Avg encircle pressure turns:", avg(rows, "encircle_pressure_turns"))
    print("Avg cut turns:", avg(rows, "cut_turns"))
    print("Avg second player initiative:", avg(rows, "second_player_initiative"))
    print("Avg bridges:", avg(rows, "bridges"))
    print("Avg locks:", avg(rows, "locks"))
    print("Avg strict synergies:", avg(rows, "synergies"))
    print("Avg combo-label turns:", avg(rows, "combo_label_hits"))
    print("Avg wild uses:", avg(rows, "wild_uses"))
    print("Avg 3-letter ratio:", round(sum(r["three_letter_ratio"] for r in rows) / len(rows), 3))
    print(f"\nSaved: {args.csv}")
    print(f"Saved: {args.json}")
    print(f"Saved: {args.summary_csv}")


if __name__ == "__main__":
    main()
