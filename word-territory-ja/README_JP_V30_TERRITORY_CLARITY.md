# Word Territory JP v30 Territory Clarity FULL ENGINE

This is v28 FULL ENGINE plus frontend-only territory clarity improvements.

Implemented checks:

1. Captured cells are visibly stamped with 「奪取」 on the board.
2. Non-capture territory changes show 「+1」 on changed cells.
3. CUT / BRIDGE / ENCIRCLE / SWING MOVE are shown both as board-path effects and as a board-level ribbon.
4. RED/BLUE territory change is shown as before -> after with an animated territory bar.
5. Backend engine remains clean v18 FULL ENGINE; no balance logic was changed.

Use RUN_NO_POWERSHELL.bat if PowerShell is unavailable.


## Release completeness rule

A FULL ENGINE release must include `backend/language_profiles/__init__.py` and `backend/language_profiles/ja.py`. The backend imports `from language_profiles import ja` when `WT_LANG=ja`; omitting these files can work only on a developer repo that already has leftovers, but fails on a blank checkout.
