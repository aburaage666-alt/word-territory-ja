import csv, sys
from pathlib import Path

if len(sys.argv) < 2:
    print('Usage: py validate_jp_v28_results_strict.py backend\\bot_match_results_ja_v28_full_engine.csv')
    sys.exit(2)
path = Path(sys.argv[1])
rows = list(csv.DictReader(path.open(encoding='utf-8')))
if not rows:
    print('ERROR: empty CSV')
    sys.exit(1)
seed = sum(int(float(r.get('seed_uses') or 0)) for r in rows)
passes = sum(int(float(r.get('pass_uses') or 0)) for r in rows)
word_moves = sum(int(float(r.get('word_moves') or 0)) for r in rows)
moves = sum(int(float(r.get('moves') or 0)) for r in rows)
three = sum(int(float(r.get('three_letter_words') or 0)) for r in rows)
gaps = [float(r.get('score_gap') or 0) for r in rows]
close = sum(1 for r in rows if int(float(r.get('close_le_6') or 0)) == 1)
word_pct = (word_moves / moves * 100) if moves else 0
three_pct = (three / word_moves * 100) if word_moves else 0
avg_gap = sum(gaps)/len(gaps)
close_pct = close/len(rows)*100
banned = {'やか','くもの','くりから','やさいか','うみか'}
banned_hits = [(r.get('match_id'), r.get('best_word')) for r in rows if (r.get('best_word') or '') in banned]
print(f'games={len(rows)} seed={seed} pass={passes} word%={word_pct:.1f} three%={three_pct:.1f} avg_gap={avg_gap:.2f} close%={close_pct:.1f} banned_hits={banned_hits}')
failed=[]
if seed != 0: failed.append(f'seed must be 0, got {seed}')
if passes != 0: failed.append(f'pass must be 0, got {passes}')
if word_pct < 99.0: failed.append(f'word% must be >=99.0, got {word_pct:.1f}')
if three_pct > 70.0: failed.append(f'3-letter% must be <=70.0, got {three_pct:.1f}')
if avg_gap > 6.0: failed.append(f'avg_gap must be <=6.0, got {avg_gap:.2f}')
if banned_hits: failed.append(f'banned best_word hits: {banned_hits}')
if failed:
    print('STRICT VALIDATION FAILED:')
    for f in failed: print(' -', f)
    sys.exit(1)
print('STRICT VALIDATION OK')
