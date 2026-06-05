#!/usr/bin/env python3
"""Word Territory balance scorecard (SC=x/8).
Usage: python3 scorecard.py results_v18.csv results_v23.csv ...
Reads bot_match_results_*.csv and applies 8 fixed acceptance gates.
Edit GATES below to match your own rubric.
"""
import csv, sys, statistics
from collections import defaultdict

# --- PROPOSED GATES (edit thresholds to your rubric) ---
GATES = {
    "RED% in 40-60":        ("RED win share balanced (first/second fair)",),
    "style 30-70 all":      ("every style's first-player win in [30%,70%]",),
    "word% >= 90":          ("at least 90% of moves are word moves",),
    "3-letter <= 70 (JP)":  ("JP-calibrated: <=70% 3-kana (EN-style <=60 is placeability-bound)",),
    "synergy >0 in >=50%":  ("synergy fires in at least half the games",),
    "no dead card":         ("each selected_synergy has avg fires > 0",),
    "close >= 55":          ("at least 55% of games gap<=6",),
    "gap <= 6.0":           ("average score gap <= 6",),
}

def load(p):
    with open(p, encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))

def score(rows):
    n=len(rows)
    red=sum(r['winner']=='RED' for r in rows)
    redpct=red/n*100
    # per-style first-player(=RED) win share
    st=defaultdict(lambda:[0,0])
    card=defaultdict(list)
    for r in rows:
        st[r['bot_style']][0]+=1
        if r['winner']=='RED': st[r['bot_style']][1]+=1
        card[r['selected_synergy']].append(int(r['synergies']))
    style_ok=all(30<=(w/g*100)<=70 for g,w in st.values() if g)
    style_detail={k:round(w/g*100) for k,(g,w) in st.items()}
    wm=sum(int(r['word_moves']) for r in rows); mv=sum(int(r['moves']) for r in rows)
    wordpct=wm/mv*100
    tlr=statistics.mean(float(r['three_letter_ratio']) for r in rows)*100
    synpos=sum(int(r['synergies'])>0 for r in rows)/n*100
    deadcard=any(statistics.mean(v)<=0 for v in card.values())
    close=sum(int(r['close_le_6']) for r in rows)/n*100
    gap=statistics.mean(int(r['score_gap']) for r in rows)
    results={
        "RED% in 40-60":       (40<=redpct<=60,            f"{redpct:.0f}%"),
        "style 30-70 all":     (style_ok,                  str(style_detail)),
        "word% >= 90":         (wordpct>=90,               f"{wordpct:.0f}%"),
        "3-letter <= 70 (JP)":  (tlr<=70,                   f"{tlr:.0f}%"),
        "synergy >0 in >=50%": (synpos>=50,                f"{synpos:.0f}%"),
        "no dead card":        (not deadcard,              "dead" if deadcard else "ok"),
        "close >= 55":         (close>=55,                 f"{close:.0f}%"),
        "gap <= 6.0":          (gap<=6.0,                   f"{gap:.2f}"),
    }
    sc=sum(1 for ok,_ in results.values() if ok)
    return sc, results

def label(path):
    import os, re
    b=os.path.basename(path)
    b=re.sub(r'^bot_match_(results|summary)_(ja_)?','',b)
    b=re.sub(r'\.csv$','',b)
    return b or path

if __name__=="__main__":
    files=sys.argv[1:]
    if not files:
        print("usage: scorecard.py results_*.csv"); sys.exit(1)
    allres={}
    for p in files:
        sc,res=score(load(p)); allres[label(p)]=(sc,res)
    gates=list(GATES.keys())
    w=max(len(g) for g in gates)
    cols=list(allres.keys())
    print(f"{'GATE':<{w}} | "+" | ".join(f"{c:^14}" for c in cols))
    print("-"*(w+3+len(cols)*17))
    for g in gates:
        cells=[]
        for c in cols:
            ok,val=allres[c][1][g]
            cells.append(f"{'PASS' if ok else 'FAIL'} {val:>8}")
        print(f"{g:<{w}} | "+" | ".join(f"{x:^14}" for x in cells))
    print("-"*(w+3+len(cols)*17))
    print(f"{'SC = x/8':<{w}} | "+" | ".join(f"{allres[c][0]}/8".center(14) for c in cols))
    # informational depth stat: share of games whose best_word is 4+ kana
    print("-"*(w+3+len(cols)*17))
    depth={}
    for p in files:
        rs=load(p); g4=sum(1 for r in rs if r.get('best_word') and len(r['best_word'])>=4)
        depth[label(p)]=f"{g4/len(rs)*100:.0f}%"
    print(f"{'(info) 4+ best-word share':<{w}} | "+" | ".join(depth[c].center(14) for c in cols))
