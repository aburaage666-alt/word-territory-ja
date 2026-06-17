# measure_drama.py - warning-aligned gameplay diagnostics
import os,sys,statistics,collections
from pathlib import Path
os.environ.setdefault("WT_LANG","ja")
BACKEND=Path(__file__).resolve().parent
sys.path.insert(0,str(BACKEND))
import engine
MODE=sys.argv[1] if len(sys.argv)>1 else "quick"
GAMES=int(sys.argv[2]) if len(sys.argv)>2 else 60
BIG=3
def build(mode):
    try: return engine.build_initial_state(board_mode=mode)
    except TypeError: return engine.build_initial_state(bot_level="normal")
def sync(st):
    f=getattr(engine,"sync_board_runtime",None)
    if callable(f): f(st)
def groups(st,p):
    return {tuple(sorted(map(tuple,g["cells"]))):g["liberty"] for g in engine.compute_group_liberties(st,p)}
def warn(st,defender):
    f=getattr(engine,"get_capture_warning_cells",None)
    if callable(f):
        try: return bool(f(st,player=defender,limit=10))
        except Exception: pass
    return any(g.get("liberty",99)<=1 for g in engine.compute_group_liberties(st,defender))
def run():
    big=events=tel=sud=near=battle=saved=captured=0; caps=[]; maxcaps=[]; lens=[]; terr=collections.defaultdict(list); maxgroups=[]
    for _ in range(GAMES):
        st=build(MODE); sync(st); game_big=False; game_battle=False; game_max=0; prev={}
        for _t in range(60):
            mover=st.currentPlayer; defender=engine.other_player(mover); before=engine.clone_state(st); bg=groups(before,defender); w=warn(before,defender)
            for cells,lib in bg.items():
                if len(cells)>=BIG and lib<=1: game_big=True
                maxgroups.append(len(cells))
            try: st=engine.apply_bot_move(st)
            except Exception: break
            last=st.moveHistory[-1] if st.moveHistory else None
            if last and getattr(last,"moveType","WORD")=="WORD" and last.word:
                lens.append(len(last.word)); terr[len(last.word)].append(last.territoryGained or 0)
            cap=(last.captureCount or 0) if last else 0; labels=(last.comboLabels or []) if last else []; tg=(last.territoryGained or 0) if last else 0
            if cap>0:
                events+=1; caps.append(cap); game_max=max(game_max,cap)
                if w: tel+=1
                else: sud+=1
            ag=groups(st,defender); made=any(v==1 for v in ag.values())
            if made: near+=1
            for cells,_lib in bg.items():
                fs=frozenset(cells)
                if prev.get(fs):
                    now=None
                    for c2,l2 in ag.items():
                        if fs & frozenset(c2): now=max(now or 0,l2)
                    if now is None: captured+=1
                    elif now>=2: saved+=1
            prev={frozenset(c):(l==1) for c,l in ag.items()}
            if tg>=3 or made or cap>0 or any("分断" in str(x) for x in labels): game_battle=True
            if getattr(st,"winner",None): break
        if game_big: big+=1
        if game_battle: battle+=1
        maxcaps.append(game_max)
    avg=lambda x: statistics.mean(x) if x else 0
    print(f"=== {MODE} ({GAMES} games) - gameplay drama V2 warning-aligned ===")
    print(f"[1 死活]  big group(>={BIG}) reached 逃げ道<=1 : {big/GAMES*100:.0f}% of games   (target >=70%)")
    print(f"          avg max group size on board          : {avg(maxgroups):.1f}")
    print(f"[2 捕獲]  capture events/game                   : {events/GAMES:.1f}")
    print(f"          avg capture size                      : {avg(caps):.1f}   max capture/game avg: {avg(maxcaps):.1f}")
    total=tel+sud
    print(f"          telegraphed actual-warning            : {(tel/total*100 if total else 0):.0f}%  ({tel}/{total})   (target >=70%)")
    print(f"[4 語彙]  word-length distribution              : {dict(sorted(collections.Counter(lens).items()))}")
    for L in sorted(terr): print(f"            len {L}: avg territory {avg(terr[L]):.1f}  (n={len(terr[L])})")
    print(f"[5 捨て]  threatened groups: saved {saved} / captured {captured}")
    print(f"          near-encircle events/game             : {near/GAMES:.1f}   capture/near ratio: {events/max(1,near):.2f}")
    print(f"[6 戦闘]  games with >=1 battle event           : {battle/GAMES*100:.0f}%   (target 100% for quick)")
if __name__=="__main__": run()
