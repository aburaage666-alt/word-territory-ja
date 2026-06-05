from pathlib import Path
import sys
root = Path(__file__).resolve().parent
paths = [root/'backend'/'ja_words.txt', root/'backend'/'ja_words_ui.txt', root/'backend'/'dictionaries'/'ja_words.txt', root/'backend'/'dictionaries'/'ja_words_ui.txt']
banned = {'やか','くもの','くりから','やさいか','うみか'}
required = {'やきもの','よみもの','のみもの','たべもの','かきもの','うみかぜ','うみかつき','うみからまつ','うみかわ','うみかわうそ'}
failed=False
for p in paths:
    if not p.exists():
        print(f'MISSING: {p}')
        failed=True
        continue
    words=set(p.read_text(encoding='utf-8').split())
    bh=sorted(banned & words)
    miss=sorted(required - words) if 'ja_words.txt' in p.name else []
    print(f'{p.relative_to(root)} words={len(words)} banned={bh} missing_required={miss}')
    if bh or (p.name=='ja_words.txt' and miss):
        failed=True
sys.exit(1 if failed else 0)
