import os, statistics
import sys
sys.path.insert(0, ".")
os.environ["WT_LANG"] = "ja"
import engine

def opp_min_and_maxdrop(before, after, opp):
    bg = engine.compute_group_liberties(before, opp)
    ag = engine.compute_group_liberties(after, opp)
    bm = {}
    am = {}
    for g in bg:
        for cell in g["cells"]:
            bm[cell] = g["liberty"]
    for g in ag:
        for cell in g["cells"]:
            am[cell] = g["liberty"]

    drop = 0
    min_after = None
    for cell, a in am.items():
        b = bm.get(cell)
        if b is None:
            continue
        drop = max(drop, b - a)
        min_after = a if min_after is None else min(min_after, a)
    return drop, (min_after if min_after is not None else 99)

def run(board_mode, games=40):
    stats = {"near": [], "double": [], "drop2": [], "cap_after_near": 0, "near_total": 0,
             "first_near": [], "first_cap": []}

    for _ in range(games):
        st = engine.build_initial_state(board_mode=board_mode)
        near = dbl = drop2 = 0
        pend_near = 0
        cap_after = 0
        first_near = None
        first_cap = None
        turn = 0

        for _ in range(60):
            opp = engine.other_player(st.currentPlayer)
            before = engine.clone_state(st)
            try:
                st = engine.apply_bot_move(st)
            except Exception:
                break

            turn += 1
            drop, min_after = opp_min_and_maxdrop(before, st, opp)
            last = st.moveHistory[-1] if st.moveHistory else None
            cap = last.captureCount if last else 0
            tg = (last.territoryGained if last else 0) or 0
            cg = max(0, min(cap, tg))
            pg = max(0, tg - cg)

            if drop >= 2:
                drop2 += 1
            if min_after == 1:
                near += 1
                first_near = first_near or turn
                pend_near = 2
            if pg >= 3 and cg >= 1:
                dbl += 1
            if cap > 0:
                first_cap = first_cap or turn
                if pend_near > 0:
                    cap_after += 1
                    pend_near = 0
            if pend_near > 0:
                pend_near -= 1
            if getattr(st, "winner", None):
                break

        stats["near"].append(near)
        stats["double"].append(dbl)
        stats["drop2"].append(drop2)
        stats["near_total"] += near
        stats["cap_after_near"] += cap_after
        if first_near:
            stats["first_near"].append(first_near)
        if first_cap:
            stats["first_cap"].append(first_cap)

    def avg(x):
        return statistics.mean(x) if x else 0

    print(f"=== {board_mode} ({games} games) ===")
    print(f"  包囲寸前/game        : {avg(stats['near']):.1f}   (ideal 5x5: 2-4)")
    print(f"  二重の手/game        : {avg(stats['double']):.1f}   (ideal 5x5: 1-3)")
    print(f"  逃げ道drop>=2 /game  : {avg(stats['drop2']):.1f}")
    print(f"  初回包囲寸前 turn    : {avg(stats['first_near']):.1f}   (ideal: <=4)")
    print(f"  初回捕獲 turn        : {avg(stats['first_cap']):.1f}   (ideal: <=6)")
    pct = (stats["cap_after_near"] / stats["near_total"] * 100) if stats["near_total"] else 0
    print(f"  包囲寸前→2手内に捕獲 : {pct:.0f}%")

if __name__ == "__main__":
    run("quick", 40)
    run("standard", 40)
