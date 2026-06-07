from pathlib import Path
import re
import shutil
import subprocess
import sys

root = Path(r"C:\\\\Users\\\\info\\\\Downloads\\\\word-territory-ja-relief-rarity-work")

if (root / "word-territory-ja" / "backend" / "engine.py").exists():
    app = root / "word-territory-ja"
    rel_engine = "word-territory-ja/backend/engine.py"
    rel_main = "word-territory-ja/backend/main.py"
    rel_api = "word-territory-ja/frontend/lib/api.js"
    rel_index = "word-territory-ja/frontend/pages/index.js"
elif (root / "backend" / "engine.py").exists():
    app = root
    rel_engine = "backend/engine.py"
    rel_main = "backend/main.py"
    rel_api = "frontend/lib/api.js"
    rel_index = "frontend/pages/index.js"
else:
    raise SystemExit("backend/engine.py が見つかりません。clone構造を確認してください。")

engine = root / rel_engine
main = root / rel_main
api = root / rel_api
index = root / rel_index

print("APP:", app)
print("ENGINE:", engine)
print("MAIN:", main)
print("API:", api)
print("INDEX:", index)

for fp in [engine, main, api, index]:
    if fp.exists():
        shutil.copy2(fp, fp.with_suffix(fp.suffix + ".relief_rarity.bak"))

# ============================================================
# backend/engine.py
# ============================================================

engine_text = engine.read_text(encoding="utf-8")
marker = "# WT_JA_RELIEF_RARITY_PITY_WILD_20260607"

old = engine_text.find(marker)
if old >= 0:
    engine_text = engine_text[:old].rstrip() + "\n"

engine_patch = r'''

# WT_JA_RELIEF_RARITY_PITY_WILD_20260607
# Implements:
# 1) Pity market bias when the current market has no playable word.
# 2) Rarity scoring for hard kana.
# 3) Free Seed during true stuck states.
# 4) One-time stuck swap and occasional Wild tile.

def _wt_ja_relief_is_ja():
    try:
        return globals().get("_LANG") == "ja"
    except Exception:
        return False


def _wt_ja_relief_pool():
    try:
        pool = [x for x in _ALL_LETTERS if isinstance(x, str) and len(x) == 1]
        if pool:
            return pool
    except Exception:
        pass
    return list("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ")


def _wt_ja_relief_is_kana(x):
    if x == "*":
        return True
    if not isinstance(x, str) or len(x) != 1:
        return False
    o = ord(x)
    return (0x3041 <= o <= 0x3096) or x == "\u30fc"


def _wt_ja_relief_clean_seq(seq, existing=None, offset=0, allow_wild=True):
    if not _wt_ja_relief_is_ja():
        return seq
    existing = set(existing or [])
    pool = _wt_ja_relief_pool()
    out = []
    for x in seq or []:
        if x == "*" and allow_wild and "*" not in out:
            out.append(x)
        elif _wt_ja_relief_is_kana(x) and x != "*" and x not in out:
            out.append(x)
    i = offset
    while len(out) < 3:
        c = pool[i % len(pool)]
        i += 1
        if c not in out and c not in existing:
            out.append(c)
    return out[:3]


def _wt_ja_relief_letter_moves(state, letter, max_results=2):
    if letter == "*":
        return [{"word": "*"}]
    try:
        return _fast_bot_moves_for_letter(
            state,
            letter,
            max_results=max_results,
            excluded=set(getattr(state, "usedWords", []) or []),
        )
    except Exception:
        return []


def _wt_ja_relief_letter_playable(state, letter):
    try:
        return len(_wt_ja_relief_letter_moves(state, letter, max_results=1)) > 0
    except Exception:
        return False


def _wt_ja_relief_market_has_play(state, letters):
    try:
        return any(_wt_ja_relief_letter_playable(state, l) for l in (letters or []) if l)
    except Exception:
        return False


def _wt_ja_relief_is_stuck(state):
    if not _wt_ja_relief_is_ja():
        return False
    try:
        active = list(getattr(state, "marketLetters", []) or [])
        if _wt_ja_relief_market_has_play(state, active):
            return False
        # Market is dead. Check if the broader candidate pool has any playable escape.
        scores = _score_all_letters(state)
        if any((s or {}).get("words", 0) > 0 for s in scores.values()):
            return True
        almost = find_almost_words(state, limit=8)
        return len(almost or []) > 0
    except Exception:
        return False


def _wt_ja_relief_pity_candidates(state, exclude=None, limit=8):
    exclude = set(exclude or [])
    out = []

    def add(x):
        if x and x not in exclude and x not in out and _wt_ja_relief_is_kana(x):
            out.append(x)

    try:
        # 1. Existing comeback candidate engine: strongest escape source.
        for l in _comeback_letter_candidates(state, exclude=exclude, limit=limit * 2):
            add(l)
    except Exception:
        pass

    try:
        # 2. Score table: letters known to produce legal words now.
        scores = _score_all_letters(state)
        ranked = sorted(
            [(l, s) for l, s in scores.items() if (s or {}).get("words", 0) > 0],
            key=lambda x: -((x[1].get("words", 0) * 2) + x[1].get("gain", 0)),
        )
        for l, _s in ranked:
            add(l)
    except Exception:
        pass

    try:
        # 3. Almost words: one-letter-away escape.
        board_letters = board_letters_set(state)
        for a in find_almost_words(state, limit=limit * 3):
            l = str(a.get("needs", ""))
            if l not in board_letters:
                add(l)
    except Exception:
        pass

    # 4. Safe common fallback. This is not restriction; it is a breathing point.
    for l in "あいいうえおかきくこさしすせたちつてとなにのはひふほまみむめもやゆよらりるれろ":
        add(l)

    # Prefer candidates that actually make a word.
    playable = [l for l in out if _wt_ja_relief_letter_playable(state, l)]
    if playable:
        return playable[:limit]
    return out[:limit]


# ---- 2) rarity scoring -------------------------------------------------------

try:
    _wt_ja_relief_orig_word_score_20260607 = word_score

    def _wt_ja_rarity_bonus_20260607(word):
        if not _wt_ja_relief_is_ja():
            return 0
        w = _norm_word(word)
        if not w:
            return 0

        weights = dict(globals().get("_LETTER_WEIGHTS", {}) or {})
        if not weights:
            return 0

        vals = [v for v in weights.values() if isinstance(v, (int, float)) and v > 0]
        if not vals:
            return 0

        max_freq = max(vals)
        bonus = 0
        seen = set()

        # Hard kana jackpot, but capped to avoid chaos.
        for ch in w:
            if ch in seen:
                continue
            seen.add(ch)

            freq = max(1, int(weights.get(ch, 1)))
            raw = int(round((max_freq / freq) ** 0.5)) - 1
            raw = max(0, min(3, raw))

            # Explicitly reward historically dead-feeling kana.
            if ch in set("ぬねへをづぢ"):
                raw = max(raw, 3)
            elif ch in set("にむめゆよるれろ"):
                raw = max(raw, 1)

            bonus += raw

        # Do not let rarity dominate territory.
        if len(w) <= 3:
            return min(bonus, 4)
        return min(bonus, 6)

    def word_score(word: str) -> int:
        base = _wt_ja_relief_orig_word_score_20260607(word)
        if not _wt_ja_relief_is_ja():
            return base
        return int(base) + int(_wt_ja_rarity_bonus_20260607(word))

except Exception:
    pass


# ---- 1 & 4) market pity + occasional wild -----------------------------------

def _wt_ja_relief_apply_to_market_pair(state, pair):
    if not _wt_ja_relief_is_ja():
        return pair

    try:
        active, preview = pair
    except Exception:
        return pair

    active = _wt_ja_relief_clean_seq(active, offset=0, allow_wild=True)
    preview = _wt_ja_relief_clean_seq(preview, existing=set(active), offset=7, allow_wild=False)

    import random as _r

    stuck = not _wt_ja_relief_market_has_play(state, active)

    if stuck:
        # Pity: force one truly usable tile into the market.
        candidates = _wt_ja_relief_pity_candidates(state, exclude=set(active), limit=8)
        if candidates:
            replace_idx = 0
            for i, l in enumerate(active):
                if l == "*" or not _wt_ja_relief_letter_playable(state, l):
                    replace_idx = i
                    break
            active[replace_idx] = candidates[0]

        # Wild appears as emergency valve when market was dead.
        try:
            if not getattr(state, "freeLetterUsed", False) and "*" not in active:
                if _r.random() < 0.35:
                    active[-1] = "*"
        except Exception:
            pass

    else:
        # Rare Wild: enough to create stories, not enough to erase kana constraints.
        try:
            turn = int(getattr(state, "turn", 1) or 1)
            if turn >= 5 and not getattr(state, "freeLetterUsed", False) and "*" not in active:
                if _r.random() < 0.06:
                    active[-1] = "*"
        except Exception:
            pass

    # If active became dead again after cleanup, put one pity letter in preview.
    try:
        used = set(active) | set(preview)
        for c in _wt_ja_relief_pity_candidates(state, exclude=used, limit=3):
            if c not in preview and c not in active:
                preview[-1] = c
                break
    except Exception:
        pass

    return active[:3], preview[:3]


try:
    _wt_ja_relief_orig_generate_letter_market_20260607 = generate_letter_market

    def generate_letter_market(state):
        pair = _wt_ja_relief_orig_generate_letter_market_20260607(state)
        return _wt_ja_relief_apply_to_market_pair(state, pair)

except Exception:
    pass


try:
    _wt_ja_relief_orig_advance_market_20260607 = advance_market

    def advance_market(state, used_letter):
        pair = _wt_ja_relief_orig_advance_market_20260607(state, used_letter)
        return _wt_ja_relief_apply_to_market_pair(state, pair)

except Exception:
    pass


# ---- 3) free seed during stuck state ----------------------------------------

try:
    _wt_ja_relief_orig_apply_seed_move_20260607 = apply_seed_move

    def apply_seed_move(state, row: int, col: int, letter: str, advance_market_flag: bool = False):
        if _wt_ja_relief_is_ja() and _wt_ja_relief_is_stuck(state):
            try:
                temp_state = deepcopy(state)
                original_synergy = getattr(state, "selectedSynergy", "")
                # Existing engine already treats SEED_TACTICIAN as no-cost seed.
                temp_state.selectedSynergy = "SEED_TACTICIAN"
                out = _wt_ja_relief_orig_apply_seed_move_20260607(
                    temp_state,
                    row,
                    col,
                    letter,
                    advance_market_flag=advance_market_flag,
                )
                out.selectedSynergy = original_synergy
                try:
                    if out.moveHistory:
                        out.moveHistory[-1].word = "FREE SEED"
                        labels = list(getattr(out.moveHistory[-1], "comboLabels", []) or [])
                        if "RELIEF SEED" not in labels:
                            labels.append("RELIEF SEED")
                        out.moveHistory[-1].comboLabels = labels
                        out.lastComboLabels = labels
                        out.recentMoves = [f"{state.currentPlayer}: FREE SEED ({letter})"] + list(getattr(out, "recentMoves", []) or [])[:4]
                except Exception:
                    pass
                return out
            except Exception:
                pass

        return _wt_ja_relief_orig_apply_seed_move_20260607(
            state,
            row,
            col,
            letter,
            advance_market_flag=advance_market_flag,
        )

except Exception:
    pass


# ---- 3) one-time swap during stuck state ------------------------------------

def swap_market_tile(state, letter=None):
    if not _wt_ja_relief_is_ja():
        raise ValueError("Swap is only available in Japanese mode")

    if not _wt_ja_relief_is_stuck(state):
        raise ValueError("Swap is only available when no current market tile can make a word")

    if getattr(state, "synergyState", None) and state.synergyState.get("_reliefSwapUsed"):
        raise ValueError("Swap already used this game")

    temp = deepcopy(state)
    temp.synergyState = dict(getattr(temp, "synergyState", {}) or {})

    active = _wt_ja_relief_clean_seq(getattr(temp, "marketLetters", []) or [], offset=0, allow_wild=True)
    preview = _wt_ja_relief_clean_seq(getattr(temp, "previewLetters", []) or [], existing=set(active), offset=7, allow_wild=False)

    target = _norm_letter(letter) if letter else ""
    replace_idx = None

    if target and target in active:
        replace_idx = active.index(target)

    if replace_idx is None:
        for i, l in enumerate(active):
            if l == "*" or not _wt_ja_relief_letter_playable(temp, l):
                replace_idx = i
                break

    if replace_idx is None:
        replace_idx = 0

    candidates = _wt_ja_relief_pity_candidates(temp, exclude=set(active), limit=8)
    if not candidates:
        raise ValueError("No swap candidate available")

    old_letter = active[replace_idx]
    active[replace_idx] = candidates[0]

    used = set(active)
    preview = [x for x in preview if x not in used and _wt_ja_relief_is_kana(x)]
    while len(preview) < 3:
        more = _wt_ja_relief_pity_candidates(temp, exclude=used | set(preview), limit=1)
        if more:
            preview.append(more[0])
        else:
            for c in _wt_ja_relief_pool():
                if c not in used and c not in preview:
                    preview.append(c)
                    break

    temp.marketLetters = active[:3]
    temp.previewLetters = preview[:3]
    temp.synergyState["_reliefSwapUsed"] = True

    player = temp.currentPlayer
    temp.currentPlayer = other_player(player)
    temp.turn += 1
    temp.consecutivePasses = 0
    temp.lastChangedCells = []
    temp.lastCapturedCells = []
    temp.lastFortifiedCells = []
    temp.lastComboLabels = ["RELIEF SWAP"]

    try:
        item = MoveHistoryItem(
            turn=state.turn,
            player=player,
            word=f"SWAP {old_letter}->{active[replace_idx]}",
            moveType="SWAP",
            placedRow=None,
            placedCol=None,
            placedLetter=active[replace_idx],
            path=[],
            comboLabels=["RELIEF SWAP"],
            redTotalAfter=total_score(temp, "RED"),
            blueTotalAfter=total_score(temp, "BLUE"),
        )
        temp.moveHistory.append(item)
    except Exception:
        pass

    temp.recentMoves = [f"{player}: SWAP {old_letter}->{active[replace_idx]}"] + list(getattr(temp, "recentMoves", []) or [])[:4]

    return temp

'''

engine_text = engine_text.rstrip() + "\n\n" + engine_patch + "\n"
engine.write_text(engine_text, encoding="utf-8")

# ============================================================
# backend/main.py
# ============================================================

main_text = main.read_text(encoding="utf-8")

if "swap_market_tile" not in main_text:
    main_text = re.sub(
        r"(validate_and_apply_move,\s*)(\))",
        r"\1swap_market_tile, \2",
        main_text,
        count=1,
    )

endpoint_marker = "# WT_JA_RELIEF_SWAP_ENDPOINT_20260607"
if endpoint_marker not in main_text:
    endpoint = r'''

# WT_JA_RELIEF_SWAP_ENDPOINT_20260607
@app.post("/games/{game_id}/swap-letter")
def swap_letter(game_id: str, req: dict = {}):
    """One-time relief swap. Only allowed when the current market has no playable word."""
    state = GAMES.get(game_id)
    if not state:
        raise HTTPException(status_code=404, detail="Game not found")
    try:
        next_state = swap_market_tile(state, req.get("letter", ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    GAMES[game_id] = next_state
    return _state_response(next_state)
'''
    anchor = "# ── Almost / Tenpai endpoint"
    if anchor in main_text:
        main_text = main_text.replace(anchor, endpoint + "\n" + anchor, 1)
    else:
        main_text += "\n" + endpoint + "\n"

main.write_text(main_text, encoding="utf-8")

# ============================================================
# frontend/lib/api.js
# ============================================================

if api.exists():
    api_text = api.read_text(encoding="utf-8")

    if "swapLetter" not in api_text:
        insert = (
            'export async function swapLetter(gameId, letter=""){'
            'return request(`/games/${gameId}/swap-letter`,{method:"POST",body:JSON.stringify({letter})});'
            '} '
        )
        if "export async function getThreat" in api_text:
            api_text = api_text.replace("export async function getThreat", insert + "export async function getThreat", 1)
        else:
            api_text += "\n" + insert + "\n"

    api.write_text(api_text, encoding="utf-8")

# ============================================================
# frontend/pages/index.js — optional Swap button exposure
# ============================================================

if index.exists():
    idx = index.read_text(encoding="utf-8")

    if "swapLetter" not in idx:
        idx = idx.replace("useFreeLetter,", "useFreeLetter, swapLetter,", 1)

    if "async function swapRelief" not in idx:
        swap_fn = r'''
async function swapRelief() {
  try {
    const next = await swapLetter(gameId, letter || "");
    setState(next);
    if (next.marketLetters?.length > 0) {
      setMarket(m => ({...m, active:next.marketLetters, preview:next.previewLetters||[], freeLetterUsed:next.freeLetterUsed||false}));
    }
    reset();
    await refresh();
    getAlmost(gameId).then(setAlmost).catch(()=>{});
  } catch(e) {
    if (await recoverIfGameGone(e)) return;
    setError(normalizeStringError(e, "交換は、作れる単語がない時だけ使えます。"));
  }
}
'''
        if "async function submitScore" in idx:
            idx = idx.replace("async function submitScore", swap_fn + "\nasync function submitScore", 1)
        else:
            idx += "\n" + swap_fn + "\n"

    if "swapRelief" in idx and "詰み交換" not in idx:
        swap_btn = '<button className="ba" onClick={swapRelief} disabled={!human()} title="作れる単語がない時だけ1回使えます">詰み交換</button>'
        if ">パス</button>" in idx:
            idx = idx.replace(">パス</button>", ">パス</button>" + swap_btn, 1)
        elif ">Pass</button>" in idx:
            idx = idx.replace(">Pass</button>", ">パス</button>" + swap_btn, 1)

    bad_tokens = [
        "get脅威",
        "normalize脅威",
        "wtJaTo脅威",
        "value.マス",
        "function Cell({ マス",
        'className="マス"',
        "{/* move controls */}}",
    ]
    for b in bad_tokens:
        if b in idx:
            raise SystemExit(f"frontendに危険な破損トークンがあります: {b}")

    index.write_text(idx, encoding="utf-8")

# ============================================================
# verification
# ============================================================

engine_now = engine.read_text(encoding="utf-8")
main_now = main.read_text(encoding="utf-8")
api_now = api.read_text(encoding="utf-8") if api.exists() else ""
index_now = index.read_text(encoding="utf-8") if index.exists() else ""

checks = {
    "ENGINE_MARKER": "WT_JA_RELIEF_RARITY_PITY_WILD_20260607" in engine_now,
    "RARITY_SCORE": "_wt_ja_rarity_bonus_20260607" in engine_now and "_wt_ja_relief_orig_word_score_20260607" in engine_now,
    "PITY_MARKET": "_wt_ja_relief_apply_to_market_pair" in engine_now,
    "FREE_SEED": "RELIEF SEED" in engine_now,
    "SWAP_ENGINE": "def swap_market_tile" in engine_now,
    "WILD_LOGIC": 'active[-1] = "*"' in engine_now,
    "MAIN_SWAP_ENDPOINT": "/games/{game_id}/swap-letter" in main_now,
    "API_SWAP": "swapLetter" in api_now,
    "NO_BAD_IDENTIFIER": "get脅威" not in index_now,
    "NO_EXTRA_JSX_BRACE": "{/* move controls */}}" not in index_now,
}

print("VERIFY relief / rarity / pity / wild patch")
for k, v in checks.items():
    print(k, "=", v)

if not all(checks.values()):
    raise SystemExit("Patch verification failed. 上の False を貼ってください。")

# Syntax check backend files
subprocess.run([sys.executable, "-m", "py_compile", str(engine), str(main)], check=True)

print("DONE: relief / rarity / pity / wild patch applied")
