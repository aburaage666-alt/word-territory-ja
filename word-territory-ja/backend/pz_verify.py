"""pz_verify.py — verify 詰めワード candidates are solvable and non-trivial.

Run from project root:
    py -3 backend/pz_verify.py
or from backend:
    py -3 pz_verify.py

OK means: at least one solving move exists, and not every legal move solves it.
This verifier is diagnostic-only and exits 0 so it does not block commits.
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("WT_LANG", "ja")
BACKEND = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND))

import engine  # noqa: E402


def _sync(st):
    fn = getattr(engine, "sync_board_runtime", None)
    if callable(fn):
        fn(st)


def _build_quick_state():
    try:
        return engine.build_initial_state(board_mode="quick")
    except TypeError:
        try:
            return engine.build_initial_state(bot_level="normal")
        except TypeError:
            return engine.build_initial_state()


def _regions(state, player):
    board = state.board
    n = len(board)
    seen = set()
    regs = []
    for r in range(n):
        for c in range(len(board[r])):
            if board[r][c].owner != player or (r, c) in seen:
                continue
            cells = set()
            stack = [(r, c)]
            while stack:
                cr, cc = stack.pop()
                if (cr, cc) in seen:
                    continue
                seen.add((cr, cc))
                cells.add((cr, cc))
                for nr, nc in engine.get_neighbors(cr, cc):
                    if board[nr][nc].owner == player and (nr, nc) not in seen:
                        stack.append((nr, nc))
            regs.append(cells)
    return regs


def _road_connected(state, player, axis):
    for reg in _regions(state, player):
        if axis == "lr":
            if any(c == 0 for _r, c in reg) and any(c == len(state.board[0]) - 1 for _r, c in reg):
                return True
        if axis == "tb":
            if any(r == 0 for r, _c in reg) and any(r == len(state.board) - 1 for r, _c in reg):
                return True
    return False


def _fallback_goal(before, after, goal, player):
    typ = (goal or {}).get("type")
    opponent = engine.other_player(player)

    if typ == "capture":
        for r in range(len(after.board)):
            for c in range(len(after.board[r])):
                if before.board[r][c].owner == opponent and after.board[r][c].owner == player:
                    return True
        last = after.moveHistory[-1] if after.moveHistory else None
        return bool(last and (last.captureCount or 0) > 0)

    if typ == "connect":
        return len(_regions(after, player)) < len(_regions(before, player))

    if typ == "near_encircle":
        before_min = min((g.get("liberty", 99) for g in engine.compute_group_liberties(before, opponent)), default=99)
        after_min = min((g.get("liberty", 99) for g in engine.compute_group_liberties(after, opponent)), default=99)
        return after_min <= 1 and after_min < before_min

    if typ == "connect_road":
        return _road_connected(after, player, (goal or {}).get("axis", "lr"))

    return False


def _goal_ok(before, after, goal, player):
    judge = getattr(engine, "evaluate_puzzle_goal", None)
    if callable(judge):
        for args in ((before, after, goal), (after, goal), (before, after, goal, player)):
            try:
                return bool(judge(*args))
            except TypeError:
                continue
            except Exception:
                break
    return _fallback_goal(before, after, goal, player)


def verify(cells, market, player, goal, limit=40):
    st = _build_quick_state()
    _sync(st)
    n = len(st.board)

    for r in range(n):
        for c in range(len(st.board[r])):
            cc = st.board[r][c]
            cc.letter = None
            cc.owner = None
            cc.fortified = False

    for (r, c, o, l) in cells:
        st.board[r][c].letter = l
        st.board[r][c].owner = o

    st.marketLetters = list(market)
    st.previewLetters = []
    st.currentPlayer = player
    _sync(st)

    total = 0
    solving = []
    for L in market:
        for mv in engine.get_letter_preview_moves(st, L, limit=limit):
            total += 1
            path = [engine.Coord(row=q["row"], col=q["col"]) for q in mv.get("path", [])]
            try:
                after = engine.validate_and_apply_move(
                    engine.clone_state(st),
                    mv["row"],
                    mv["col"],
                    L,
                    path,
                )
            except Exception:
                continue

            if _goal_ok(st, after, goal, player):
                solving.append((mv.get("word"), mv["row"], mv["col"], L))

    uniq = sorted(set(solving))
    return total, len(uniq), uniq[:4]


if __name__ == "__main__":
    RICH = ["い", "か", "し", "つ", "な"]
    candidates = {
        "capture2": (
            [(2, 1, "BLUE", "ぬ"),
             (1, 1, "RED", "た"), (3, 1, "RED", "ち"), (2, 2, "RED", "の"),
             (2, 0, None, "か"), (1, 0, None, "し"), (3, 0, None, "つ")],
            RICH, "RED", {"type": "capture"}),
        "connect2": (
            [(1, 1, "RED", "ち"), (3, 3, "RED", "の"),
             (2, 2, None, "か"), (1, 2, None, "し"), (2, 1, None, "つ"),
             (2, 3, None, "な"), (3, 2, None, "い"), (1, 3, None, "か")],
            RICH, "RED", {"type": "connect"}),
        "road2_lr": (
            [(1, 0, "RED", "ち"), (1, 1, "RED", "の"), (1, 3, "RED", "か"), (1, 4, "RED", "し"),
             (0, 2, None, "か"), (1, 2, None, "し"), (2, 2, None, "つ"),
             (0, 1, None, "な"), (2, 3, None, "い")],
            RICH, "RED", {"type": "connect_road", "axis": "lr"}),
    }

    bad = 0
    for pid, (cells, mk, pl, goal) in candidates.items():
        try:
            t, s, ex = verify(cells, mk, pl, goal)
            ok = "OK" if (s >= 1 and t > s) else ("TRIVIAL" if t == s and t > 0 else "UNSOLVABLE")
            print(f"{pid:10s} {str(goal):42s} legal={t:3d} solving={s:3d} {ok}  e.g. {ex[:2]}")
            if ok != "OK":
                bad += 1
        except Exception as e:
            bad += 1
            print(f"{pid:10s} ERROR {type(e).__name__}: {e}")

    if bad:
        print(f"pz_verify_warning={bad} candidate(s) need review")
    else:
        print("pz_verify=PASS")
