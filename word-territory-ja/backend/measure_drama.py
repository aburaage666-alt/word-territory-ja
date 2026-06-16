"""measure_drama.py — quantify gameplay drama levers.

Run from project root:
    py -3 backend/measure_drama.py quick 60
or from backend:
    py -3 measure_drama.py quick 60

This is diagnostic only. It does not change game rules.
"""
import os
import sys
import statistics
import collections
from pathlib import Path

os.environ.setdefault("WT_LANG", "ja")
BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

import engine  # noqa: E402

MODE = sys.argv[1] if len(sys.argv) > 1 else "quick"
GAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 60
CUT_LABELS = ("分断", "CUT")
BIG = 3


def _build_state(mode):
    try:
        return engine.build_initial_state(board_mode=mode)
    except TypeError:
        try:
            return engine.build_initial_state(bot_level="normal")
        except TypeError:
            return engine.build_initial_state()


def _sync(st):
    fn = getattr(engine, "sync_board_runtime", None)
    if callable(fn):
        fn(st)


def opp_groups(state, opp):
    return {tuple(sorted(map(tuple, g["cells"]))): g["liberty"]
            for g in engine.compute_group_liberties(state, opp)}


def run():
    big_danger = 0
    max_group_sizes = []
    cap_sizes = []
    max_caps = []
    telegraphed = sudden = 0
    word_lens = []
    terr_by_len = collections.defaultdict(list)
    near_encircle_events = 0
    capture_events = 0
    saved = captured = 0
    quick_battle = 0

    for _ in range(GAMES):
        st = _build_state(MODE)
        _sync(st)
        game_big_danger = False
        game_max_cap = 0
        game_battle = False
        prev_threat = {}

        for _turn in range(60):
            mover = st.currentPlayer
            opp = engine.other_player(mover)
            before = engine.clone_state(st)
            before_opp = opp_groups(before, opp)
            warning = any(v == 1 for v in before_opp.values())

            for cells, lib in before_opp.items():
                if len(cells) >= BIG and lib <= 1:
                    game_big_danger = True
                max_group_sizes.append(len(cells))

            try:
                st = engine.apply_bot_move(st)
            except Exception:
                break

            last = st.moveHistory[-1] if st.moveHistory else None
            if last and getattr(last, "moveType", "WORD") == "WORD" and last.word:
                wl = len(last.word)
                word_lens.append(wl)
                terr_by_len[wl].append(last.territoryGained or 0)

            cap = (last.captureCount or 0) if last else 0
            labels = (last.comboLabels or []) if last else []
            tg = (last.territoryGained or 0) if last else 0

            if cap > 0:
                cap_sizes.append(cap)
                capture_events += 1
                game_max_cap = max(game_max_cap, cap)
                if warning:
                    telegraphed += 1
                else:
                    sudden += 1

            after_opp = opp_groups(st, opp)
            made_ne = any(v == 1 for v in after_opp.values())
            if made_ne:
                near_encircle_events += 1

            for cells, _lib in before_opp.items():
                fs = frozenset(cells)
                if prev_threat.get(fs):
                    nowlib = None
                    for c2, l2 in after_opp.items():
                        if fs & frozenset(c2):
                            nowlib = max(nowlib or 0, l2)
                    if nowlib is None:
                        captured += 1
                    elif nowlib >= 2:
                        saved += 1

            prev_threat = {frozenset(c): (l == 1) for c, l in after_opp.items()}
            is_cut = any(any(t in str(lab) for t in CUT_LABELS) for lab in labels)
            if tg >= 3 or is_cut or made_ne or cap > 0:
                game_battle = True

            if getattr(st, "winner", None):
                break

        if game_big_danger:
            big_danger += 1
        max_caps.append(game_max_cap)
        if game_battle:
            quick_battle += 1

    avg = lambda x: statistics.mean(x) if x else 0
    print(f"=== {MODE} ({GAMES} games) — gameplay drama ===")
    print(f"[1 死活]  big group(>={BIG}) reached 逃げ道<=1 : {big_danger/GAMES*100:.0f}% of games   (target >=70%)")
    print(f"          avg max group size on board          : {avg(max_group_sizes):.1f}")
    print(f"[2 捕獲]  capture events/game                   : {capture_events/GAMES:.1f}")
    print(f"          avg capture size                      : {avg(cap_sizes):.1f}   max capture/game avg: {avg(max_caps):.1f}")
    tel = telegraphed + sudden
    print(f"          telegraphed (warning on board)        : {(telegraphed/tel*100 if tel else 0):.0f}%  ({telegraphed}/{tel})   (target >=80%)")
    print(f"[4 語彙]  word-length distribution              : {dict(sorted(collections.Counter(word_lens).items()))}")
    for L in sorted(terr_by_len):
        print(f"            len {L}: avg territory {avg(terr_by_len[L]):.1f}  (n={len(terr_by_len[L])})")
    print(f"[5 捨て]  threatened groups: saved {saved} / captured {captured}", end="")
    if saved + captured:
        print(f"   -> escape rate {saved/(saved+captured)*100:.0f}%  (depth target: 30-70%)")
    else:
        print()
    print(f"          near-encircle events/game             : {near_encircle_events/GAMES:.1f}   capture/near ratio: {capture_events/max(1,near_encircle_events):.2f}")
    print(f"[6 戦闘]  games with >=1 battle event           : {quick_battle/GAMES*100:.0f}%   (target 100% for quick)")


if __name__ == "__main__":
    run()
