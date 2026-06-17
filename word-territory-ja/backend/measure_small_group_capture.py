# measure_small_group_capture.py - small group-capture diagnostic V4
import os, sys, statistics
from pathlib import Path

os.environ.setdefault("WT_LANG", "ja")
BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

import engine

MODE = sys.argv[1] if len(sys.argv) > 1 else "quick"
GAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 60

def build(mode):
    try:
        return engine.build_initial_state(board_mode=mode)
    except TypeError:
        return engine.build_initial_state(bot_level="normal")

def sync(st):
    f = getattr(engine, "sync_board_runtime", None)
    if callable(f):
        f(st)

def run():
    events = 0
    caps = []
    maxcaps = []
    pair_label = 0
    enabled = bool(getattr(engine, "_WT_PAIR_CAPTURE_V4_ENABLED", False))
    bot_enabled = bool(getattr(engine, "_WT_PAIR_CAPTURE_BOT_PREFERENCE_ENABLED", False))

    for _ in range(GAMES):
        st = build(MODE)
        sync(st)
        mx = 0
        for _t in range(60):
            try:
                st = engine.apply_bot_move(st)
            except Exception:
                break
            last = st.moveHistory[-1] if st.moveHistory else None
            cap = int((last.captureCount or 0) if last else 0)
            labels = list((last.comboLabels or []) if last else [])
            if cap > 0:
                events += 1
                caps.append(cap)
                mx = max(mx, cap)
            if "連鎖捕り" in labels or "Pair Capture" in labels:
                pair_label += 1
            if getattr(st, "winner", None):
                break
        maxcaps.append(mx)

    avg = lambda x: statistics.mean(x) if x else 0
    print("=== SMALL GROUP CAPTURE DIAGNOSTIC V4 ===")
    print(f"enabled: {enabled}")
    print(f"bot_pair_capture_preference: {bot_enabled}")
    print(f"games: {GAMES}")
    print(f"capture events/game: {events/GAMES:.2f}")
    print(f"avg capture size: {avg(caps):.2f}")
    print(f"max capture/game avg: {avg(maxcaps):.2f}")
    print(f"multi-cell capture events: {sum(1 for x in caps if x >= 2)}")
    print(f"pair_capture_label_events: {pair_label}")

if __name__ == "__main__":
    run()
