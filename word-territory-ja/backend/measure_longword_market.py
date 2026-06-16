
# measure_longword_market.py - check whether market offers 4+ kana enablers.
#
# Run:
#     py -3 backend/measure_longword_market.py quick 60
#
# Diagnostic only. A good target after WT_LONGWORD_MARKET_V2:
# - games_with_long_active: 70%+
# - long_active_turn_ratio: 25%+
import os
import sys
from pathlib import Path

os.environ.setdefault("WT_LANG", "ja")
BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

import engine  # noqa: E402

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


def active_has_long(st):
    cands = []
    fn = getattr(engine, "_wt_longword_market_candidates_v2", None)
    if callable(fn):
        try:
            cands = fn(st, min_len=4, limit=20)
        except Exception:
            cands = []
    letters = set(getattr(st, "marketLetters", []) or [])
    return any(c.get("letter") in letters for c in cands)


def run():
    games_with = 0
    turns = 0
    long_turns = 0
    long_words = 0
    all_words = 0

    for _ in range(GAMES):
        st = _build(MODE)
        _sync(st)
        game_has = False
        for _t in range(60):
            turns += 1
            if active_has_long(st):
                long_turns += 1
                game_has = True
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
        if game_has:
            games_with += 1

    print("=== LONGWORD MARKET DIAGNOSTIC ===")
    print(f"games: {GAMES}")
    print(f"games_with_long_active: {games_with}/{GAMES}")
    print(f"long_active_turn_ratio: {(long_turns / turns if turns else 0):.3f}")
    print(f"long_word_play_ratio: {(long_words / all_words if all_words else 0):.3f}")
    print(f"long_words_played: {long_words}/{all_words}")


if __name__ == "__main__":
    run()
