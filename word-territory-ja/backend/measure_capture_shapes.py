# measure_capture_shapes.py - diagnose why multi-cell capture does not fire.
# Run: py -3 backend/measure_capture_shapes.py quick 60
# Diagnostic only. It does not change game rules.
import os
import sys
import collections
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


def groups_owned(st, player):
    seen = set()
    out = []
    for r in range(len(st.board)):
        for c in range(len(st.board[r])):
            if (r, c) in seen or st.board[r][c].owner != player:
                continue
            stack = [(r, c)]
            cells = []
            while stack:
                cr, cc = stack.pop()
                if (cr, cc) in seen or st.board[cr][cc].owner != player:
                    continue
                seen.add((cr, cc))
                cells.append((cr, cc))
                for nr, nc in engine.get_neighbors(cr, cc):
                    if (nr, nc) not in seen and st.board[nr][nc].owner == player:
                        stack.append((nr, nc))
            if cells:
                out.append(tuple(sorted(cells)))
    return out


def group_liberties_map(st, player):
    mp = {}
    try:
        for g in engine.compute_group_liberties(st, player):
            cells = tuple(sorted(map(tuple, g.get("cells", []))))
            mp[cells] = int(g.get("liberty", 99))
    except Exception:
        pass
    return mp


def captured_cells(before, after, attacker, defender):
    cells = []
    for r in range(len(before.board)):
        for c in range(len(before.board[r])):
            if before.board[r][c].owner == defender and after.board[r][c].owner == attacker:
                cells.append((r, c))
    return cells


def one_from_two_cell_group(before, after, attacker, defender):
    caps = set(captured_cells(before, after, attacker, defender))
    if not caps:
        return False, 0
    count = 0
    for g in groups_owned(before, defender):
        if len(g) == 2:
            n = sum(1 for x in g if x in caps)
            if n == 1:
                count += 1
    return count > 0, count


def move_path(m):
    path = []
    for p in m.get("path", []) or []:
        if hasattr(p, "row") and hasattr(p, "col"):
            path.append(engine.Coord(row=p.row, col=p.col))
        elif isinstance(p, dict):
            path.append(engine.Coord(row=p.get("row"), col=p.get("col")))
        else:
            r, c = p
            path.append(engine.Coord(row=r, col=c))
    return path


def legal_candidate_stats(st, limit=20):
    attacker = st.currentPlayer
    defender = engine.other_player(attacker)
    stats = collections.Counter()
    examples = []

    try:
        moves = engine._fast_bot_moves(
            st,
            max_len=4,
            max_results=limit,
            excluded=set(getattr(st, "usedWords", []) or []),
        )
    except Exception:
        moves = []

    for m in moves or []:
        stats["candidate_moves"] += 1
        word = str(m.get("word", "") or "")
        if len(word) >= 4:
            stats["candidate_len4_plus"] += 1
        try:
            path = move_path(m)
            try:
                after = engine.validate_and_apply_move(
                    engine.clone_state(st), m["row"], m["col"], m["letter"], path, advance_market_flag=False
                )
            except TypeError:
                after = engine.validate_and_apply_move(
                    engine.clone_state(st), m["row"], m["col"], m["letter"], path
                )
        except Exception:
            continue
        cap = captured_cells(st, after, attacker, defender)
        if cap:
            stats["candidate_captures"] += 1
        if len(cap) >= 2:
            stats["candidate_multi_capture"] += 1
        ok, n = one_from_two_cell_group(st, after, attacker, defender)
        if ok:
            stats["candidate_one_from_pair"] += n
            if len(word) >= 4:
                stats["candidate_len4_one_from_pair"] += n
                if len(examples) < 5:
                    examples.append((word, m.get("letter"), m.get("row"), m.get("col"), n))
    return stats, examples


def run():
    total = collections.Counter()
    examples = []

    for _ in range(GAMES):
        st = build(MODE)
        sync(st)
        for _t in range(60):
            attacker = st.currentPlayer
            defender = engine.other_player(attacker)
            gmap = group_liberties_map(st, defender)
            pair_groups = [g for g in groups_owned(st, defender) if len(g) == 2]
            total["turns"] += 1
            total["turns_with_pair_group"] += 1 if pair_groups else 0
            total["pair_groups"] += len(pair_groups)
            total["pair_groups_liberty_le_1"] += sum(1 for g in pair_groups if gmap.get(g, 99) <= 1)
            total["pair_groups_liberty_0"] += sum(1 for g in pair_groups if gmap.get(g, 99) == 0)

            cs, ex = legal_candidate_stats(st, limit=20)
            total.update(cs)
            examples.extend(ex)

            before = engine.clone_state(st)
            try:
                st = engine.apply_bot_move(st)
            except Exception:
                break
            last = st.moveHistory[-1] if st.moveHistory else None
            cap = int((last.captureCount or 0) if last else 0)
            word = str((last.word if last else "") or "")
            if cap > 0:
                total["actual_capture_moves"] += 1
            if cap >= 2:
                total["actual_multi_capture_moves"] += 1
            ok, n = one_from_two_cell_group(before, st, attacker, defender)
            if ok:
                total["actual_one_from_pair"] += n
                if len(word) >= 4:
                    total["actual_len4_one_from_pair"] += n
            if getattr(st, "winner", None):
                break

    turns = max(1, total["turns"])
    print("=== CAPTURE SHAPE DIAGNOSTIC ===")
    print(f"mode: {MODE}")
    print(f"games: {GAMES}")
    print(f"turns: {total['turns']}")
    print(f"turns_with_pair_group: {total['turns_with_pair_group']} ({total['turns_with_pair_group']/turns:.3f})")
    print(f"pair_groups: {total['pair_groups']}")
    print(f"pair_groups_liberty_le_1: {total['pair_groups_liberty_le_1']}")
    print(f"pair_groups_liberty_0: {total['pair_groups_liberty_0']}")
    print("--- legal candidate moves sampled before bot move ---")
    print(f"candidate_moves: {total['candidate_moves']}")
    print(f"candidate_len4_plus: {total['candidate_len4_plus']}")
    print(f"candidate_captures: {total['candidate_captures']}")
    print(f"candidate_multi_capture: {total['candidate_multi_capture']}")
    print(f"candidate_one_from_pair: {total['candidate_one_from_pair']}")
    print(f"candidate_len4_one_from_pair: {total['candidate_len4_one_from_pair']}")
    print("--- actual bot moves ---")
    print(f"actual_capture_moves: {total['actual_capture_moves']}")
    print(f"actual_multi_capture_moves: {total['actual_multi_capture_moves']}")
    print(f"actual_one_from_pair: {total['actual_one_from_pair']}")
    print(f"actual_len4_one_from_pair: {total['actual_len4_one_from_pair']}")
    print(f"examples_len4_one_from_pair: {examples[:5]}")


if __name__ == "__main__":
    run()