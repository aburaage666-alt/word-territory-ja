# measure_longword_market.py - active market long-word diagnostic.
import os
import sys
from pathlib import Path

os.environ.setdefault("WT_LANG", "ja")
BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

import engine

MODE = sys.argv[1] if len(sys.argv) > 1 else "quick"
GAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 60


def _build(mode):
    try:
        return engine.build_initial_state(board_mode=mode)
    except TypeError:
        return engine.build_initial_state(bot_level="normal")


def _sync(st):
    fn = getattr(engine, "sync_board_runtime", None)
    if callable(fn):
        fn(st)


def _best_long_for_letter(st, letter):
    try:
        moves = engine._fast_bot_moves_for_letter(st, letter, max_results=8, excluded=set(getattr(st, "usedWords", []) or []))
    except Exception:
        return ""
    best = ""
    for m in moves or []:
        w = str(m.get("word", "") or "")
        if len(w) >= 4 and len(w) > len(best):
            best = w
    return best


def active_long_words(st):
    out = []
    for l in list(getattr(st, "marketLetters", []) or []):
        w = _best_long_for_letter(st, l)
        if w:
            out.append((l, w))
    return out


def possible_long_candidates(st):
    fn = getattr(engine, "_wt_longword_market_candidates_v2", None)
    if not callable(fn):
        return []
    try:
        return fn(st, min_len=4, limit=20)
    except Exception:
        return []


def run():
    games_with_active = 0
    games_with_possible = 0
    turns = 0
    long_active_turns = 0
    possible_turns = 0
    long_words = 0
    all_words = 0

    for _ in range(GAMES):
        st = _build(MODE)
        _sync(st)
        game_active = False
        game_possible = False
        for _t in range(60):
            turns += 1
            if active_long_words(st):
                long_active_turns += 1
                game_active = True
            if possible_long_candidates(st):
                possible_turns += 1
                game_possible = True

            try:
                st = engine.apply_bot_move(st)
            except Exception:
                break

            last = st.moveHistory[-1] if st.moveHistory else None
            if last and getattr(last, "moveType", "WORD") == "WORD" and last.word:
                all_words += 1
                if len(last.word) >= 4:
                    long_words += 1

            if getattr(st, "winner", None):
                break

        if game_active:
            games_with_active += 1
        if game_possible:
            games_with_possible += 1

    print("=== LONGWORD MARKET DIAGNOSTIC V3 ===")
    print(f"games: {GAMES}")
    print(f"games_with_possible_long: {games_with_possible}/{GAMES}")
    print(f"games_with_long_active: {games_with_active}/{GAMES}")
    print(f"possible_long_turn_ratio: {(possible_turns / turns if turns else 0):.3f}")
    print(f"long_active_turn_ratio: {(long_active_turns / turns if turns else 0):.3f}")
    print(f"long_word_play_ratio: {(long_words / all_words if all_words else 0):.3f}")
    print(f"long_words_played: {long_words}/{all_words}")


if __name__ == "__main__":
    run()
