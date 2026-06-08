# -*- coding: utf-8 -*-
"""
Word Territory JA: mobile UI + tutorial cleanup v1

Run from either:
  - git root containing word-territory-ja/, or
  - nested word-territory-ja/ repository body.

What it changes, safely:
- Adds board-size CSS class and inline CSS variable support to the board.
- Adds responsive 5x5/7x7 board CSS overrides at the end of the style block.
- Japanese-ifies the first-move mini tutorial/banner text.
- Fixes tutorial wording so it matches current rules:
  * 奪字 = enemy-letter word trigger, locked enemy prioritized
  * 回転侵略 = once per game, 2x2, letters rotate, ownership stays

It does NOT change backend logic, submit payloads, 奪字 logic, or 回転侵略 logic.
"""
from __future__ import annotations
from pathlib import Path
import sys


def find_body(start: Path) -> Path:
    p = start.resolve()
    candidates = [p, p / "word-territory-ja"]
    for c in candidates:
        if (c / "frontend" / "pages" / "index.js").exists():
            return c
    for parent in [p, *p.parents]:
        if (parent / "frontend" / "pages" / "index.js").exists():
            return parent
        nested = parent / "word-territory-ja"
        if (nested / "frontend" / "pages" / "index.js").exists():
            return nested
    raise SystemExit("ERROR: frontend/pages/index.js が見つかりません。")


def replace_once(s: str, old: str, new: str, label: str) -> tuple[str, bool]:
    if old in s:
        return s.replace(old, new, 1), True
    print(f"WARN: pattern not found for {label}")
    return s, False


def main() -> int:
    root = find_body(Path.cwd())
    idx = root / "frontend" / "pages" / "index.js"
    s = idx.read_text(encoding="utf-8", errors="replace")
    original = s
    changed = []

    # 1) Introduce boardSize const near render, after the !state loading return.
    marker = "  // ── render ────────────────────────────────────────────────────────────────\n  return <>"
    if "const boardSize = state?.boardSize || state?.board?.length || 7;" not in s:
        if marker in s:
            s = s.replace(
                marker,
                "  // ── render ────────────────────────────────────────────────────────────────\n"
                "  const boardSize = state?.boardSize || state?.board?.length || 7;\n"
                "  return <>",
                1,
            )
            changed.append("add boardSize const")
        else:
            print("WARN: render marker not found; boardSize const not inserted")

    # 2) Add board-5 / board-7 class and CSS variable to board div.
    old = 'className={`board ${boardOpeningClass} ${spectatorMode ? "board-demo" : ""} ${lastMoveIsSwing ? "board-swing" : ""} ${bridgeFlash ? "board-bridge" : ""}`} style={{touchAction:"none"}}'
    new = 'className={`board board-${boardSize} ${boardOpeningClass} ${spectatorMode ? "board-demo" : ""} ${lastMoveIsSwing ? "board-swing" : ""} ${bridgeFlash ? "board-bridge" : ""}`} style={{touchAction:"none", "--board-size": boardSize}}'
    if old in s:
        s = s.replace(old, new, 1)
        changed.append("add board size class/style")
    elif "board-${boardSize}" in s:
        print("OK: board size class already present")
    else:
        print("WARN: board class pattern not found; manual check needed")

    # 3) Tutorial Japanese text and rule-accurate wording.
    replacements = [
        ('<strong>First move</strong>', '<strong>最初の一手</strong>', "tutorial mini title"),
        ('"Choose this letter."', '"光っている文字を選ぶ"', "tutorial mini step 0"),
        ('"Tap a glowing tile."', '"緑のマスをタップ"', "tutorial mini step 1"),
        ('"Connect a word path."', '"文字をつないで単語を作る"', "tutorial mini step 2"),
        ('"Capture Word."', '"陣地を確定"', "tutorial mini step 3"),
        ('<button onClick={finishTutorial}>Skip</button>', '<button onClick={finishTutorial}>スキップ</button>', "tutorial skip"),
        ('<strong>How to play:</strong>{" "}\n          Tap a <span className="fm-green">green square</span> → type a letter → connect letters to make a word → press <strong>Claim Territory</strong>', '<strong>遊び方：</strong>{" "}\n          <span className="fm-green">緑のマス</span>を選ぶ → 文字を置く → 文字をつないで単語を作る → <strong>陣地を確定</strong>', "firstmove banner"),
        ('ロックされた敵マスを語に含めて中立化。試合に2回。', '敵文字を含む語で発動。ロック済み敵文字があれば優先して中立化。', "intro dazi rule"),
        ('2×2の敵文字を回して打ち込み、固めた陣を崩す。', '2×2の文字だけを回転。所有権は動かさず、1試合1回だけ使える。', "intro rotate rule"),
        ('<title>Word Territory{dailyMode&&dailyInfo?` · Daily #${dailyInfo.dayNumber}`:""}</title>', '<title>ワードテリトリー{dailyMode&&dailyInfo?` · Daily #${dailyInfo.dayNumber}`:""}</title>', "html title"),
    ]
    for old, new, label in replacements:
        before = s
        s, ok = replace_once(s, old, new, label)
        if ok and s != before:
            changed.append(label)

    # 4) Append final mobile CSS overrides before closing style.
    css_marker = "\n    `}</style>"
    css_block = r'''

      /* ── JA v2 mobile board + tutorial polish ─────────────────────────── */
      .board.board-5{--cell:58px;grid-template-columns:repeat(5,var(--cell))!important}
      .board.board-7{grid-template-columns:repeat(7,var(--cell))!important}
      .board.board-5 .cell-slot,.board.board-5 .cell{width:var(--cell)!important;height:var(--cell)!important}
      .board.board-7 .cell-slot,.board.board-7 .cell{width:var(--cell)!important;height:var(--cell)!important}
      .tutorial-mini{display:flex;align-items:center;gap:8px;flex-wrap:wrap;background:#fff8e1;border:1px solid #f6d365;border-radius:12px;padding:9px 12px;margin:8px 0;font-size:13px;box-shadow:0 2px 10px rgba(31,41,51,.06)}
      .tutorial-mini strong{font-weight:900;color:#7c4a03}
      .tutorial-mini button{margin-left:auto;border:1px solid #d6b453;background:#fff;border-radius:999px;padding:5px 10px;font-size:12px;font-weight:800;cursor:pointer}
      .firstmove-banner{line-height:1.55;border-radius:12px}
      @media(max-width:900px){
        .board.board-5{--cell:clamp(48px,calc((100vw - 52px) / 5),64px)!important;--gap:5px!important;grid-template-columns:repeat(5,var(--cell))!important}
        .board.board-7{--cell:clamp(38px,calc((100vw - 54px) / 7),52px)!important;--gap:4px!important;grid-template-columns:repeat(7,var(--cell))!important}
        .hdr-r{justify-content:flex-start;width:100%}
        .bsm,.bprim,.ba{min-height:42px}
      }
      @media(max-width:600px){
        .page{padding:10px 6px 8px!important}
        .hdr{gap:8px!important;margin-bottom:8px!important}
        .hdr-l h1{font-size:18px!important;letter-spacing:1px!important}
        .sub,.opening-note,.tagline{font-size:11px!important;line-height:1.35!important}
        .board-wrap{overflow:visible!important;display:flex;justify-content:center}
        .board.board-5{--cell:clamp(50px,calc((100vw - 48px) / 5),66px)!important;--gap:5px!important;padding:8px!important;width:max-content!important;max-width:100%!important}
        .board.board-7{--cell:clamp(36px,calc((100vw - 48px) / 7),50px)!important;--gap:3px!important;padding:7px!important;width:max-content!important;max-width:100%!important}
        .cell-slot,.cell{border-radius:8px!important}
        .brow{grid-template-columns:1fr 1fr!important;gap:8px!important;padding:8px 0!important}
        .brow .bsubmit{grid-column:1 / -1!important}
        .ba{padding:12px 8px!important;font-size:13px!important;border-radius:11px!important}
        .mpanel{padding:10px 9px!important;border-radius:14px!important}
        .mrow{gap:7px!important;align-items:center!important}
        .pvbox{min-width:150px!important;flex:1!important}
        .pvword{font-size:25px!important;line-height:1.1!important}
        .tutorial-mini{font-size:12px;padding:8px 10px;margin:6px 0}
        .tutorial-mini button{margin-left:0;padding:5px 9px}
        .firstmove-banner{font-size:12px!important;padding:8px 10px!important}
        .panel{border-radius:14px!important;margin-bottom:8px!important}
        .ph{padding:10px 12px!important}
        .hist{max-height:150px!important}
      }
      @media(max-width:360px){
        .board.board-5{--cell:clamp(44px,calc((100vw - 40px) / 5),58px)!important;--gap:4px!important}
        .board.board-7{--cell:clamp(32px,calc((100vw - 36px) / 7),44px)!important;--gap:2px!important}
      }
'''
    if "JA v2 mobile board + tutorial polish" not in s:
        if css_marker in s:
            s = s.replace(css_marker, css_block + css_marker, 1)
            changed.append("append mobile/tutorial CSS")
        else:
            print("WARN: style closing marker not found; CSS not inserted")
    else:
        print("OK: mobile/tutorial CSS already present")

    if s == original:
        print("No changes made.")
        return 0

    backup = idx.with_suffix(idx.suffix + ".bak_mobile_tutorial_v1")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")
    idx.write_text(s, encoding="utf-8", newline="\n")

    print(f"Patched: {idx}")
    print(f"Backup : {backup}")
    print("Changes:")
    for c in changed:
        print(f"- {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
