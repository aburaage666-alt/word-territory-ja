# JP_V28_FULL_ENGINE_CLEAN_V18_RELEASE
# JP_PROTOTYPE_V1_SAFE_FOLDER
# JP_PROTOTYPE_V2_SEED_REDUCTION
# JP_PROTOTYPE_V3_BOT_VALID_DICTIONARY
# JP_PROTOTYPE_V4_SWING_DAMPING
# JP_PROTOTYPE_V5_COMEBACK_ONLY_SCORING
# JP_PROTOTYPE_V8_V5_PLUS_FORTIFIER_LOCK_ONLY_NO_HARD_EXCLUDE
# JP_PROTOTYPE_V10_DICTIONARY_1300
# JP_PROTOTYPE_V11_LARGE_DICT_BALANCE
# JP_PROTOTYPE_V14_BLUE_DEFENDER_ATTACK_FORTIFIER_CONNECT
# JP_PROTOTYPE_V16_DICT_BUILDER_OPENING_TUNE
# JP_PROTOTYPE_V17_DICTIONARY_FULL_MONO_FIX
# JP_PROTOTYPE_V18_LENGTH_CURVE_BORDER_FIX
import random
from collections import deque
from copy import deepcopy

from dictionary import get_words, get_ui_words, get_demo_words, is_valid_word, normalize_word, is_ui_word as dict_is_ui_word, is_demo_word as dict_is_demo_word
import os as _os
_LANG = _os.environ.get('WT_LANG', 'en').lower()
if _LANG == 'ja':
    from language_profiles import ja as _LANG_PROFILE
else:
    _LANG_PROFILE = None
from models import Cell, Coord, GameState, MoveHistoryItem, PreviewMoveResponse, Scores

BOARD_SIZE = getattr(_LANG_PROFILE, 'BOARD_SIZE', 7) if _LANG == 'ja' else 7
MAX_TURNS = 35
_WORD_MIN = getattr(_LANG_PROFILE, 'MIN_WORD_LEN', 3) if _LANG == 'ja' else 3
_WORD_MAX = getattr(_LANG_PROFILE, 'MAX_WORD_LEN', 6) if _LANG == 'ja' else 6
_FT_MIN_PATH = getattr(_LANG_PROFILE, 'FRONTLINE_MIN_PATH_LEN', 3) if _LANG == 'ja' else 3

OPENINGS = [
    ("STONE OPENING", ["T", "A", "O", "E", "R", "N", "S"]),
    ("RIVER OPENING", ["R", "A", "E", "T", "L", "N", "S"]),
    ("BRIDGE OPENING", ["B", "R", "I", "D", "G", "E", "S"]),
    ("LIGHT OPENING", ["L", "I", "G", "H", "T", "E", "R"]),
    ("WATER OPENING", ["W", "A", "T", "E", "R", "S", "N"]),
    ("PLANT OPENING", ["P", "L", "A", "N", "T", "E", "R"]),
    ("GARDEN OPENING", ["S", "E", "A", "T", "R", "N", "L"]),
    ("FOREST OPENING", ["M", "E", "A", "T", "R", "S", "N"]),
    ("MARKET OPENING", ["C", "A", "R", "E", "T", "N", "S"]),
    ("CIRCLE OPENING", ["S", "T", "O", "N", "E", "R", "A"]),
]


JP_OPENINGS = getattr(_LANG_PROFILE, "JP_OPENINGS", []) if _LANG == "ja" else []

# 7x7 center=(3,3): shape top(1,3), row2(2,2-5), col(3-4,3)
OPENING_COORDS = [(1, 3), (2, 2), (2, 3), (2, 4), (2, 5), (3, 3), (4, 3)]




def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE


def get_neighbors(r: int, c: int):
    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        nr, nc = r + dr, c + dc
        if in_bounds(nr, nc):
            yield nr, nc


def other_player(player: str) -> str:
    return "BLUE" if player == "RED" else "RED"


def are_adjacent(a, b) -> bool:
    return abs(a.row - b.row) + abs(a.col - b.col) == 1



def _norm_word(w: str) -> str:
    return normalize_word(w)

def _norm_letter(ch: str) -> str:
    w = _norm_word(str(ch or "")[:1])
    return w[:1] if w else ""

def _market_letters() -> list[str]:
    if _LANG == "ja":
        return list(getattr(_LANG_PROFILE, "ALL_KANA", []))
    import string
    return list(string.ascii_uppercase)

def word_score(word: str) -> int:
    n = len(_norm_word(word))
    if _LANG == "ja":
        if n == 2:
            return 1
        if n == 3:
            return 2
        if n == 4:
            return 4
        if n >= 5:
            return 7
        return 0
    if n == 3:
        return 1
    if n == 4:
        return 2
    if n == 5:
        return 3
    if n == 6:
        return 5
    return 0


def clone_state(state: GameState) -> GameState:
    return deepcopy(state)


def total_score(state: GameState, player: str) -> float:
    if player == "RED":
        return state.scores.redTerritory * 1.5 + state.scores.redWord
    return state.scores.blueTerritory * 1.5 + state.scores.blueWord


def count_territory(state: GameState, player: str) -> int:
    return sum(1 for row in state.board for cell in row if cell.owner == player)


def count_locked_cells(state: GameState, player: str) -> int:
    return sum(1 for row in state.board for cell in row if cell.owner == player and cell.fortified)


def choose_opening():
    openings = JP_OPENINGS if _LANG == "ja" else OPENINGS
    candidates = openings[:]
    random.shuffle(candidates)
    best = candidates[0]
    best_score = -1
    words = get_words()
    for name, seed in candidates:
        available = set(seed)
        if _LANG == "ja":
            score = sum(1 for w in words if _WORD_MIN <= len(w) <= min(_WORD_MAX, 4) and all(ch in available for ch in w))
        else:
            score = sum(1 for w in words if 3 <= len(w) <= 4 and all(ch in available for ch in w))
        if score >= 3:
            return name, seed
        if score > best_score:
            best_score = score
            best = (name, seed)
    return best


BOT_STYLES = ["Builder", "Raider", "Defender"] if _LANG == "ja" else ["Builder", "Raider", "Cutter", "Expander", "Defender"]

def choose_bot_style(bot_level: str = "easy") -> str:
    """Pick a visible bot personality for the match.

    This is primarily a UX/positioning layer: it makes the opponent feel like
    a territory strategist rather than a generic word AI. The current move
    engine remains conservative; future versions can weight decisions by style.
    """
    if bot_level == "strong":
        return random.choice(["Raider", "Builder", "Defender"] if _LANG == "ja" else ["Raider", "Cutter", "Builder"])
    return random.choice(BOT_STYLES)


def build_initial_state(bot_level: str = "easy", opening_idx: int | None = None) -> GameState:
    board = [[Cell(row=r, col=c) for c in range(BOARD_SIZE)] for r in range(BOARD_SIZE)]
    openings = JP_OPENINGS if _LANG == 'ja' else OPENINGS
    if opening_idx is not None:
        opening_name, seed = openings[opening_idx % len(openings)]
    else:
        opening_name, seed = choose_opening()
    for (r, c), ch in zip(OPENING_COORDS, seed):
        board[r][c].letter = ch
    state = GameState(
        boardSize=BOARD_SIZE,
        board=board,
        currentPlayer="RED",
        turn=1,
        usedWords=[],
        recentMoves=[],
        moveHistory=[],
        scores=Scores(),
        winner=None,
        consecutivePasses=0,
        vsBot=True,
        botPlayer="BLUE",
        botLevel=bot_level,
        botStyle=choose_bot_style(bot_level),
        openingName=opening_name,
        lastChangedCells=[],
        lastCapturedCells=[],
        lastFortifiedCells=[],
        lastComboLabels=[],
    )
    # Initialize Synergy Card options (3 random cards to choose from)
    state.synergyOptions = pick_synergy_options()
    state.selectedSynergy = ""
    state.synergyState = {}
    # Initialize Letter Market
    active, preview = generate_letter_market(state)
    state.marketLetters  = active
    state.previewLetters = preview
    return state


def board_letters_set(state: GameState) -> set[str]:
    return {_norm_word(cell.letter) for row in state.board for cell in row if cell.letter}


def can_spell_from_board(word: str, available_letters: set[str]) -> bool:
    return all(ch in available_letters for ch in word)


def find_almost_words(state: GameState, limit: int = 5) -> list[dict]:
    """
    Tenpai / Almost UI: find words that are playable if ONE specific letter
    were available — i.e., words reachable from current board + any single new tile.

    Returns list of {"word": str, "needs": str, "length": int}
    sorted by length desc (longer = more exciting).
    """
    words = get_words()
    excluded = set(state.usedWords)
    board_letters = board_letters_set(state)
    placeable = get_placeable_empty_cells(state)

    results = []
    seen_words = set()

    # For each placeable cell, try every letter A-Z
    import string
    for (er, ec) in placeable[:8]:  # limit cells for speed
        for needed_letter in string.ascii_uppercase:
            # Skip if this letter is already on the board (not "almost")
            if needed_letter in board_letters:
                continue
            # Try paths from this cell with this letter
            starts = [(er, ec)]
            for nr, nc in get_neighbors(er, ec):
                if state.board[nr][nc].letter:
                    starts.append((nr, nc))

            for start in starts[:3]:
                stack = [([start], frozenset([start]))]
                while stack:
                    path, visited = stack.pop()
                    plen = len(path)
                    if plen >= 3 and (er, ec) in set(path):
                        word = letters_from_path(state, path, (er, ec), needed_letter)
                        if (word and word in words and word not in excluded
                                and word not in seen_words and _is_ui_word(word)):
                            seen_words.add(word)
                            results.append({
                                "word": word,
                                "needs": needed_letter,
                                "length": len(word),
                            })
                            if len(results) >= limit * 3:
                                # Sort and return early
                                results.sort(key=lambda x: -x["length"])
                                return results[:limit]
                    if plen >= 4:
                        continue
                    r, c = path[-1]
                    for nr, nc in get_neighbors(r, c):
                        if (nr, nc) in visited:
                            continue
                        if (nr, nc) != (er, ec) and not state.board[nr][nc].letter:
                            continue
                        stack.append((path + [(nr, nc)], visited | {(nr, nc)}))

    results.sort(key=lambda x: -x["length"])
    return results[:limit]


# Words to exclude from player-facing hints and bot preference.
# Important: these are NOT removed from the dictionary/validator.
# A player can still manually play them, but Suggested / Almost / Bot / Preview
# avoid surfacing abbreviations, proper-looking forms, archaic/obscure entries,
# or words that make the demo feel like a dictionary exploit.
_SUGGESTED_EXCLUDE = frozenset({
    # abbreviations / units / acronyms
    'MPH','ETC','LIB','TBSP','TSP','HRS','HR','MIN','SEC','USD','GBP','EUR',
    'DNA','RNA','CPU','GPU','USB','URL','HTML','HTTP','CEO','CFO','MBA','PHD',
    # Greek letters / particles / crosswordese
    'PHI','PSI','ETA','TAO','OCA','EFT','OFT','ERE','EKE','KOI','POI',
    # interjections / odd short entries
    'OOH','AAH','HMM','UGH','PST','SHH',
    # obscure / proper-looking / weak demo words observed in tests
    'HES','MAS','EST','SIM','IDES','ODES','JUT','ZIT','GOB','DOIT','NARC','OTIC','ALEC',
    'VAR','FARO','TARO','GEN','TOSH','LENO','BIFF','GLIB',
    # very technical / weak bot choices
    'ION','IONA','ERG','OHM','EMU','OVA','AXE',
    # UI/preview/bot filter: abbreviations, dictionary noise, obscure variants
    'MPH','ETC','LIB','GLIB','BIFF','ASAP','PICA','OMER','CADE','CIS','BABA','UREA','VAR','FARO','TARO','GEN','TOSH','LENO',
    'CPU','GPU','USB','PDF','PNG','JPG','GIF','API','CSS','HTML','HTTP','URL',
    'CEO','CFO','COO','LLC','LTD','INC','MBA','PHD','DNA','RNA','ATM','FAQ',
    'TBSP','TSP','OZ','LBS','KG','KM','CM','MM','MPG','BTW','FYI','DIY','VPN',
    'SQL','XML','JSON','YAML','SDK','CLI','GUI','UX','UI','AI','ML','NLP',

})


def _is_ui_word(word: str) -> bool:
    """Return True for words suitable for UI hints / bot-first choices."""
    if _LANG == "ja":
        return dict_is_ui_word(word)
    w = word.upper().strip()
    if w in _SUGGESTED_EXCLUDE:
        return False
    if len(w) < _WORD_MIN or len(w) > _WORD_MAX:
        return False
    vowels = sum(1 for ch in w if ch in 'AEIOU')
    if vowels == 0:
        return False
    if len(w) == 3 and vowels <= 1 and (w.endswith('H') or w.endswith('C') or w.endswith('B')):
        return False
    if len(w) <= 4 and w.endswith('S') and w[:-1] in _SUGGESTED_EXCLUDE:
        return False
    if len(w) <= 4 and any(ch in w for ch in 'QXZJ') and w not in {'JAM','JAR','JAW','JOG','JOY','JOKE','JUMP','QUIZ','ZERO','ZOO','AXE','FOX'}:
        return False
    return True


# Demo Dictionary: stricter than UI hints.
# Watch Demo / Trailer / Spectator showcase uses this list so the demo never
# feels like a dictionary exploit. The full Valid Dictionary remains available
# for manual play, and UI Dictionary remains broader for Suggested / Almost.
_DEMO_WORDS = frozenset(('STONE', 'WATER', 'PLANT', 'BRIDGE', 'TRAIN', 'LIGHT', 'RIVER', 'GARDEN', 'HOPE', 'FIRE', 'LINE', 'FIELD', 'ROAD', 'GATE', 'STAR', 'ROPE', 'BONE', 'TONE', 'ROSE', 'CONE', 'TREE', 'ROOT', 'LEAF', 'HOUSE', 'HOME', 'WALL', 'PATH', 'TRAIL', 'LAND', 'LAKE', 'RAIN', 'CLOUD', 'SUN', 'MOON', 'NIGHT', 'DAY', 'WIND', 'HILL', 'VALLEY', 'FOREST', 'MARKET', 'CIRCLE', 'CART', 'CARE', 'RATE', 'TEAR', 'NEAR', 'EARN', 'EAST', 'WEST', 'NORTH', 'SOUTH', 'HAND', 'HARD', 'RING', 'WING', 'KING', 'SING', 'FIND', 'FINE', 'MIND', 'MINE', 'KIND', 'LINK', 'SAND', 'BIRD', 'FISH', 'BOAT', 'PORT', 'SHIP', 'ROCK', 'IRON', 'WOOD', 'GOLD', 'SILVER', 'GREEN', 'BLUE', 'RED', 'BLACK', 'WHITE', 'CLEAR', 'BRIGHT', 'SMART', 'QUICK', 'SLOW', 'FAST', 'OPEN', 'CLOSE', 'COVER', 'BUILD', 'BREAK', 'CLAIM', 'CROSS', 'BLOCK', 'LOCK', 'SAFE', 'GUARD', 'POWER', 'SHARE', 'PLACE', 'SPACE', 'MAP', 'WORD', 'GAME', 'MOVE', 'TURN', 'SCORE', 'ROUND', 'BATTLE', 'BRICK', 'TRACK', 'TRUCK', 'PLANE', 'GRASS', 'SEED', 'BLOOM', 'FRUIT', 'WHEAT'))
_DEMO_WORD_EXCLUDE = frozenset({
    'IRE','DISC','WREN','WRET','THUS','CHUB','HULK','HULL','GLIB','BIFF',
    'MPH','ETC','LIB','TBSP','TSP','VAR','FARO','TARO','GEN','TOSH','LENO',
})


# JP V3: Bot dictionary is intentionally broader than UI/Demo.
# UI hints and Watch Demo stay clean; the bot needs enough valid words to avoid Seed spam.
_JP_BOT_HARD_EXCLUDE = frozenset({
    "きちく",
    "わたしかち",
    "かわさき",
    "たなか",
    "なりた",
    "ふじさん",
    "いもう",
    "いきち",
    "かみず",
    "こなみ",
    "やさか",
    "はびら",
    "ほそみ",
    "さかみ",
    "しやくし",
    "ひのでや",
    "ももたろ",
    "よそお",
    "なぎさた",
    "あめば",
    "あめも",
    "あめや",
    "うみば",
    "うみも",
    "うみや",
    "かきも",
    "かぜば",
    "かぜも",
    "かぜや",
    "かわば",
    "かわも",
    "かわや",
    "さかなば",
    "さとば",
    "さとも",
    "さとや",
    "すしば",
    "そばば",
    "そらば",
    "そらも",
    "そらや",
    "たべも",
    "のみも",
    "はなも",
    "ほしば",
    "ほしも",
    "ほしや",
    "まちば",
    "まちも",
    "まちや",
    "みずば",
    "みずも",
    "みずや",
    "もちば",
    "もりば",
    "もりも",
    "もりや",
    "やきも",
    "やまば",
    "やまも",
    "やまや",
    "ゆきば",
    "ゆきも",
    "ゆきや",
    "よみも",
})

def _is_bot_word(word: str) -> bool:
    """Return True if a word is usable by the bot.

    EN keeps the old UI filter to avoid dictionary debris.
    JA uses the Valid dictionary, not the narrow UI dictionary, because JP v2
    showed that applying UI filtering to bot search caused Seed collapse.
    """
    w = _norm_word(word)
    if not w:
        return False
    if _LANG == "ja":
        if w in _JP_BOT_HARD_EXCLUDE:
            return False
        if len(w) < _WORD_MIN or len(w) > _WORD_MAX:
            return False
        return is_valid_word(w)
    return _is_ui_word(w)


def _is_demo_word(word: str) -> bool:
    if _LANG == "ja":
        return dict_is_demo_word(word)
    w = word.upper().strip()
    if w in _DEMO_WORD_EXCLUDE:
        return False
    return w in _DEMO_WORDS and _is_ui_word(w)


# ── Letter Market ─────────────────────────────────────────────────────────────

# English letter frequency (rough weights)
_LETTER_WEIGHTS = {
    'E':12,'T':9,'A':8,'O':8,'I':7,'N':7,'S':6,'H':6,'R':6,'D':4,'L':4,
    'C':3,'U':3,'M':2,'W':2,'F':2,'G':2,'Y':2,'P':2,'B':2,'V':1,'K':1,
    'J':1,'X':1,'Q':1,'Z':1,
}
_ALL_LETTERS = list(_LETTER_WEIGHTS.keys())
_WEIGHTS     = [_LETTER_WEIGHTS[l] for l in _ALL_LETTERS]
if _LANG == 'ja':
    _LETTER_WEIGHTS = dict(getattr(_LANG_PROFILE, 'KANA_WEIGHTS', {}))
    _ALL_LETTERS = list(getattr(_LANG_PROFILE, 'ALL_KANA', []))
    _WEIGHTS = [getattr(_LANG_PROFILE, 'KANA_WEIGHTS', {}).get(l, 1) for l in _ALL_LETTERS]


# ── Synergy Card Definitions ──────────────────────────────────────────────────

SYNERGY_CARDS = {
    # V6 retired: BRIDGE_MASTER no longer grants bonus territory; BRIDGE remains a core combo.
    "FORTIFIER": {
        "name": "守り固め",
        "icon": "🏰",
        "difficulty": "やさしい",
        "effect": "最初の固定が強力。以後の固定も領地変動を加える。",
        "tip": "広げる前に、囲んだ領地を固める。",
        "flavor": "守り切る壁が勝ちを呼ぶ。",
    },
    # V13 retired: CUT_SPECIALIST created high variance/outlier games. CUT remains a combo label only.
    # V10 retired: Frontline now appears only as combo label FRONTLINE PRESSURE; no +T bonus.
    "ENCIRCLER": {
        "name": "包囲者",
        "icon": "🕸️",
        "difficulty": "むずかしい",
        "effect": "包囲を強める手は領地+3。",
        "tip": "相手の周囲を狭めて包囲する。",
        "flavor": "領地は奪取の前に罠になる。",
    },
    "BORDER_LORD": {
        "name": "中央支配",
        "icon": "🏴",
        "difficulty": "やさしい",
        "effect": "中央6×6の戦場で作った単語は領地+1。",
        "tip": "中央を制し、相手を外側へ追い出す。",
        "flavor": "中央が前線を決める。",
    },
    # V10 retired: Trap Setter was unreliable in Bot tests; no +T bonus.
    # V6 retired: SHORT_TACTICIAN repeatedly produced score-gap outliers in Bot tests.
    # Old saved games with selectedSynergy="SHORT_TACTICIAN" are handled as no-bonus legacy states.
    "COMEBACK_SPARK": {
        "name": "逆転の火花",
        "icon": "🔥",
        "difficulty": "ふつう",
        "effect": "6マス以上劣勢のとき、役ボーナスに領地変動を追加。",
        "tip": "劣勢の圧力を逆転の一手に変える。",
        "flavor": "圧力が領地を生む。",
    },
}

if _LANG == "ja":
    # PHASE4_JA_ROTATION_CARD_TEXT_V1
    if "ROTATION_RAIDER" in SYNERGY_CARDS:
        SYNERGY_CARDS["ROTATION_RAIDER"].update({"name": "回転侵略者", "difficulty": "むずかしい", "effect": "1試合に1回、敵地を含む2×2の文字だけを回転。所有権は動かない。", "tip": "回転後の語で打ち込みを狙う。ロック済みマスは対象外。", "flavor": "文字の地形を回して、敵陣に穴を開ける。"})

if _LANG == "ja":
    # PHASE3_JA_SYNERGY_TEXT_V1
    _JP_SYNERGY_TEXT = {
        "FORTIFIER": {"name": "要塞家", "difficulty": "やさしい", "effect": "最初のロックを強化。以後のロックも領地変動を生む。", "tip": "囲った地面を固めてから広げよう。", "flavor": "守れる壁が勝つ。"},
        "ENCIRCLER": {"name": "包囲家", "difficulty": "むずかしい", "effect": "包囲網を締める手は +3T。", "tip": "敵マスの周囲を閉じよう。", "flavor": "領地は、捕獲の前に罠になる。"},
        "BORDER_LORD": {"name": "国境領主", "difficulty": "やさしい", "effect": "中央6×6の戦場で作る語は +1T。", "tip": "中央を支配して相手を外へ押し出そう。", "flavor": "中央が前線を決める。"},
        "COMEBACK_SPARK": {"name": "逆転の火花", "difficulty": "ふつう", "effect": "6マス以上負けている時、役ボーナスが強化される。", "tip": "苦しい局面を反転の一手に変えよう。", "flavor": "圧力は領地を生む。"},
    }
    for _k, _v in _JP_SYNERGY_TEXT.items():
        if _k in SYNERGY_CARDS:
            SYNERGY_CARDS[_k].update(_v)


def pick_synergy_options() -> list[str]:
    """Pick synergy cards. JP prototype keeps V23 active 3 only."""
    if _LANG == 'ja':
        return ['BORDER_LORD', 'FORTIFIER', 'COMEBACK_SPARK']
    import random as _r
    active = ['BORDER_LORD', 'FORTIFIER', 'COMEBACK_SPARK']
    return active[:]


def _coord_tuple(p):
    """Safely normalize Coord / dict / tuple into (row, col).

    Important: do not use getattr(..., p.get(...)) because Python evaluates
    the default argument before calling getattr. That crashes for Coord objects
    with: 'Coord' object has no attribute 'get'.
    """
    if isinstance(p, tuple):
        return p
    if hasattr(p, 'row') and hasattr(p, 'col'):
        return (p.row, p.col)
    if isinstance(p, dict):
        return (p.get('row'), p.get('col'))
    # Fallback for other mapping-like objects
    try:
        return (p['row'], p['col'])
    except Exception:
        raise ValueError(f"Invalid coordinate object: {p!r}")


def _path_touches_enemy(state: GameState, path, player: str) -> bool:
    opponent = other_player(player)
    if not path:
        return False
    for p in path:
        r, c = _coord_tuple(p)
        for nr, nc in get_neighbors(r, c):
            if state.board[nr][nc].owner == opponent:
                return True
    return False


def _path_in_center_zone(path) -> bool:
    if not path:
        return False
    for p in path:
        r, c = _coord_tuple(p)
        # central 6x6 on a 7x7 board: avoid only the far outer corner pressure
        if 0 <= r <= 5 and 0 <= c <= 5:
            return True
    return False


def _capture_net_pressure(state: GameState, row: int | None, col: int | None, player: str) -> bool:
    """Cheap proxy for 'created a capture threat': placed near ≥2 enemy cells or closes a small pocket."""
    if row is None or col is None:
        return False
    opponent = other_player(player)
    adj_enemy = 0
    adj_empty = 0
    for nr, nc in get_neighbors(row, col):
        if state.board[nr][nc].owner == opponent:
            adj_enemy += 1
        if state.board[nr][nc].letter is None:
            adj_empty += 1
    return adj_enemy >= 2 or (adj_enemy >= 1 and adj_empty <= 1)


# BALANCE_PATCH_V3_COMBO_SYNERGY
# BALANCE_PATCH_V4_SECOND_CAPTURE_FORTIFIER
# BALANCE_PATCH_V5_LOCK_SHORT_ENCIRCLE
# BALANCE_PATCH_V6_NO_SHORT_BRIDGEBONUS
# BALANCE_PATCH_V10_V6BASE_NO_FRONTLINE
# BALANCE_PATCH_V11_NO_ENCIRCLER_BONUS
# BALANCE_PATCH_V13_V11BASE_CUT_DRAW
# BALANCE_PATCH_V14_LEAD_LIMIT_BORDER_FORTIFIER
# BALANCE_PATCH_V16_RIVER_OUTLIER_GUARD
# BALANCE_PATCH_V17_ALLCARDS_TEST_SUITE
# BALANCE_PATCH_V18_ACTIVE3_INTENTIONAL_RETIRED
# BALANCE_PATCH_V19_2PI2_BLUE_EXPANDER_BUILDER
# BALANCE_PATCH_V20_V19_RECURSION_FIX
# BALANCE_PATCH_V21_BORDER_LORD_UNDERDOG
# BALANCE_PATCH_V23_RELEASE_V21_LOCKED
# Synergy is separated from ordinary combo labels. COMEBACK / FORTIFY CHAIN
# remain map-combo labels; only labels prefixed with SYNERGY: are synergy activations.
_SYNERGY_CAPS = {
"FORTIFIER": 2,
"BORDER_LORD": 4,
"COMEBACK_SPARK": 3,
"LONG_WORD": 3,
    "VOWEL_ENGINE": 4,
    "SEED_TACTICIAN": 2,
    "PATH_SEEKER": 3,
}

def _synergy_count_key(card: str, player: str) -> str:
    return f"synCount:{card}:{player}"

def _synergy_can_activate(state: GameState, card: str, player: str) -> bool:
    if not card:
        return False
    ss = state.synergyState or {}

    # Early snowball control: no synergy acceleration in the opening.
    # The game still has combos, but build-card bonuses start after both sides
    # have had time to establish territory.
    try:
        if int(state.turn) <= 6 and card != "COMEBACK_SPARK":
            return False
    except Exception:
        pass

    cap = _SYNERGY_CAPS.get(card, 3)
    try:
        if int(ss.get(_synergy_count_key(card, player), 0)) >= cap:
            return False
    except Exception:
        return False

    # Prevent "same card every turn" behavior.
    try:
        if ss.get("lastSynergyCard") == card and int(ss.get("lastSynergyTurn", -999)) >= state.turn - 1:
            return False
    except Exception:
        pass
    return True

def _record_synergy_activation(ss: dict, card: str, player: str, turn: int) -> dict:
    ss = dict(ss or {})
    key = _synergy_count_key(card, player)
    ss[key] = int(ss.get(key, 0)) + 1
    ss["lastSynergyCard"] = card
    ss["lastSynergyPlayer"] = player
    ss["lastSynergyTurn"] = turn
    return ss

def _synergy_preview_text(state: GameState, combos: list[str], player: str,
                          word: str, letter: str, path=None, row: int | None = None,
                          col: int | None = None) -> str:
    card = state.selectedSynergy
    if card in _RETIRED_SCORE_NEUTRAL_SYNERGIES:
        return ""
    if not card or not _synergy_can_activate(state, card, player):
        return ""
    name = SYNERGY_CARDS.get(card, {}).get('name', 'Synergy')
    has_capture = "CAPTURE" in combos or "MAJOR CAPTURE" in combos
    has_bridge = "BRIDGE" in combos
    has_cut = "CUT" in combos
    opp = other_player(player)
    my_t = count_territory(state, player)
    opp_t = count_territory(state, opp)
    lead = my_t - opp_t

    # V6: Bridge Master no longer grants a separate synergy bonus.
    if card == "FORTIFIER" and lead < _active_card_lead_limit(player) and "FORTIFY CHAIN" in combos:
        return f"★ {name} ready"
    if card in ("CUT_HUNTER") and has_cut and (has_capture or has_bridge):
        return f"★ {name} ready"
    # V5: Encircler is now a comeback/control trigger, not a snowball trigger.
    if card == "BORDER_LORD" and my_t < opp_t and _path_in_center_zone(path):
        return f"★ {name} ready"
    if card == "COMEBACK_SPARK":
        if (opp_t - my_t) >= _comeback_gap_required(player):
            return f"★ {name} ready"
    # Legacy cards preserved for old saved games
    if card == "PATH_SEEKER" and "LONG PATH" in combos:
        return f"★ {name} ready"
    if card == "LONG_WORD" and len(word) >= 5:
        return f"★ {name} ready"
    if card == "VOWEL_ENGINE" and letter.upper() in "AEIOU":
        return f"★ {name} ready"
    if card == "SEED_TACTICIAN" and state.synergyState.get("seedPending"):
        return f"★ {name} ready"
    return ""


# V21: BORDER_LORD is now underdog-only; central control no longer rewards the leading side.
# V18 design decision:
# Retired cards are intentional score-neutral terrain/event labels.
# Only BORDER_LORD, FORTIFIER, and COMEBACK_SPARK remain active scoring Synergy cards.
_ACTIVE_SCORING_SYNERGIES = {"BORDER_LORD", "FORTIFIER", "COMEBACK_SPARK"}
_RETIRED_SCORE_NEUTRAL_SYNERGIES = {
    "SHORT_TACTICIAN",
    "BRIDGE_MASTER",
    "FRONTLINE_TACTICIAN",
    "TRAP_SETTER",
    "ENCIRCLER",
    "CUT_SPECIALIST",
    "CUT_HUNTER",
}

if _LANG == 'ja':
    SYNERGY_CARDS = {k: SYNERGY_CARDS[k] for k in ('BORDER_LORD', 'FORTIFIER', 'COMEBACK_SPARK')}


def _active_card_lead_limit(player: str) -> int:
    """Asymmetric cap to compensate first-player RED tempo.

    RED gets a stricter snowball stop; BLUE keeps the V14/V16 limit.
    """
    return 4 if player == "RED" else 6

def _comeback_gap_required(player: str) -> int:
    """RED has first-player tempo, so its comeback card needs a larger deficit."""
    return 8 if player == "RED" else 6

def apply_synergy_bonus(state: GameState, combos: list[str], player: str,
                        word: str, letter: str, path=None,
                        row: int | None = None, col: int | None = None,
                        territory_gain: int = 0,
                        lock_gain: int = 0) -> int:
    """Return extra territory from the active terrain-shaped synergy card.

    V5 balance:
    - locked cells are permanent ground
    - Short Tactician cannot create runaway leads
    - Encircler is a controlled pressure/comeback trigger
    """
    card = state.selectedSynergy

    # JP v18: BORDER_LORD must not be dead in Japanese.
    # It is no longer score-neutral, but JP activation is capped below.
    if card in _RETIRED_SCORE_NEUTRAL_SYNERGIES:
        return 0
    if not card or not _synergy_can_activate(state, card, player):
        return 0

    bonus = 0
    opp = other_player(player)
    my_t  = count_territory(state, player)
    opp_t = count_territory(state, opp)
    lead = my_t - opp_t
    has_capture = "CAPTURE" in combos or "MAJOR CAPTURE" in combos
    has_bridge = "BRIDGE" in combos
    has_cut = "CUT" in combos

    if card == "BRIDGE_MASTER" and has_bridge and (has_capture or territory_gain >= 4):
        bonus += 0  # V6: Bridge remains a combo, but Bridge Master no longer adds territory.
    elif card == "FORTIFIER":
        if _LANG == "ja":
            # JP v14: FORTIFIER is redefined for Japanese.
            # Because short-word LOCK creation is intentionally suppressed,
            # FORTIFIER rewards longer words that reconnect/anchor own territory.
            total = int(state.synergyState.get("jpFortifierTotal", 0) or 0)
            owned_cells_in_path = 0
            try:
                for p in (path or []):
                    rr, cc = _coord_tuple(p)
                    if state.board[rr][cc].owner == player:
                        owned_cells_in_path += 1
            except Exception:
                owned_cells_in_path = 0

            fortify_anchor = (len(_norm_word(word)) >= 4 and owned_cells_in_path >= 1)
            if total < 3 and lead < 4 and (lock_gain >= 1 or "FORTIFY CHAIN" in combos or fortify_anchor):
                bonus += 1
                state.synergyState["jpFortifierTotal"] = total + 1
        elif lead < _active_card_lead_limit(player) and (lock_gain > 0 or "FORTIFY CHAIN" in combos):
            bonus += 2 if not state.synergyState.get("firstLockDone") else 1
    elif card in ("CUT_HUNTER"):
        if has_cut and (has_capture or has_bridge or territory_gain >= 4):
            bonus += 1
    elif card == "BORDER_LORD" and my_t < opp_t and _path_in_center_zone(path):
        if _LANG == "ja":
            # JP v18: revive BORDER_LORD without returning to v12 runaway.
            # It can light up for the trailing player in the center, max twice/game.
            total = int(state.synergyState.get("jpBorderLordTotal", 0) or 0)
            if total < 2:
                bonus += 1
                state.synergyState["jpBorderLordTotal"] = total + 1
        else:
            bonus += 1
    elif card == "COMEBACK_SPARK" and (opp_t - my_t) >= _comeback_gap_required(player):
        bonus += min(2, max(1, len([c for c in combos if not str(c).startswith('SYNERGY')])))
    # legacy cards for saved games
    elif card == "LONG_WORD":
        bonus += 2 if len(word) == 5 else 3 if len(word) >= 6 else 0
    elif card == "VOWEL_ENGINE" and letter.upper() in "AEIOU":
        bonus += 1
    elif card == "SEED_TACTICIAN" and state.synergyState.get("seedPending"):
        bonus += 2
    elif card == "PATH_SEEKER" and "LONG PATH" in combos:
        bonus += 2
    return bonus

def synergy_activation_text(state: GameState, combos: list[str], player: str,
                            word: str, letter: str, bonus: int) -> str:
    """Human-readable terrain-style synergy activation message."""
    if bonus <= 0 or not state.selectedSynergy:
        return ""
    card = state.selectedSynergy
    name = SYNERGY_CARDS.get(card, {}).get('name', 'Synergy')
    if card == 'BRIDGE_MASTER':
        return f"{name}: 領地接続 +{bonus}T"
    if card == 'FORTIFIER':
        return f"{name}: 固定領地 +{bonus}T"
    if card in ('CUT_HUNTER'):
        return f"{name}: 分断成功 +{bonus}T"
    if card == 'FRONTLINE_TACTICIAN':
        return f"{name}: 前線押し上げ +{bonus}T"
    if card == 'ENCIRCLER':
        return f"{name}: 包囲強化 +{bonus}T"
    if card == 'BORDER_LORD':
        return f"{name}: 中央支配 +{bonus}T"
    if card == 'TRAP_SETTER':
        return f"{name}: 罠発動 +{bonus}T"
    if card == 'COMEBACK_SPARK':
        return f"{name}: 逆転圧力 +{bonus}T"
    if card == 'SHORT_TACTICIAN':
        return f"{name}: 短手の前線 +{bonus}T"
    return f"{name}発動 +{bonus}T"

def update_synergy_state(state: GameState, combos: list[str],
                         is_seed: bool = False) -> dict:
    """Update terrain-synergy state machine.

    Ordinary combos such as COMEBACK and FORTIFY CHAIN are not synergy triggers.
    Only SYNERGY: labels increment synergy counters.
    """
    ss = dict(state.synergyState or {})
    card = state.selectedSynergy
    actor = state.currentPlayer
    if not card:
        return ss

    if any(str(c).startswith("SYNERGY:") for c in combos):
        ss = _record_synergy_activation(ss, card, actor, state.turn)

    if card == "FORTIFIER" and ("FORTIFY CHAIN" in combos or any(str(c).startswith("SYNERGY:Fortifier") for c in combos)):
        ss["firstLockDone"] = True
    elif card in ("CUT_HUNTER"):
        if "CUT" in combos:
            ss["cutPending"] = True
            ss["cutPendingFor"] = actor
        elif "CAPTURE" in combos and ss.get("cutPendingFor") == actor:
            ss["cutPending"] = False
            ss.pop("cutPendingFor", None)
    elif card == "SEED_TACTICIAN":
        if is_seed:
            ss["seedPending"] = True
        else:
            ss["seedPending"] = False
    return ss

def _letter_enables_word(state: GameState, letter: str, max_check: int = 8) -> bool:
    """Quick check: does placing this letter anywhere create ≥1 valid word?"""
    words = get_words()
    placeable = get_placeable_empty_cells(state)
    import random as _r
    sample = placeable[:max_check]
    for (er, ec) in sample:
        # Try a fast path from each cell
        stack = [([p], frozenset([p])) for p in [(er,ec)] +
                 [(r,c) for r,c in get_neighbors(er,ec) if state.board[r][c].letter]]
        while stack:
            path, vis = stack.pop()
            if len(path) >= 3 and (er,ec) in set(path):
                w = letters_from_path(state, path, (er,ec), letter)
                if w and w in words:
                    return True
            if len(path) >= 4:
                continue
            r, c = path[-1]
            for nr, nc in get_neighbors(r, c):
                if (nr,nc) in vis: continue
                if (nr,nc) != (er,ec) and not state.board[nr][nc].letter: continue
                stack.append((path+[(nr,nc)], vis|{(nr,nc)}))
    return False



_ROLE_PRIORITY = {
    "WILD": 90,
    "CAPTURE": 80,
    "BRIDGE": 75,
    "LOCK": 70,
    "POWER": 60,
    "LONG": 50,
    "SAFE": 40,
    "SETUP": 10,
}

def _market_role_payload(role: str) -> dict:
    meta = {
        "WILD":    ("★", "Wild"),
        "CAPTURE": ("⚔️", "Capture"),
        "BRIDGE":  ("🌉", "Bridge"),
        "LOCK":    ("🔒", "Lock"),
        "POWER":   ("⚡", "Power"),
        "LONG":    ("➜", "Long"),
        "SAFE":    ("🛡", "Safe"),
        "SETUP":   ("✨", "Setup"),
    }
    icon, label = meta.get(role, meta["SETUP"])
    return {"bestRole": role, "roleIcon": icon, "roleLabel": label}

def _pick_best_role(roles: list[str], word_count: int, best_gain: int, best_word: str) -> str:
    normalized = []
    for r in roles or []:
        rr = str(r).upper()
        if "CAPTURE" in rr:
            normalized.append("CAPTURE")
        elif "BRIDGE" in rr:
            normalized.append("BRIDGE")
        elif "FORTIFY" in rr or "LOCK" in rr:
            normalized.append("LOCK")
        elif "LONG" in rr:
            normalized.append("LONG")
    if best_gain >= 5:
        normalized.append("POWER")
    if word_count >= 4:
        normalized.append("SAFE")
    if not normalized:
        normalized.append("SETUP")
    return max(normalized, key=lambda r: _ROLE_PRIORITY.get(r, 0))


def _letter_best_stats(state: GameState, letter: str) -> dict:
    """Return market stats plus a bestRole for one letter.

    For active market letters only, so simulating a few moves is acceptable.
    """
    if letter == "*":
        payload = {"wordCount": 0, "bestGain": 0, "bestWord": "", "roles": ["WILD"], "isWild": True}
        payload.update(_market_role_payload("WILD"))
        return payload

    excluded = set(state.usedWords)
    moves = _fast_bot_moves_for_letter(state, letter, max_results=10, excluded=excluded)
    if not moves:
        payload = {"wordCount": 0, "bestGain": 0, "bestWord": "", "roles": ["SETUP"]}
        payload.update(_market_role_payload("SETUP"))
        return payload

    best_word = ""
    best_gain = 0
    roles = []
    for m in moves:
        try:
            after = validate_and_apply_move(
                clone_state(state), m["row"], m["col"], m["letter"], m["path"],
                advance_market_flag=False
            )
            last = after.moveHistory[-1]
            best_gain = max(best_gain, last.territoryGained or 0)
            if (last.territoryGained or 0) >= best_gain:
                best_word = last.word
            for c in (last.comboLabels or []):
                cc = str(c)
                if cc.startswith("SYNERGY"):
                    continue
                if cc not in roles:
                    roles.append(cc)
            if (last.captureCount or 0) > 0 and "CAPTURE" not in roles:
                roles.append("CAPTURE")
            if (last.fortifiedCellsGained or 0) > 0 and "LOCK" not in roles:
                roles.append("LOCK")
        except Exception:
            gain = m.get("territory_gain", 0)
            if gain >= best_gain:
                best_gain = gain
                best_word = m.get("word", best_word)

    if not roles:
        if len(best_word) >= 5:
            roles.append("LONG PATH")
        elif len(moves) >= 4:
            roles.append("SAFE")
        else:
            roles.append("SETUP")

    best_role = _pick_best_role(roles, len(moves), best_gain, best_word)
    payload = {
        "wordCount": len(moves),
        "bestGain": best_gain,
        "bestWord": best_word,
        "roles": roles[:3],
        "isWild": False,
    }
    payload.update(_market_role_payload(best_role))
    return payload


def _fast_bot_moves_for_letter(state: GameState, letter: str,
                                max_results: int = 8,
                                excluded: set | None = None) -> list[dict]:
    """Like _fast_bot_moves but constrained to a specific letter."""
    excluded = excluded or set()
    words = get_words()
    placeable = get_placeable_empty_cells(state)
    results = []
    collect_cap = max_results * (12 if _LANG == "ja" else 8)

    for (er, ec) in placeable[:(10 if _LANG == "ja" else 8)]:
        stack = [([p], frozenset([p])) for p in [(er,ec)] +
                 [(r,c) for r,c in get_neighbors(er,ec) if state.board[r][c].letter]]
        while stack:
            path, vis = stack.pop()
            if len(path) >= 3 and (er,ec) in set(path):
                w = letters_from_path(state, path, (er,ec), letter)
                if w and w in words and w not in excluded and _is_ui_word(w):
                    gain = len(path)
                    results.append({"row": er, "col": ec, "letter": letter,
                                    "path": [Coord(row=r, col=c) for r,c in path],
                                    "word": w, "territory_gain": gain})
                    if len(results) >= collect_cap:
                        return sorted(results, key=_candidate_move_quality, reverse=True)[:max_results]
            if len(path) >= 5:
                continue
            r, c = path[-1]
            for nr, nc in get_neighbors(r,c):
                if (nr,nc) in vis:
                    continue
                if (nr,nc)!=(er,ec) and not state.board[nr][nc].letter:
                    continue
                stack.append((path+[(nr,nc)], vis|{(nr,nc)}))

    return sorted(results, key=_candidate_move_quality, reverse=True)[:max_results]

def _score_all_letters(state: GameState) -> dict:
    """
    Score candidate letters for the current board state.
    Only checks Almost-guided letters + top-weighted commons (not all 26).
    Fast: ~5-10ms per call.
    """
    import heapq as _hq
    excluded = set(state.usedWords)
    board_letters = board_letters_set(state)
    VOWELS = set("あいうえお") if _LANG == "ja" else set("AEIOU")

    # Candidate set: Almost letters + top 12 by frequency, minus board letters
    try:
        almost_letters = {a["needs"] for a in find_almost_words(state, limit=8)}
    except Exception:
        almost_letters = set()

    top_freq = sorted(
        [l for l in _ALL_LETTERS if l not in board_letters],
        key=lambda l: -_LETTER_WEIGHTS[l]
    )[:12]

    candidates = list((almost_letters | set(top_freq)) - board_letters)
    # Always include common vowels if not on board (EN only)
    if _LANG == 'en':
        for v in "AEIOU":
            if v not in board_letters and v not in candidates:
                candidates.append(v)

    scores = {}
    for letter in candidates:
        moves = _fast_bot_moves_for_letter(state, letter, max_results=6, excluded=excluded)
        best_gain = max((m.get("territory_gain", 0) for m in moves), default=0)
        best_word = max(moves, key=lambda m: m.get("territory_gain", 0),
                        default={}).get("word", "") if moves else ""
        power = any(len(m.get("word","")) >= 5 for m in moves)
        scores[letter] = {
            "words":     len(moves),
            "gain":      best_gain,
            "best_word": best_word,
            "power":     power,
            "is_vowel":  letter in VOWELS,
        }
    return scores



def _comeback_letter_candidates(state: GameState, exclude: set | None = None, limit: int = 6) -> list[str]:
    if _LANG == 'ja':
        exclude = exclude or set()
        board_letters = board_letters_set(state)
        letters = []
        try:
            for a in find_almost_words(state, limit=18):
                l = str(a.get('needs', ''))
                if l and l not in board_letters and l not in exclude:
                    letters.append(l)
        except Exception:
            pass
        for l in _ALL_LETTERS:
            if l not in board_letters and l not in exclude:
                letters.append(l)
        seen=[]
        for l in letters:
            if l not in seen:
                seen.append(l)
            if len(seen) >= limit:
                break
        return seen
    """Return letters that can create an actual comeback chance.

    Used only when the current player is behind. Preference:
    capture / bridge / synergy-capable moves > high territory swing > almost words.
    Rare letters are excluded because comeback should feel helpful, not cruel.
    """
    exclude = exclude or set()
    rare = {'Q', 'X', 'Z', 'J'}
    board_letters = board_letters_set(state)
    letters = []

    # Start from Almost needs because the UI already teaches this.
    try:
        for a in find_almost_words(state, limit=18):
            l = str(a.get("needs", "")).upper()
            if l and l not in board_letters and l not in rare and l not in exclude:
                letters.append(l)
    except Exception:
        pass

    # Add common high-frequency letters as backup.
    for l in "ETAOINSHRDLUCMFWYPGBVK":
        if l not in board_letters and l not in rare and l not in exclude:
            letters.append(l)

    seen, scored = set(), []
    for l in letters:
        if l in seen:
            continue
        seen.add(l)
        try:
            moves = _fast_bot_moves_for_letter(state, l, max_results=10, excluded=set(state.usedWords))
        except Exception:
            moves = []
        best = 0
        for m in moves:
            try:
                ns = simulate_move(state, m)
                last = ns.moveHistory[-1]
                labels = last.comboLabels or []
                val = 0
                val += last.territoryGained * 2
                val += last.captureCount * 10
                val += last.fortifiedCellsGained * 3
                val += 9 if "BRIDGE" in labels else 0
                val += 6 if "MAJOR CAPTURE" in labels else 0
                val += 6 if any(str(x).startswith("SYNERGY") for x in labels) else 0
                val += min(6, word_score(m.get("word", "")))
                best = max(best, val)
            except Exception:
                best = max(best, len(m.get("word", "")) if isinstance(m, dict) else 0)
        # Keep true Almost letters even if quick simulation is weak.
        if best == 0:
            best = 2
        scored.append((best, l))

    scored.sort(reverse=True)
    return [l for _, l in scored[:limit]]



def _apply_comeback_wild(state: GameState, active: list[str]) -> list[str]:
    """Convert rare letters to a WILD tile only while the current player is behind."""
    try:
        if state.freeLetterUsed:
            return active
        gap = get_score_gap(state, state.currentPlayer)
        if gap < 6:
            return active
        rare = {"Q", "X", "Z", "J"}
        out = list(active)
        for i, l in enumerate(out):
            if l in rare:
                out[i] = "*"
                return out
        return out
    except Exception:
        return active


def generate_letter_market(state: GameState) -> tuple[list[str], list[str]]:
    """
    3-slot Letter Market:
    - Slot 0 SAFE:  highest wordCount (reliable play)
    - Slot 1 POWER: highest territory gain / role potential
    - Slot 2 SETUP: Almost-guided or frequency-weighted

    Guarantees: ≥2 of 3 active letters have playable words.
    Preview: no duplicates, ≥1 vowel, no repeat from active.
    """
    import random as _r

    RARE  = {'Q','X','Z','J'} if _LANG == 'en' else set()
    VOWELS = set("あいうえお") if _LANG == "ja" else set("AEIOU")
    board_letters = board_letters_set(state)

    scores = _score_all_letters(state)
    playable = {l: s for l, s in scores.items() if s["words"] > 0}

    # Comeback bias: losing by 6+ → Almost-completing letters boosted
    try:
        gap = get_score_gap(state, state.currentPlayer)
        if gap >= 6:
            almost_cb = find_almost_words(state, limit=8)
            for a in almost_cb:
                l = a["needs"]
                if l not in board_letters and l not in playable:
                    playable[l] = {"words": 1, "gain": 3, "best_word": "", "power": False, "is_vowel": l in VOWELS}
                elif l in playable:
                    playable[l] = dict(playable[l])
                    playable[l]["gain"] = max(playable[l]["gain"], 4)
    except Exception:
        pass

    def pick(pool_dict, key_fn, exclude):
        candidates = [(l, s) for l, s in pool_dict.items() if l not in exclude]
        if not candidates:
            return None
        return max(candidates, key=lambda x: key_fn(x[1]))[0]

    def weighted_pick(exclude):
        pool = [l for l in _ALL_LETTERS
                if l not in board_letters and l not in RARE and l not in exclude]
        if not pool:
            pool = [l for l in _ALL_LETTERS if l not in exclude] or _ALL_LETTERS
        weights = [_LETTER_WEIGHTS[l] for l in pool]
        return _r.choices(pool, weights=weights)[0]

    used = set()
    active = []

    # Slot 0: SAFE — most playable words
    safe = pick(playable, lambda s: s["words"] * 2 + s["gain"], used)
    if safe:
        active.append(safe); used.add(safe)

    # Slot 1: POWER — highest gain, prefer Power Word / different from safe
    power = pick(playable, lambda s: s["gain"] * 3 + (4 if s["power"] else 0) + s["words"], used)
    if power:
        active.append(power); used.add(power)
    elif playable:
        # second-best playable
        p2 = pick(playable, lambda s: s["gain"] + s["words"], used)
        if p2:
            active.append(p2); used.add(p2)

    # Slot 2: SETUP — try 3rd playable first, then Almost-guided
    third_playable = pick(playable, lambda s: s["words"] + s["gain"], used)
    if third_playable:
        active.append(third_playable); used.add(third_playable)
    else:
        try:
            almost = find_almost_words(state, limit=10)
            setup_candidates = [a["needs"] for a in almost
                                if a["needs"] not in board_letters and a["needs"] not in used]
            if setup_candidates:
                active.append(setup_candidates[0]); used.add(setup_candidates[0])
            else:
                active.append(weighted_pick(used)); used.add(active[-1])
        except Exception:
            active.append(weighted_pick(used)); used.add(active[-1])

    # Fill any remaining slots
    while len(active) < 3:
        l = weighted_pick(used)
        active.append(l); used.add(l)

    # Late-game fallback: if board is dense (>70% filled) and no playable letters,
    # fill with best Almost-completing letters
    board_total = BOARD_SIZE * BOARD_SIZE
    filled = sum(1 for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if state.board[r][c].letter)
    if filled / board_total > 0.70 and all(l not in playable for l in active):
        try:
            almost_fb = find_almost_words(state, limit=12)
            for a in almost_fb:
                l = a["needs"]
                if l not in board_letters and l not in set(active):
                    active[-1] = l  # replace last slot
                    break
        except Exception:
            pass

    # Strong comeback intervention: when a human/player is losing badly,
    # one market tile must be a real comeback letter, not just a label.
    try:
        gap = get_score_gap(state, state.currentPlayer)
        if gap >= 6:
            cb_letters = _comeback_letter_candidates(state, exclude=set(), limit=6)
            if cb_letters:
                # Prefer replacing the weakest/rarest slot. Never keep J/Q/X/Z as a "comeback" tile.
                rare = {'Q', 'X', 'Z', 'J'}
                replace_idx = 0
                for i, l in enumerate(active):
                    if l in rare or l not in playable:
                        replace_idx = i
                        break
                chosen = next((l for l in cb_letters if l not in set(active)), cb_letters[0])
                active[replace_idx] = chosen
                used = set(active)
    except Exception:
        pass

    # Ensure at least 1 vowel in active 3
    if not any(l in VOWELS for l in active):
        # replace the weakest (last slot) with a vowel
        vowels_avail = [l for l in VOWELS if l not in board_letters and l not in used]
        if vowels_avail:
            active[-1] = _r.choice(vowels_avail)
            used = set(active)

    # Preview: no duplicates, no same as active, ≥1 vowel
    preview = []
    prev_seen = set(active)
    # Add 1 Almost letter for preview
    try:
        almost = find_almost_words(state, limit=6)
        for a in almost:
            l = a["needs"]
            if l not in board_letters and l not in prev_seen:
                preview.append(l); prev_seen.add(l); break
    except Exception:
        pass
    while len(preview) < 3:
        l = weighted_pick(prev_seen)
        preview.append(l); prev_seen.add(l)
    # Ensure ≥1 vowel in preview
    if not any(l in VOWELS for l in preview):
        vowels_avail = [l for l in VOWELS if l not in board_letters and l not in prev_seen - set(preview)]
        if vowels_avail:
            preview[-1] = _r.choice(vowels_avail)

    active = _apply_comeback_wild(state, active)
    return active[:3], preview[:3]


def advance_market(state: GameState, used_letter: str) -> tuple[list[str], list[str]]:
    """
    Remove used_letter from active, pull from preview, replenish.
    Always returns 3 active + 3 preview letters.
    """
    import random as _r
    RARE = {"Q","X","Z","J"} if _LANG == "en" else set()
    board_letters = board_letters_set(state)

    # Step 1: Remove used letter from active
    active = [l for l in state.marketLetters if l != used_letter]

    # Step 2: Pull from preview to fill active to 3
    preview = list(state.previewLetters) if state.previewLetters else []
    while len(active) < 3 and preview:
        active.append(preview.pop(0))

    # Step 3: If still short, use scored letters
    existing = set(active) | set(preview)
    if len(active) < 3:
        try:
            scores = _score_all_letters(state)
            ranked = sorted(
                [(l, s) for l, s in scores.items()
                 if s["words"] > 0 and l not in existing],
                key=lambda x: -(x[1]["gain"] + x[1]["words"])
            )
            for l, _ in ranked:
                if len(active) >= 3: break
                active.append(l); existing.add(l)
        except Exception:
            pass
        while len(active) < 3:
            pool = [l for l in _ALL_LETTERS if l not in RARE and l not in existing]
            if not pool: pool = [l for l in _ALL_LETTERS if l not in existing] or list(_ALL_LETTERS)
            l = _r.choices(pool, weights=[_LETTER_WEIGHTS[l] for l in pool])[0]
            active.append(l); existing.add(l)

    # Step 4: Refill preview to 3 using Almost guidance
    try:
        almost = find_almost_words(state, limit=6)
        good = [a["needs"] for a in almost
                if a["needs"] not in board_letters and a["needs"] not in existing]
        _r.shuffle(good)
    except Exception:
        good = []
    for l in good:
        if len(preview) >= 3: break
        preview.append(l); existing.add(l)
    while len(preview) < 3:
        pool = [l for l in _ALL_LETTERS if l not in RARE and l not in existing]
        if not pool: pool = [l for l in _ALL_LETTERS if l not in RARE]
        l = _r.choices(pool, weights=[_LETTER_WEIGHTS[l] for l in pool])[0]
        preview.append(l); existing.add(l)

    active = _apply_comeback_wild(state, active)
    return active[:3], preview[:3]




def get_letter_preview_moves(state: GameState, letter: str, limit: int = 12) -> list[dict]:
    """Return best board placements for a selected Letter Market tile.

    This powers the Balatro-like expectation preview:
    selected letter -> highlighted cells -> predicted word / territory / combo.
    It is intentionally best-effort and never mutates the live state.
    """
    letter = _norm_letter(letter)
    if not letter or letter not in _ALL_LETTERS:
        return []

    excluded = set(state.usedWords)
    player = state.currentPlayer
    try:
        raw_moves = _fast_bot_moves_for_letter(state, letter, max_results=limit * 4, excluded=excluded)
    except Exception:
        raw_moves = []

    by_cell: dict[tuple[int, int], dict] = {}
    for m in raw_moves:
        try:
            after = validate_and_apply_move(
                clone_state(state),
                m["row"], m["col"], m["letter"], m["path"],
                advance_market_flag=False,
            )
            last = after.moveHistory[-1]
            if not _is_ui_word(last.word):
                continue
            combos = list(last.comboLabels or [])
            value = (
                last.territoryGained * 2
                + last.wordScoreGained
                + last.fortifiedCellsGained * 2
                + last.captureCount * 5
                + (4 if "BRIDGE" in combos else 0)
                + (4 if "CUT" in combos else 0)
                + (3 if "LONG PATH" in combos else 0)
                + (3 if any(str(c).startswith("SYNERGY") for c in combos) else 0)
            )
            kind = "SAFE"
            if last.captureCount > 0 or "BRIDGE" in combos or "CUT" in combos or any(str(c).startswith("SYNERGY") for c in combos):
                kind = "POWER"
            elif len(last.word) >= 5 or "LONG PATH" in combos:
                kind = "LONG"
            elif last.territoryGained <= 2:
                kind = "SETUP"

            syn_hint = _synergy_preview_text(state, combos, player, last.word, letter,
                                             path=last.path, row=m["row"], col=m["col"])
            roles = [c for c in combos if not str(c).startswith("SYNERGY")]
            if syn_hint:
                roles.append(syn_hint)
            tier = "safe"
            if last.captureCount > 0 or "BRIDGE" in combos or any(str(c).startswith("SYNERGY") for c in combos) or syn_hint:
                tier = "strong"
            elif last.territoryGained >= 5 or "CUT" in combos:
                tier = "frontline"
            elif "LONG PATH" in combos or len(last.word) >= 5:
                tier = "path"
            item = {
                "row": m["row"],
                "col": m["col"],
                "letter": letter,
                "word": last.word,
                "territoryGain": last.territoryGained,
                "gain": last.territoryGained,
                "wordScore": last.wordScoreGained,
                "lockGain": last.fortifiedCellsGained,
                "captureCount": last.captureCount,
                "comboLabels": combos,
                "roles": roles,
                "synergyPreview": syn_hint,
                "kind": kind,
                "tier": tier,
                "value": value,
                "path": [{"row": p.row, "col": p.col} for p in last.path],
            }
            key = (item["row"], item["col"])
            if key not in by_cell or item["value"] > by_cell[key]["value"]:
                by_cell[key] = item
        except Exception:
            continue

    moves = sorted(by_cell.values(), key=lambda x: (-x["value"], -x["territoryGain"], x["word"]))
    return moves[:limit]



def get_threat_preview(state: GameState, limit: int = 8) -> list[dict]:
    """Return opponent capture threats against the current player.

    This is intentionally lightweight: it simulates a small set of opponent moves
    and returns cells/regions that may swing next turn. It powers the UI warning
    layer without making the bot omniscient.
    """
    if state.winner:
        return []
    defender = state.currentPlayer
    attacker = other_player(defender)
    probe = clone_state(state)
    probe.currentPlayer = attacker
    try:
        moves = _fast_bot_moves(probe, max_len=4, max_results=limit * 4, excluded=set(state.usedWords))
    except Exception:
        moves = []
    threats = []
    seen = set()
    for m in moves:
        try:
            after = validate_and_apply_move(clone_state(probe), m["row"], m["col"], m["letter"], m["path"], advance_market_flag=False)
            last = after.moveHistory[-1]
            if last.captureCount <= 0 and "CUT" not in (last.comboLabels or []):
                continue
            endangered = []
            for c in (after.lastCapturedCells or []):
                # Captured by attacker: warn defender that this cell/area is vulnerable.
                key = (c.row, c.col)
                if key not in seen:
                    seen.add(key)
                    endangered.append({"row": c.row, "col": c.col})
            if not endangered and last.captureCount <= 0:
                continue
            threats.append({
                "row": m["row"],
                "col": m["col"],
                "word": last.word,
                "territorySwing": last.territoryGained,
                "captureCount": last.captureCount,
                "comboLabels": last.comboLabels or [],
                "cells": endangered,
                "reason": f"{attacker} may swing +{last.territoryGained} with {last.word}",
                "level": "high" if last.captureCount >= 2 or "BRIDGE" in (last.comboLabels or []) else "medium",
            })
            if len(threats) >= limit:
                break
        except Exception:
            continue
    return threats

def get_market_stats(state: GameState) -> list[dict]:
    """Return stats for each active market letter."""
    stats = []
    for letter in state.marketLetters:
        s = _letter_best_stats(state, letter)
        s["letter"] = letter
        stats.append(s)
    return stats


def find_candidate_words(state: GameState, limit: int = 15) -> list[str]:
    """Return PLAYABLE words for Suggested — filtered for common words."""
    excluded = set(state.usedWords)
    moves = _fast_bot_moves(state, max_len=4, max_results=limit * 2, excluded=excluded)
    seen = set()
    result = []
    for m in moves:
        w = m["word"]
        if w in seen or not _is_ui_word(w):
            continue
        seen.add(w)
        result.append(w)
        if len(result) >= limit:
            break
    return result

def snapshot(state: GameState):
    owners = {(cell.row, cell.col): cell.owner for row in state.board for cell in row}
    locked = {(cell.row, cell.col): cell.fortified for row in state.board for cell in row}
    red_total = total_score(state, "RED")
    blue_total = total_score(state, "BLUE")
    leader = "RED" if red_total > blue_total else "BLUE" if blue_total > red_total else "TIE"
    return owners, locked, red_total, blue_total, leader


def diff_cells(before_state: GameState, after_state: GameState, player: str):
    before_owner, before_locked, before_red, before_blue, before_leader = snapshot(before_state)
    after_owner, after_locked, after_red, after_blue, after_leader = snapshot(after_state)

    changed = []
    captured = []
    newly_locked = []
    territory_gain = 0
    capture_count = 0

    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            before = before_owner[(r, c)]
            after = after_owner[(r, c)]
            if before != after:
                changed.append(Coord(row=r, col=c))
            if before != player and after == player:
                territory_gain += 1
                if before is not None and before != player:
                    captured.append(Coord(row=r, col=c))
                    capture_count += 1
            if not before_locked[(r, c)] and after_locked[(r, c)] and after == player:
                newly_locked.append(Coord(row=r, col=c))

    return {
        "changed": changed,
        "captured": captured,
        "newly_locked": newly_locked,
        "territory_gain": territory_gain,
        "capture_count": capture_count,
        "leader_changed": before_leader != after_leader and before_leader != "TIE" and after_leader != "TIE",
        "red_total": after_red,
        "blue_total": after_blue,
    }


def _count_connected_regions(state, player: str) -> int:
    """Count how many disconnected regions player owns (for BRIDGE/CUT detection)."""
    visited = set()
    regions = 0
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if state.board[r][c].owner == player and (r, c) not in visited:
                regions += 1
                stack = [(r, c)]
                while stack:
                    cr, cc = stack.pop()
                    if (cr, cc) in visited:
                        continue
                    visited.add((cr, cc))
                    for nr, nc in get_neighbors(cr, cc):
                        if state.board[nr][nc].owner == player and (nr, nc) not in visited:
                            stack.append((nr, nc))
    return regions


def find_cross_words(state, row: int, col: int, letter: str) -> list[str]:
    """Find all valid words formed by placing letter at (row,col) in any direction."""
    found = []
    words = get_words()
    letter = _norm_letter(letter)
    for dr, dc in [(0,1),(1,0),(0,-1),(-1,0)]:
        r, c = row - dr, col - dc
        while in_bounds(r,c) and state.board[r][c].letter:
            r -= dr; c -= dc
        r += dr; c += dc
        chars = []
        rr, cc = r, c
        while in_bounds(rr, cc) and (state.board[rr][cc].letter or (rr==row and cc==col)):
            chars.append(letter if (rr==row and cc==col) else _norm_letter(state.board[rr][cc].letter))
            rr += dr; cc += dc
        word_str = _norm_word("".join(chars))
        if len(word_str) >= _WORD_MIN and word_str in words and word_str not in found:
            found.append(word_str)
    return found


def combo_labels(word: str, territory_gain: int, lock_gain: int,
                 capture_count: int, leader_changed: bool,
                 before_state=None, after_state=None, player: str = "RED",
                 cross_words: list | None = None,
                 row: int = -1, col: int = -1) -> list[str]:
    labels = []

    # ── Power moves ───────────────────────────────────────────────────────────
    if len(word) >= 5:
        labels.append("LONG PATH")
    if territory_gain >= 6:
        labels.append("MEGA TERRITORY")
    if lock_gain >= 2:
        labels.append("FORTIFY CHAIN")
    if capture_count >= 1:
        labels.append("CAPTURE")
    if capture_count >= 2:
        labels.append("MAJOR CAPTURE")
    if leader_changed:
        labels.append("SWING MOVE")

    # ── Cross Word Bonus (もじぴったん的連鎖) ─────────────────────────────────
    if cross_words and len(cross_words) >= 2:
        labels.append("CROSS WORD")    # 1手で2語以上 +2T

    # ── Early Yaku (序盤でも出る役) ──────────────────────────────────────────
    if before_state and after_state:
        opponent = "BLUE" if player == "RED" else "RED"
        before_my_t  = sum(1 for r in before_state.board for c in r if c.owner == player)
        after_my_t   = sum(1 for r in after_state.board  for c in r if c.owner == player)
        before_opp_t = sum(1 for r in before_state.board for c in r if c.owner == opponent)
        after_opp_t  = sum(1 for r in after_state.board  for c in r if c.owner == opponent)

        # FIRST CAPTURE — first time taking opponent's cell this game
        before_hist = [m for m in before_state.moveHistory if "CAPTURE" in (m.comboLabels or [])]
        if capture_count >= 1 and not before_hist:
            labels.append("FIRST CAPTURE")

        # EDGE REACH — player reaches the board edge for the first time
        edge_before = any(
            before_state.board[r][c].owner == player
            for r in range(BOARD_SIZE) for c in range(BOARD_SIZE)
            if r in (0, BOARD_SIZE-1) or c in (0, BOARD_SIZE-1)
        )
        edge_after = any(
            after_state.board[r][c].owner == player
            for r in range(BOARD_SIZE) for c in range(BOARD_SIZE)
            if r in (0, BOARD_SIZE-1) or c in (0, BOARD_SIZE-1)
        )
        if not edge_before and edge_after:
            labels.append("EDGE REACH")

        # LINK only fires if BRIDGE didn't (BRIDGE is the stronger version)
        # Both are checked via region counting — skip standalone LINK to reduce spam

        # COMEBACK — player was behind, now leads or closes gap significantly
        before_leader = "RED" if before_state.scores.redTerritory > before_state.scores.blueTerritory else "BLUE"
        if before_leader != player and leader_changed:
            labels.append("COMEBACK")

        # BRIDGE and CUT
        before_regions = _count_connected_regions(before_state, player)
        after_regions  = _count_connected_regions(after_state, player)
        if before_regions > 1 and after_regions < before_regions:
            labels.append("BRIDGE")
        before_opp_r = _count_connected_regions(before_state, opponent)
        after_opp_r  = _count_connected_regions(after_state, opponent)
        if after_opp_r > before_opp_r:
            labels.append("CUT")

        # ENCIRCLE PRESSURE: score-neutral version of the retired Encircler bonus.
        if _capture_net_pressure(after_state, row, col, player) and (
            "CAPTURE" in labels or "MAJOR CAPTURE" in labels or "CUT" in labels or "BRIDGE" in labels
        ):
            labels.append("ENCIRCLE PRESSURE")

    return labels



def _cooldown_key(r: int, c: int) -> str:
    return f"{r},{c}"

def _is_capture_cooling(state: GameState, r: int, c: int, player: str) -> bool:
    """True if this cell was just captured by the opponent and cannot be flipped yet."""
    try:
        cd = (state.synergyState or {}).get("captureCooldown", {})
        info = cd.get(_cooldown_key(r, c))
        if not info:
            return False
        return info.get("owner") != player and int(info.get("until", -1)) > int(state.turn)
    except Exception:
        return False

def _record_capture_cooldowns(state: GameState, captured: list[Coord], player: str) -> None:
    """Captured cells cannot be recaptured on the opponent's immediate next turn."""
    try:
        ss = dict(state.synergyState or {})
        cd = dict(ss.get("captureCooldown", {}))
        # prune old entries
        cd = {k: v for k, v in cd.items() if int(v.get("until", -1)) >= int(state.turn)}
        for p in captured or []:
            cd[_cooldown_key(p.row, p.col)] = {"owner": player, "until": int(state.turn) + 1}
        ss["captureCooldown"] = cd
        state.synergyState = ss
    except Exception:
        pass

# PHASE3_INVASION_FRONTLINE_V1
def _enemy_of(player: str) -> str:
    return "BLUE" if player == "RED" else "RED"

def _beachhead_bonus(before_state: GameState, row: int, col: int, player: str, word: str) -> int:
    """Reward a light invasion inside enemy influence so maps keep changing."""
    opponent = _enemy_of(player)
    min_len = 4 if _LANG == "ja" else 3
    if len(word or "") < min_len:
        return 0
    enemy = 0
    mine = 0
    cells = {(row, col)}
    for nr, nc in get_neighbors(row, col):
        cells.add((nr, nc))
    for rr, cc in cells:
        owner = before_state.board[rr][cc].owner
        if owner == opponent:
            enemy += 1
        elif owner == player:
            mine += 1
    placed_on_enemy = before_state.board[row][col].owner == opponent
    enemy_majority = enemy >= max(2, mine + 1)
    return 1 if (placed_on_enemy or enemy_majority) else 0

def _frontline_push(before_state: GameState, row: int, col: int, player: str, territory_gain: int) -> bool:
    if territory_gain <= 0:
        return False
    opponent = _enemy_of(player)
    if not any(before_state.board[nr][nc].owner == opponent for nr, nc in get_neighbors(row, col)):
        return False
    mid = BOARD_SIZE // 2
    return row >= mid if player == "RED" else row <= mid

# PHASE4_ROTATION_RAID_V1
def rotate_block_state(state: GameState, row: int, col: int, player=None) -> GameState:
    """Rotate only the letters in a 2x2 block. Ownership never moves.

    Constraints:
    - once per game
    - 2x2 only
    - locked cells cannot be rotated
    - rotation alone captures nothing and does not advance the turn
    """
    if state.winner:
        return state
    player = player or state.currentPlayer
    opponent = "BLUE" if player == "RED" else "RED"
    try:
        size = int(getattr(state, "boardSize", BOARD_SIZE) or BOARD_SIZE)
    except Exception:
        size = BOARD_SIZE
    if row < 0 or col < 0 or row + 1 >= size or col + 1 >= size:
        raise ValueError("Rotation Raid must target the top-left of a 2x2 block.")

    coords = [(row, col), (row, col + 1), (row + 1, col + 1), (row + 1, col)]
    cells = [state.board[r][c] for r, c in coords]

    ss = dict(state.synergyState or {})
    if ss.get("rotationRaidUsed"):
        raise ValueError("Rotation Raid already used this game.")
    if any(getattr(cell, "fortified", False) for cell in cells):
        raise ValueError("Locked cells cannot be rotated.")
    if any(not getattr(cell, "letter", None) for cell in cells):
        raise ValueError("Rotation Raid needs a complete 2x2 letter block.")
    if not any(getattr(cell, "owner", None) == opponent for cell in cells):
        raise ValueError("Rotation Raid must touch enemy territory.")

    before_letters = [cell.letter for cell in cells]
    after_letters = [before_letters[-1]] + before_letters[:-1]  # clockwise letter rotation
    for cell, letter in zip(cells, after_letters):
        cell.letter = letter

    ss["rotationRaidUsed"] = True
    ss["rotationRaidPlayer"] = player
    ss["rotationRaidTurn"] = int(state.turn)
    ss["rotationRaidCells"] = [{"row": r, "col": c} for r, c in coords]
    state.synergyState = ss
    state.lastChangedCells = [Coord(row=r, col=c) for r, c in coords]
    state.lastCapturedCells = []
    state.lastFortifiedCells = []
    state.lastComboLabels = ["ROTATION RAID"]

    recalc_scores(state)
    try:
        red_total = (state.scores.redTerritory or 0) * 1.5 + (state.scores.redWord or 0)
        blue_total = (state.scores.blueTerritory or 0) * 1.5 + (state.scores.blueWord or 0)
        state.moveHistory.append(MoveHistoryItem(
            turn=state.turn,
            player=player,
            word="回転侵略" if _LANG == "ja" else "ROTATION RAID",
            moveType="ROTATE",
            placedRow=row,
            placedCol=col,
            placedLetter="",
            path=[Coord(row=r, col=c) for r, c in coords],
            wordScoreGained=0,
            territoryGained=0,
            fortifiedCellsGained=0,
            captureCount=0,
            comboLabels=["ROTATION RAID"],
            redTotalAfter=red_total,
            blueTotalAfter=blue_total,
        ))
    except Exception:
        pass
    return state

SECOND_PLAYER_BONUS = 2  # EN/V23 value
JP_SECOND_PLAYER_BONUS = 3  # JP v11: large dictionary needs stronger BLUE foothold.

def _apply_blue_second_player_initiative(state: GameState, player: str, path) -> int:
    """Give BLUE a stronger one-time foothold on its first actual word move.

    V18 showed 2PI fired in every match, but +1 cell was not enough.
    V19 keeps the correction one-time only, but raises the bonus to 2 cells.
    Returns the number of bonus cells claimed.
    """
    if player != "BLUE":
        return 0
    try:
        ss = dict(state.synergyState or {})
        if ss.get("blueInitiativeUsed"):
            return 0
        initiative_window = 6 if _LANG == "ja" else 4
        if int(state.turn) > initiative_window:
            return 0

        candidates = []
        seen = set()
        path_cells = [(p.row, p.col) for p in (path or [])]
        for r, c in path_cells:
            for nr, nc in get_neighbors(r, c):
                if (nr, nc) in seen:
                    continue
                seen.add((nr, nc))
                cell = state.board[nr][nc]
                if cell.owner is None and not cell.fortified:
                    near_letter = 1 if any(state.board[ar][ac].letter for ar, ac in get_neighbors(nr, nc)) else 0
                    center_bias = -abs(nr - BOARD_SIZE//2) - abs(nc - BOARD_SIZE//2)
                    candidates.append((near_letter, center_bias, nr, nc))

        if not candidates:
            return 0

        candidates.sort(reverse=True)
        claimed = 0
        bonus_limit = JP_SECOND_PLAYER_BONUS if _LANG == "ja" else SECOND_PLAYER_BONUS
        for _, _, rr, cc in candidates:
            if claimed >= bonus_limit:
                break
            cell = state.board[rr][cc]
            if cell.owner is None and not cell.fortified:
                cell.owner = "BLUE"
                claimed += 1

        if claimed:
            ss["blueInitiativeUsed"] = True
            ss["blueInitiativeCells"] = claimed
            state.synergyState = ss
        return claimed
    except Exception:
        return 0


def apply_locks(state: GameState):
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            cell = state.board[r][c]
            if cell.owner is None:
                cell.fortified = False
                continue
            owner = cell.owner
            all_same = True
            for nr, nc in get_neighbors(r, c):
                if state.board[nr][nc].owner != owner:
                    all_same = False
                    break
            if r in (0, BOARD_SIZE - 1) or c in (0, BOARD_SIZE - 1):
                all_same = False
            cell.fortified = all_same


def apply_captures(state: GameState, player: str):
    visited = set()
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            if (r, c) in visited or state.board[r][c].owner == player:
                continue
            region = []
            queue = deque([(r, c)])
            touches_edge = False
            while queue:
                cr, cc = queue.popleft()
                if (cr, cc) in visited:
                    continue
                visited.add((cr, cc))
                current = state.board[cr][cc]
                if current.owner == player:
                    continue
                region.append((cr, cc))
                if cr in (0, BOARD_SIZE - 1) or cc in (0, BOARD_SIZE - 1):
                    touches_edge = True
                for nr, nc in get_neighbors(cr, cc):
                    if (nr, nc) not in visited and state.board[nr][nc].owner != player:
                        queue.append((nr, nc))
            if not touches_edge:
                for rr, cc in region:
                    target = state.board[rr][cc]
                    # V4: locked ground is truly locked; no surrounded-capture override.
                    if target.fortified:
                        continue
                    # V4: avoid same-cell ping-pong by blocking immediate recapture.
                    if _is_capture_cooling(state, rr, cc, player):
                        continue
                    target.owner = player

def recalc_scores(state: GameState, current_player_for_word_score: str | None = None, last_word: str | None = None):
    state.scores.redTerritory = count_territory(state, "RED")
    state.scores.blueTerritory = count_territory(state, "BLUE")
    if last_word and current_player_for_word_score:
        score = word_score(last_word)
        if current_player_for_word_score == "RED":
            state.scores.redWord += score
        else:
            state.scores.blueWord += score


def path_contains(path, row: int, col: int) -> bool:
    return any(p.row == row and p.col == col for p in path)


def validate_path_and_word(state: GameState, row: int, col: int, letter: str, path):
    letter = _norm_letter(letter)
    if not letter:
        raise ValueError("Invalid letter")
    if not path_contains(path, row, col):
        raise ValueError("Your placed letter must be part of the word path.")
    seen = set()
    chars = []
    for i, p in enumerate(path):
        if not in_bounds(p.row, p.col):
            raise ValueError("Path out of bounds")
        key = (p.row, p.col)
        if key in seen:
            raise ValueError("You cannot use the same cell twice in a path.")
        seen.add(key)
        if i > 0 and not are_adjacent(path[i - 1], p):
            raise ValueError("Cells must be directly connected — no diagonals.")
        cell = state.board[p.row][p.col]
        if p.row == row and p.col == col:
            chars.append(letter)
        elif cell.letter is not None:
            chars.append(_norm_letter(cell.letter))
        else:
            raise ValueError("All non-placed path cells must contain letters")
    return _norm_word("".join(chars))


def recent_duplicate_blocked(state: GameState, word: str) -> bool:
    """Block any word already used in this game."""
    key = _norm_word(word)
    return key in {_norm_word(w) for w in state.usedWords}



def _jp_capture_cap_for_word(word: str, player: str, turn: int) -> int:
    """Large-dictionary JP capture cap.

    In a large kana dictionary, words are expected to be found often.
    Therefore short words must not flip large enemy regions.
    """
    if _LANG != "ja":
        return 999
    n = len(_norm_word(word))
    cap = 0 if n <= 2 else 1 if n == 3 else 2 if n == 4 else 3
    # RED opening acceleration control. BLUE may have a little more room early.
    if int(turn) <= 6:
        if player == "RED":
            cap = min(cap, 1)
        else:
            cap = min(cap, 2)
    return cap


def _jp_apply_enemy_capture_cap(before: GameState, after: GameState, player: str, word: str, turn: int) -> int:
    """Neutralize enemy-cell flips beyond the JP capture cap.

    Returns the number of enemy-owned cells kept as captures.
    Extra flipped enemy cells become neutral rather than reverting to the opponent.
    """
    if _LANG != "ja":
        return 999
    cap = _jp_capture_cap_for_word(word, player, turn)
    flipped = []
    for rr in range(BOARD_SIZE):
        for cc in range(BOARD_SIZE):
            before_owner = before.board[rr][cc].owner
            after_owner = after.board[rr][cc].owner
            if before_owner not in (None, player) and after_owner == player:
                flipped.append((rr, cc))

    if len(flipped) > cap:
        for rr, cc in flipped[cap:]:
            if not after.board[rr][cc].fortified:
                after.board[rr][cc].owner = None
    return min(len(flipped), cap)


def _jp_remove_new_locks_for_short_words(before: GameState, after: GameState, word: str) -> None:
    """2/3 kana words may form words and labels, but they cannot create new LOCKs."""
    if _LANG != "ja":
        return
    if len(_norm_word(word)) >= 4:
        return
    for rr in range(BOARD_SIZE):
        for cc in range(BOARD_SIZE):
            if not before.board[rr][cc].fortified and after.board[rr][cc].fortified:
                after.board[rr][cc].fortified = False


def _jp_is_large_dict_mode() -> bool:
    return _LANG == "ja" and len(get_words()) >= 1200

# WT_DAZI_V2_INDEPENDENT_ACTION
def _dazi_uses_key(player: str) -> str:
    return f"_daziUses_{player}"

def _coord_key(p) -> tuple[int, int]:
    return (int(p.row), int(p.col))

def apply_dazi_move(state: GameState, path):
    """Independent Disarm/Dazi action.

    It consumes the turn, places no new letter, and neutralizes one enemy
    cell only if the player can form a valid word using existing board letters.
    """
    if state.winner:
        raise ValueError("Game already finished")

    player = state.currentPlayer
    opponent = "BLUE" if player == "RED" else "RED"

    if state.synergyState is None:
        state.synergyState = {}

    uses_key = _dazi_uses_key(player)
    used = int(state.synergyState.get(uses_key, 0) or 0)
    if used >= 2:
        raise ValueError("Disarm has already been used twice.")

    if not path or len(path) < _WORD_MIN:
        raise ValueError(f"Disarm needs a connected word path of at least {_WORD_MIN} letters.")
    if len(path) > _WORD_MAX:
        raise ValueError(f"Disarm word path must be {_WORD_MIN}–{_WORD_MAX} letters.")

    seen = set()
    chars = []
    target = None

    for i, p in enumerate(path):
        r, c = _coord_key(p)
        bs = len(state.board)
        if r < 0 or c < 0 or r >= bs or c >= bs:
            raise ValueError("Path out of bounds")
        key = (r, c)
        if key in seen:
            raise ValueError("You cannot use the same cell twice in a path.")
        seen.add(key)
        if i > 0 and not are_adjacent(path[i - 1], p):
            raise ValueError("Cells must be directly connected — no diagonals.")

        cell = state.board[r][c]
        if cell.letter is None:
            raise ValueError("Disarm path must use existing letters only.")

        chars.append(_norm_letter(cell.letter))

        if cell.owner == opponent:
            # Prefer a locked enemy letter, but allow any enemy letter.
            # This makes Dazi usable as an invasion tool even when no LOCK is available.
            if target is None:
                target = (r, c)
            else:
                tr, tc = target
                previous_locked = bool(state.board[tr][tc].fortified)
                if bool(cell.fortified) and not previous_locked:
                    target = (r, c)

    if target is None:
        raise ValueError("奪字には敵の文字を含む単語が必要です。")

    word = _norm_word("".join(chars))
    if len(word) < _WORD_MIN or len(word) > _WORD_MAX:
        raise ValueError(f"Need {_WORD_MIN}–{_WORD_MAX} tiles. '{word}' has {len(word)}.")
    if recent_duplicate_blocked(state, word):
        raise ValueError(f"You already played {word} this game. Try another word.")
    if not is_valid_word(word):
        raise ValueError(f"'{word}' is not in the dictionary. Try a common word.")

    temp = deepcopy(state)
    tr, tc = target

    # Neutralize only one locked enemy letter. The glyph remains.
    temp.board[tr][tc].owner = None
    temp.board[tr][tc].fortified = False

    recalc_scores(temp)

    if temp.synergyState is None:
        temp.synergyState = {}
    temp.synergyState[uses_key] = used + 1

    red_total = total_score(temp, "RED")
    blue_total = total_score(temp, "BLUE")

    item = MoveHistoryItem(
        turn=state.turn,
        player=player,
        word=word,
        moveType="DAZI",
        placedRow=tr,
        placedCol=tc,
        placedLetter=temp.board[tr][tc].letter,
        path=[Coord(row=int(p.row), col=int(p.col)) for p in path],
        wordScoreGained=0,
        territoryGained=0,
        fortifiedCellsGained=0,
        captureCount=0,
        comboLabels=["DISARM"],
        redTotalAfter=red_total,
        blueTotalAfter=blue_total,
    )

    temp.usedWords.append(word)
    temp.moveHistory.append(item)
    temp.recentMoves = [f"{player}: {word} [DISARM]"] + temp.recentMoves[:4]
    temp.lastChangedCells = [Coord(row=tr, col=tc)]
    temp.lastCapturedCells = []
    temp.lastFortifiedCells = []
    temp.lastComboLabels = ["DISARM"]

    temp.currentPlayer = other_player(player)
    temp.turn += 1
    temp.consecutivePasses = 0

    if is_game_over(temp):
        temp.winner = decide_winner(temp)

    return temp

def validate_and_apply_move(state: GameState, row: int, col: int, letter: str, path, advance_market_flag: bool = False, dazi: bool = False):
    if state.winner:
        raise ValueError("Game already finished")
    if not in_bounds(row, col):
        raise ValueError("Out of bounds")
    if state.board[row][col].letter is not None:
        raise ValueError("Cell already occupied")
    letter = _norm_letter(letter)
    if not letter or letter not in _ALL_LETTERS:
        raise ValueError("Letter must be one valid tile")
    if not any(state.board[nr][nc].letter for nr, nc in get_neighbors(row, col)):
        raise ValueError("Place your letter next to an existing letter on the board.")

    word = validate_path_and_word(state, row, col, letter, path)
    if len(word) < _WORD_MIN or len(word) > _WORD_MAX:
        raise ValueError(f"Need {_WORD_MIN}–{_WORD_MAX} tiles. '{word}' has {len(word)}.")
    if recent_duplicate_blocked(state, word):
        raise ValueError(f"You already played {word} this game. Try another word.")
    if not is_valid_word(word):
        raise ValueError(f"'{word}' is not in the dictionary. Try a common word.")
    player = state.currentPlayer

    before = clone_state(state)
    temp = deepcopy(state)
    temp.board[row][col].letter = letter
    # Short word cap: prevent short-word spam
    max_cells = (1 if _LANG == "ja" and len(word) == 2 else 2 if _LANG == "en" and len(word) == 3 else len(path))
    cells_claimed = 0
    for p in path:
        cell = temp.board[p.row][p.col]
        if cell.owner != player:
            # V5: fortified enemy cells are permanent territory. They can still
            # be used as letters in a word path, but their ownership does not flip.
            if cell.fortified and cell.owner is not None:
                continue
            # V5: immediate recapture cooldown also applies to direct path claims.
            if _is_capture_cooling(temp, p.row, p.col, player):
                continue
            if cells_claimed >= max_cells:
                continue
            cells_claimed += 1
        cell.owner = player
    # PHASE4_DAZI_DISARM_V1
    # 奪字 / Disarm: up to twice per player, neutralize one LOCKED enemy cell
    # used in the submitted word path. It keeps the glyph but clears owner+lock.
    dazi_done = False
    if dazi:
        uses_map = dict(getattr(temp, "daziUses", {}) or {})
        used = int(uses_map.get(player, 0) or 0)
        if used >= 2:
            raise ValueError("Disarm already used twice")
        for p in path:
            c = temp.board[p.row][p.col]
            if c.fortified and c.owner is not None and c.owner != player:
                c.owner = None
                c.fortified = False
                uses_map[player] = used + 1
                temp.daziUses = uses_map
                dazi_done = True
                break
        if not dazi_done:
            raise ValueError("Disarm needs a enemy cell in your word path")

    apply_captures(temp, player)

    # JP v11: large-dictionary capture caps.
    # In a dense kana dictionary, words are available often; captures must scale by word length.
    _jp_apply_enemy_capture_cap(before, temp, player, word, state.turn)

    apply_locks(temp)

    # JP v11: 2/3 kana words cannot create new LOCKs.
    # 4/5 kana words are the main LOCK-building moves.
    _jp_remove_new_locks_for_short_words(before, temp, word)

    blue_initiative_used = _apply_blue_second_player_initiative(temp, player, path)
    if blue_initiative_used:
        apply_locks(temp)
    recalc_scores(temp, current_player_for_word_score=player, last_word=word)

    wild_cost_active = state.synergyState.get("_wildCostPending") == player
    if wild_cost_active:
        if player == "RED":
            temp.scores.redWord = max(0, temp.scores.redWord - 1)
        else:
            temp.scores.blueWord = max(0, temp.scores.blueWord - 1)

    delta = diff_cells(before, temp, player)

    # Detect cross words formed by this placement
    cross_words_formed = find_cross_words(before, row, col, letter)
    combos = combo_labels(
        word, delta["territory_gain"], len(delta["newly_locked"]),
        delta["capture_count"], delta["leader_changed"],
        before_state=before, after_state=temp, player=player,
        cross_words=cross_words_formed, row=row, col=col,
    )

    beachhead_bonus = _beachhead_bonus(before, row, col, player, word)
    if beachhead_bonus:
        combos.append("BEACHHEAD")
    if _frontline_push(before, row, col, player, delta["territory_gain"]):
        combos.append("FRONTLINE PUSH")


    # ── Role bonus: award extra territory for strategic combos ───────────────
    bonus = 0
    if beachhead_bonus:
        bonus += beachhead_bonus
    if _LANG == "ja":
        # JP v11: in large dictionaries, 3-kana words happen constantly.
        # BRIDGE/CUT labels remain visible, but scoring starts at 4+ kana.
        wl = len(word)
        if wl >= 4:
            if "BRIDGE" in combos:        bonus += 1
            if "CUT" in combos:           bonus += 1
            if "FORTIFY CHAIN" in combos: bonus += 1
        if "LONG PATH" in combos:         bonus += 1
        if wl >= 4 and "CROSS WORD" in combos: bonus += 1
        if "COMEBACK" in combos:          bonus += 1
        # FIRST CAPTURE may help readability, but no extra territory in large-dict mode.
        # EDGE / DOUBLE / MAJOR / MEGA remain score-neutral in Japanese.
    else:
        # Power moves (中盤〜終盤)
        if "BRIDGE" in combos:        bonus += 3
        if "CUT" in combos:           bonus += 2
        if "FORTIFY CHAIN" in combos: bonus += 2
        if "MAJOR CAPTURE" in combos: bonus += 1
        if "DOUBLE CAPTURE" in combos:bonus += 1
        if "LONG PATH" in combos:     bonus += 1
        if "MEGA TERRITORY" in combos:bonus += 1
        # Cross Word (もじぴったん的連鎖)
        if "CROSS WORD" in combos:    bonus += 2
        # Early Yaku (序盤でも出る役)
        if "FIRST CAPTURE" in combos: bonus += 1
        if "EDGE REACH" in combos:    bonus += 1
        if "COMEBACK" in combos:      bonus += 2

    # Synergy Card bonus (Balatro-like build direction)
    base_bonus = bonus
    synergy_bonus = apply_synergy_bonus(temp, combos, player, word, letter, path=path, row=row, col=col, territory_gain=delta["territory_gain"], lock_gain=len(delta["newly_locked"]))
    bonus_uncapped = base_bonus + synergy_bonus
    # WT_JA_T2_BONUS_CAP_CALL_20260607
    bonus_uncapped = _wt_ja_cap_early_t2_bonus_20260607(state, temp, player, combos, bonus_uncapped, word)

    # ── Anti-snowball: cap bonus when player is already winning by 10+ cells ──
    bonus = bonus_uncapped
    if bonus > 0 and temp.scores:
        my_t   = temp.scores.redTerritory if player == "RED" else temp.scores.blueTerritory
        opp_t  = temp.scores.blueTerritory if player == "RED" else temp.scores.redTerritory
        lead   = my_t - opp_t
        if lead >= 15:
            bonus = min(bonus, 1)   # hard cap at 1 when crushing
        elif lead >= 10:
            bonus = min(bonus, 2)   # soft cap at 2 when comfortably ahead

    # JP v4: 3-kana words are extremely common.
    # They may still capture and trigger labels, but large bonus stacking is capped.
    if _LANG == "ja" and len(word) == 3:
        if delta["capture_count"] >= 2:
            bonus = min(bonus, 1)
        elif delta["capture_count"] >= 1 and ("BRIDGE" in combos or "CUT" in combos or "FORTIFY CHAIN" in combos):
            bonus = min(bonus, 1)
        elif "BRIDGE" in combos and "CUT" in combos:
            bonus = min(bonus, 1)
        else:
            bonus = min(bonus, 2)

    # Show the actual synergy contribution after any anti-snowball cap.
    actual_base_bonus = min(base_bonus, bonus)
    actual_synergy_bonus = max(0, bonus - actual_base_bonus)
    if actual_synergy_bonus > 0:
        syn_text = synergy_activation_text(temp, combos, player, word, letter, actual_synergy_bonus)
        if syn_text:
            combos.append(f"SYNERGY:{syn_text}")
    if dazi_done and "DAZI" not in combos:
        combos.append("DAZI")
    if wild_cost_active:
        combos.append("WILD COST")
    if blue_initiative_used:
        combos.append("SECOND PLAYER INITIATIVE")
    if bonus > 0:
        # Convert nearest unfortified non-player cells to player (bonus territory)
        import random as _r
        candidates = [
            (r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE)
            if temp.board[r][c].letter and temp.board[r][c].owner != player
            and not temp.board[r][c].fortified
            and not _is_capture_cooling(temp, r, c, player)
        ]
        _r.shuffle(candidates)
        for r, c in candidates[:bonus]:
            temp.board[r][c].owner = player
        if candidates[:bonus]:
            apply_locks(temp)
            recalc_scores(temp)
            delta["territory_gain"] += min(bonus, len(candidates))

    item = MoveHistoryItem(
        turn=state.turn,
        player=player,
        word=word,
        moveType="WORD",
        placedRow=row,
        placedCol=col,
        placedLetter=letter,
        path=[Coord(row=p.row, col=p.col) for p in path],
        wordScoreGained=word_score(word),
        territoryGained=delta["territory_gain"],
        fortifiedCellsGained=len(delta["newly_locked"]),
        captureCount=delta["capture_count"],
        comboLabels=combos,
        redTotalAfter=delta["red_total"],
        blueTotalAfter=delta["blue_total"],
    )


    temp.usedWords.append(word)
    temp.moveHistory.append(item)
    combo_suffix = f" [{' | '.join(combos)}]" if combos else ""
    temp.recentMoves = [f"{player}: {word}{combo_suffix}"] + temp.recentMoves[:4]
    temp.lastChangedCells = delta["changed"]
    temp.lastCapturedCells = delta["captured"]
    temp.lastFortifiedCells = delta["newly_locked"]
    temp.lastComboLabels = combos
    temp.synergyState = update_synergy_state(temp, combos, is_seed=False)
    _record_capture_cooldowns(temp, delta["captured"], player)
    if wild_cost_active:
        temp.synergyState.pop("_wildCostPending", None)
    temp.currentPlayer = other_player(player)
    temp.turn += 1
    temp.consecutivePasses = 0

    if is_game_over(temp):
        temp.winner = decide_winner(temp)

    # Advance Letter Market — only for human player moves (flag=True)
    if advance_market_flag and temp.marketLetters:
        new_active, new_preview = advance_market(temp, letter)
        temp.marketLetters  = new_active
        temp.previewLetters = new_preview
    return temp


def apply_seed_move(state: GameState, row: int, col: int, letter: str, advance_market_flag: bool = False):
    if state.winner:
        raise ValueError("Game already finished")
    if not in_bounds(row, col) or state.board[row][col].letter is not None:
        raise ValueError("Seed move requires an empty cell")
    letter = _norm_letter(letter)
    if not letter or letter not in _ALL_LETTERS:
        raise ValueError("Letter must be one valid tile")
    if not any(state.board[nr][nc].letter for nr, nc in get_neighbors(row, col)):
        raise ValueError("Seed move must be next to existing letters")

    temp = deepcopy(state)
    player = state.currentPlayer
    temp.board[row][col].letter = letter
    # Last Stand: if a player has almost no territory, seed becomes a reclaim move.
    # This prevents the psychologically dead "0 cells" state from feeling hopeless.
    try:
        pre_cells = sum(1 for rr in range(BOARD_SIZE) for cc in range(BOARD_SIZE)
                        if state.board[rr][cc].owner == player)
        if pre_cells <= 2:
            temp.board[row][col].owner = player
            temp.board[row][col].fortified = False
    except Exception:
        pass
    temp.currentPlayer = other_player(player)
    temp.turn += 1
    temp.consecutivePasses = 0
    temp.lastChangedCells = [Coord(row=row, col=col)]
    temp.lastCapturedCells = []
    temp.lastFortifiedCells = []
    temp.lastComboLabels = []
    temp.synergyState = update_synergy_state(temp, [], is_seed=True)
    # Seed cost: opponent +1T (unless SEED_TACTICIAN or player has ≤2 cells)
    my_cells = sum(1 for r in range(BOARD_SIZE) for c in range(BOARD_SIZE)
                   if temp.board[r][c].owner == player)
    if state.selectedSynergy != "SEED_TACTICIAN" and my_cells > 2:
        import random as _r
        opp = other_player(player)
        give_cells = [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE)
                      if temp.board[r][c].letter and temp.board[r][c].owner == player
                      and not temp.board[r][c].fortified]
        if give_cells:
            _r.shuffle(give_cells)
            temp.board[give_cells[0][0]][give_cells[0][1]].owner = opp
    seed_word = "LAST STAND" if sum(1 for rr in range(BOARD_SIZE) for cc in range(BOARD_SIZE) if state.board[rr][cc].owner == player) <= 2 else "SEED"
    item = MoveHistoryItem(
        turn=state.turn,
        player=player,
        word=seed_word,
        moveType="SEED",
        placedRow=row,
        placedCol=col,
        placedLetter=letter,
        path=[Coord(row=row, col=col)],
        redTotalAfter=total_score(temp, "RED"),
        blueTotalAfter=total_score(temp, "BLUE"),
    )
    temp.moveHistory.append(item)
    temp.recentMoves = [f"{player}: SEED ({letter})"] + temp.recentMoves[:4]
    if is_game_over(temp):
        temp.winner = decide_winner(temp)
    # Advance market — only for human player moves (flag=True)
    if advance_market_flag and temp.marketLetters:
        new_active, new_preview = advance_market(temp, letter)
        temp.marketLetters  = new_active
        temp.previewLetters = new_preview
    return temp


def pass_turn(state: GameState):
    if state.winner:
        return state
    temp = deepcopy(state)
    current = temp.currentPlayer
    temp.currentPlayer = other_player(temp.currentPlayer)
    temp.turn += 1
    temp.consecutivePasses += 1
    temp.recentMoves = [f"{current}: PASS"] + temp.recentMoves[:4]
    temp.lastChangedCells = []
    temp.lastCapturedCells = []
    temp.lastFortifiedCells = []
    temp.lastComboLabels = []
    if is_game_over(temp):
        temp.winner = decide_winner(temp)
    return temp


def preview_move(state: GameState, row: int, col: int, letter: str, path) -> PreviewMoveResponse:
    try:
        word = validate_path_and_word(state, row, col, letter, path) if path else ""
        includes = path_contains(path, row, col) if path else False
        valid_len = 3 <= len(word) <= 6
        in_dict = is_valid_word(word) if valid_len else False
        response = PreviewMoveResponse(
            word=word,
            isValidLength=valid_len,
            includesPlacedCell=includes,
            isInDictionary=in_dict,
            wordScore=word_score(word) if in_dict else 0,
        )
        if in_dict and not recent_duplicate_blocked(state, word):
            after = validate_and_apply_move(clone_state(state), row, col, letter, path)
            last = after.moveHistory[-1]
            response.territoryGain = last.territoryGained
            response.lockGain = last.fortifiedCellsGained
            response.captureHappened = last.captureCount > 0
            response.captureCount = last.captureCount
            response.comboLabels = last.comboLabels
        return response
    except Exception as exc:
        return PreviewMoveResponse(errorMessage=str(exc))


def get_score_gap(state: GameState, player: str) -> int:
    """Return how many cells player is behind (positive = losing)."""
    opp = "BLUE" if player == "RED" else "RED"
    my_t  = sum(1 for r in state.board for c in r if c.owner == player)
    opp_t = sum(1 for r in state.board for c in r if c.owner == opp)
    return opp_t - my_t


def is_game_over(state: GameState) -> bool:
    if state.winner:
        return True
    if state.turn > MAX_TURNS or state.consecutivePasses >= 2:
        return True
    return all(cell.letter is not None for row in state.board for cell in row)


def decide_winner(state: GameState):
    # 案4: territory count is primary (Othello-style)
    red_t = count_territory(state, "RED")
    blue_t = count_territory(state, "BLUE")
    if red_t != blue_t:
        return "RED" if red_t > blue_t else "BLUE"
    # Tiebreak: word score
    if state.scores.redWord != state.scores.blueWord:
        return "RED" if state.scores.redWord > state.scores.blueWord else "BLUE"
    return "DRAW"


# BOT

def get_placeable_empty_cells(state: GameState):
    return [(r, c) for r in range(BOARD_SIZE) for c in range(BOARD_SIZE) if state.board[r][c].letter is None and any(state.board[nr][nc].letter for nr, nc in get_neighbors(r, c))]


def generate_paths_from_cell(state: GameState, placed, target_len: int):
    results = []
    seen = set()

    def dfs(path):
        if len(path) == target_len:
            if placed in path:
                key = tuple(path)
                if key not in seen:
                    seen.add(key)
                    results.append(path[:])
            return
        r, c = path[-1]
        for nr, nc in get_neighbors(r, c):
            if (nr, nc) in path:
                continue
            if (nr, nc) != placed and state.board[nr][nc].letter is None:
                continue
            path.append((nr, nc))
            dfs(path)
            path.pop()

    # Start from placed cell or existing cells near it; this supports placed letter in middle/end.
    starts = [placed]
    for nr, nc in get_neighbors(placed[0], placed[1]):
        if state.board[nr][nc].letter:
            starts.append((nr, nc))
    for start in starts:
        dfs([start])
    return results


def letters_from_path(state: GameState, path, placed, placed_letter):
    chars = []
    for r, c in path:
        if (r, c) == placed:
            chars.append(placed_letter)
        else:
            cell = state.board[r][c]
            if not cell.letter:
                return None
            chars.append(cell.letter)
    return "".join(chars).upper()


def find_word_path_for_target(state: GameState, target_word: str):
    target_word = _norm_word(target_word)
    for er, ec in get_placeable_empty_cells(state):
        for idx, ch in enumerate(target_word):
            # placed letter must supply the matching letter at some path position.
            for path in generate_paths_from_cell(state, (er, ec), len(target_word)):
                if (er, ec) not in path:
                    continue
                if path.index((er, ec)) != idx:
                    continue
                if letters_from_path(state, path, (er, ec), ch) == target_word:
                    return {
                        "row": er,
                        "col": ec,
                        "letter": ch,
                        "path": [Coord(row=r, col=c) for r, c in path],
                        "word": target_word,
                    }
    return None


def generate_moves_for_lengths(
    state: GameState,
    lengths: set[int],
    limit_words: int,
    max_results: int,
    excluded: set[str] | None = None,
) -> list[dict]:
    """Find legal moves for the given word lengths.

    excluded: words to skip entirely (for bot: pass state.usedWords to prevent
              any repetition; for suggestions: pass recent few words).
              Defaults to the last-3-moves window used by the validator.
    """
    available = board_letters_set(state)
    if excluded is None:
        excluded = {m.word for m in state.moveHistory[-3:] if m.moveType == "WORD"}
    # All letters available because bot/player places exactly one new letter
    all_letters = available | set(_ALL_LETTERS)

    def board_overlap(w: str) -> int:
        """Count letters in w that already exist on board — higher = more likely to have a valid path."""
        return sum(1 for c in w if c in available)

    words = sorted(
        (w for w in get_words() if len(w) in lengths and w not in excluded and can_spell_from_board(w, all_letters)),
        # Prefer words that use more existing board letters (faster to find a path),
        # tie-break: longer words first (stronger moves), then alphabetical
        key=lambda w: (-board_overlap(w), -len(w), w),
    )
    results = []
    for word in words[:limit_words]:
        move = find_word_path_for_target(state, word)
        if move:
            results.append(move)
            if len(results) >= max_results:
                break
    return results


def simulate_move(state: GameState, move):
    return validate_and_apply_move(clone_state(state), move["row"], move["col"], move["letter"], move["path"])



def _jp_word_length_priority(word: str) -> float:
    """JP v18 length curve for bot evaluation.

    3-kana words remain valid tactical glue, but 4/5-kana words should be
    visibly preferred so the game shows heavier, Balatro-like hands.
    """
    if _LANG != "ja":
        return 0.0
    n = len(_norm_word(word))
    if n <= 2:
        return -6.0
    if n == 3:
        return 0.0
    if n == 4:
        return 18.0
    if n >= 5:
        return 32.0
    return 0.0


def _candidate_move_quality(move: dict) -> float:
    """Prefer longer natural words; JP v18 strongly weights 4/5-kana words."""
    w = _norm_word(move.get("word") or "")
    length = len(w)
    gain = move.get("territory_gain", 0) or 0

    if _LANG == "ja":
        q = gain * 0.35 + _jp_word_length_priority(w)
        if length == 3:
            q -= 4.0
        if not _is_ui_word(w):
            q -= 100
        return q

    q = gain
    if length >= 5:
        q += 4
    elif length == 4:
        q += 2
    elif length == 3:
        q += 0.5
    if not _is_ui_word(w):
        q -= 100
    return q


def evaluate_state_for_player(state: GameState, player: str) -> float:
    opponent = other_player(player)
    return (
        (total_score(state, player) - total_score(state, opponent)) * 5.0
        + (count_territory(state, player) - count_territory(state, opponent)) * 2.2
        + (count_locked_cells(state, player) - count_locked_cells(state, opponent)) * 4.0
    )



def _rank_jp_bot_moves(moves: list[dict], max_results: int) -> list[dict]:
    """Rank JP bot moves so the bot does not stop at the first 3-kana word.

    Goals:
    - reduce Seed fallback
    - allow 2-kana connection words
    - prefer 4-5 kana words when available
    - keep player-facing words clean via ja_words_ui
    """
    if _LANG != "ja":
        return moves[:max_results]

    def score(m: dict) -> float:
        w = _norm_word(m.get("word", ""))
        n = len(w)
        # Strongly reward readable long Japanese words, but do not remove 2-kana.
        length_bonus = _jp_word_length_priority(w)
        # Prefer moves that reuse more existing letters; less random seeding feeling.
        path_len = len(m.get("path", []) or [])
        center_bonus = 0.0
        try:
            r = int(m.get("row", 0)); c = int(m.get("col", 0))
            center_bonus = 2.0 - (abs(r - BOARD_SIZE // 2) + abs(c - BOARD_SIZE // 2)) * 0.15
        except Exception:
            pass
        return length_bonus + path_len * 0.25 + center_bonus

    dedup = {}
    for m in moves:
        w = _norm_word(m.get("word", ""))
        if not w:
            continue
        if w not in dedup or score(m) > score(dedup[w]):
            dedup[w] = m

    ranked = sorted(dedup.values(), key=score, reverse=True)
    return ranked[:max_results]


def _fast_bot_moves(state: GameState, max_len: int, max_results: int, excluded: set) -> list[dict]:
    """
    Fast bot move finder.

    EN keeps the V23 lightweight limits.
    JA widens search because kana words are shorter and the v1 bot overused Seed.
    """
    import random
    words = get_words()
    results = []
    LETTERS = _ALL_LETTERS

    placeable = get_placeable_empty_cells(state)

    if _LANG == "ja":
        # Wider JP search: v1 averaged 25 Seed moves because 4 cells / len4 was too narrow.
        cell_limit = 15
        start_limit = 5
        effective_len = min(max_len, 5)
        result_soft_cap = max_results * 12
    else:
        cell_limit = 4
        start_limit = 3
        effective_len = min(max_len, 4)
        result_soft_cap = max_results

    if len(placeable) > cell_limit:
        placeable = random.sample(placeable, cell_limit)

    for (er, ec) in placeable:
        starts = [(er, ec)]
        for nr, nc in get_neighbors(er, ec):
            if state.board[nr][nc].letter:
                starts.append((nr, nc))
        starts = starts[:start_limit]

        for start in starts:
            stack = [([start], frozenset([start]))]
            while stack:
                path, visited = stack.pop()
                plen = len(path)

                if plen >= _WORD_MIN and (er, ec) in set(path):
                    for placed_letter in LETTERS:
                        word = letters_from_path(state, path, (er, ec), placed_letter)
                        if word and word in words and word not in excluded and _is_bot_word(word):
                            results.append({
                                "row": er, "col": ec,
                                "letter": placed_letter,
                                "path": [Coord(row=r, col=c) for r, c in path],
                                "word": word,
                            })
                            if _LANG != "ja" and len(results) >= max_results:
                                return results
                            if _LANG == "ja" and len(results) >= result_soft_cap:
                                return _rank_jp_bot_moves(results, max_results)

                if plen >= effective_len:
                    continue

                r, c = path[-1]
                for nr, nc in get_neighbors(r, c):
                    if (nr, nc) in visited:
                        continue
                    if (nr, nc) != (er, ec) and not state.board[nr][nc].letter:
                        continue
                    stack.append((path + [(nr, nc)], visited | {(nr, nc)}))

    return _rank_jp_bot_moves(results, max_results) if _LANG == "ja" else results[:max_results]


def generate_normal_moves(state: GameState) -> list[dict]:
    used = set(state.usedWords)
    if _LANG == "ja":
        return _fast_bot_moves(state, max_len=5, max_results=14, excluded=used)
    return _fast_bot_moves(state, max_len=4, max_results=5, excluded=used)


def generate_strong_moves(state: GameState) -> list[dict]:
    used = set(state.usedWords)
    if _LANG == "ja":
        return _fast_bot_moves(state, max_len=5, max_results=20, excluded=used)
    return _fast_bot_moves(state, max_len=4, max_results=8, excluded=used)



def _is_river_opening(state: GameState) -> bool:
    return "RIVER" in str(getattr(state, "openingName", "") or "").upper()

def _river_lead_state(state: GameState, player: str) -> bool:
    """True when River opening is likely to snowball for the current bot.

    V16 targets the observed outliers:
    RIVER OPENING × Raider/Defender/Expander × lead >= 6.
    """
    style = _effective_bot_style(state, player)
    if style not in ("Raider", "Defender", "Expander"):
        return False
    lead = -get_score_gap(state, player)  # positive = player ahead
    return _is_river_opening(state) and lead >= 6

def _river_opening_dampener(state: GameState, last: MoveHistoryItem, player: str) -> float:
    """Penalty for crushing River-opening moves while already ahead.

    This does not change rules or scoring. It only changes Bot choice, so
    River Opening remains playable but stops producing repeated gap-20 games.
    """
    if not _river_lead_state(state, player):
        return 0.0

    labels = last.comboLabels or []
    penalty = 0.0
    penalty += (last.captureCount or 0) * 5.0
    penalty += (last.fortifiedCellsGained or 0) * 3.0
    penalty += max(0, (last.territoryGained or 0) - 2) * 2.2
    if "BRIDGE" in labels:
        penalty += 6.0
    if "MAJOR CAPTURE" in labels:
        penalty += 5.0
    if "FORTIFY CHAIN" in labels:
        penalty += 4.0
    return penalty





def _jp_blue_builder_early_contest(state: GameState, player: str) -> bool:
    """JP v16: BLUE Builder needs early contest pressure in large-dictionary JA.

    v15 showed Defender was not the root cause; Builder as BLUE second player
    was also RED-biased. For turns 1-8, BLUE Builder is evaluated with Raider-like
    contest incentives.
    """
    return (
        _LANG == "ja"
        and player == "BLUE"
        and (getattr(state, "botStyle", "") or "") == "Builder"
        and int(getattr(state, "turn", 0) or 0) <= 8
    )


def _jp_blue_builder_contest_bonus(state: GameState, last: MoveHistoryItem, player: str) -> float:
    if not _jp_blue_builder_early_contest(state, player):
        return 0.0
    labels = last.comboLabels or []
    lead = -get_score_gap(state, player)
    bonus = 0.0
    bonus += (last.captureCount or 0) * 5.5
    bonus += max(0, (last.territoryGained or 0) - 1) * 1.5
    bonus += 3.5 if "BRIDGE" in labels else 0.0
    bonus += 3.0 if "CUT" in labels else 0.0
    bonus += 2.0 if "CAPTURE" in labels or "MAJOR CAPTURE" in labels else 0.0
    # Builder still likes structure, so do not punish fortify as strongly as Defender.
    bonus -= (last.fortifiedCellsGained or 0) * 1.2

    # Keep anti-snowball behavior if BLUE already pulled ahead.
    if lead >= 6:
        return bonus * 0.20
    if lead >= 3:
        return bonus * 0.50
    return bonus


def _jp_blue_defender_attacker(state: GameState, player: str) -> bool:
    """JA large-dictionary correction.

    BLUE as second-player Defender was weak because JP rules suppress short-word
    LOCK creation. In that situation, Defender must contest territory like a
    light Raider during evaluation.
    """
    return _LANG == "ja" and player == "BLUE" and (getattr(state, "botStyle", "") or "") == "Defender"


def _jp_blue_defender_attack_bonus(state: GameState, last: MoveHistoryItem, player: str) -> float:
    """Explicit attack/contest bonus for BLUE Defender.

    This is stronger than changing style names because it directly affects the
    same score line that chooses moves. It rewards captures and territory contest,
    and de-emphasizes fortify-only play.
    """
    if not _jp_blue_defender_attacker(state, player):
        return 0.0
    labels = last.comboLabels or []
    lead = -get_score_gap(state, player)  # positive = BLUE already ahead
    bonus = 0.0
    bonus += (last.captureCount or 0) * 7.0
    bonus += max(0, (last.territoryGained or 0) - 1) * 1.8
    bonus += 4.0 if "BRIDGE" in labels else 0.0
    bonus += 3.0 if "CUT" in labels else 0.0
    bonus += 2.0 if "CAPTURE" in labels or "MAJOR CAPTURE" in labels else 0.0
    bonus -= (last.fortifiedCellsGained or 0) * 3.0

    # If already ahead, keep anti-snowball behavior.
    if lead >= 6:
        return bonus * 0.15
    if lead >= 3:
        return bonus * 0.45
    return bonus


def _effective_bot_style(state: GameState, player: str) -> str:
    """Return the style actually used for evaluation.

    JP v14:
    - Second-player Defender behaves as Raider in JA large-dictionary games.
    - This is also reinforced directly in choose_bot_move scoring.
    """
    style = getattr(state, "botStyle", "") or ""

    if _jp_blue_defender_attacker(state, player):
        return "Raider"

    # JP v16: BLUE Builder uses Raider-like priorities only in the opening.
    if _jp_blue_builder_early_contest(state, player):
        return "Raider"

    if player == "BLUE" and style == "Expander" and int(getattr(state, "turn", 0) or 0) <= 10:
        return "Builder"
    return style

def _bot_style_bonus(state: GameState, last: MoveHistoryItem, move: dict, player: str) -> float:
    """Make visible Bot Style meaningful without making one style dominant."""
    style = _effective_bot_style(state, player)
    labels = last.comboLabels or []
    word = (move.get("word") or last.word or "").upper()
    length = len(word)
    lead = -get_score_gap(state, player)     # positive = player ahead
    behind = get_score_gap(state, player)    # positive = player behind

    val = 0.0

    # JP v14: BLUE Defender needs direct contest incentives, not fortify-only play.
    if _jp_blue_defender_attacker(state, player):
        val += _jp_blue_defender_attack_bonus(state, last, player)
    if _jp_blue_builder_early_contest(state, player):
        val += _jp_blue_builder_contest_bonus(state, last, player)

    if length >= 5:
        val += 5.0
    elif length == 4:
        val += 2.5
    elif length == 3 and last.captureCount <= 0 and "BRIDGE" not in labels and "CUT" not in labels:
        val -= 5.0

    if style == "Raider":
        val += (last.captureCount or 0) * 2.5
        val += 1.5 if "MAJOR CAPTURE" in labels else 0.0
        if lead >= 6:
            val -= (last.captureCount or 0) * 4.5
            val -= max(0, (last.territoryGained or 0) - 3) * 1.6
    elif style == "Defender":
        # Defender should not only lock; it must relieve pressure by reclaiming.
        val += (last.fortifiedCellsGained or 0) * 1.2
        val += 3.0 if "BRIDGE" in labels else 0.0
        if behind >= 4:
            val += (last.captureCount or 0) * 6.0
            val += max(0, (last.territoryGained or 0) - 2) * 1.4
            if last.captureCount <= 0 and "BRIDGE" not in labels:
                val -= (last.fortifiedCellsGained or 0) * 2.2
        if lead >= 8:
            val -= (last.fortifiedCellsGained or 0) * 1.5
    elif style == "Builder":
        val += (last.fortifiedCellsGained or 0) * 1.8
        val += 2.0 if "BRIDGE" in labels else 0.0
    elif style == "Cutter":
        val += 4.0 if "CUT" in labels else 0.0
        val += 1.5 if "BRIDGE" in labels else 0.0
    elif style == "Expander":
        val += max(0, (last.territoryGained or 0) - 2) * 1.3
        val += 2.0 if "LONG PATH" in labels else 0.0
    # V16: suppress River Opening snowball only when already ahead.
    val -= _river_opening_dampener(state, last, player)
    return val


def choose_bot_move(state: GameState):
    if state.botLevel == "normal":
        moves = generate_normal_moves(state)
        if not moves:
            return None
        player = state.currentPlayer
        # positive if bot/current player is already ahead
        lead = -get_score_gap(state, player)
        def quick_score(m):
            try:
                ns = simulate_move(state, m)
                base = evaluate_state_for_player(ns, player)
                last = ns.moveHistory[-1]
                labels = last.comboLabels or []
                bonus = sum(3 if l in ("BRIDGE","CUT") else
                            2 if l in ("CAPTURE","CROSS WORD") else 1
                            for l in labels)
                # Rubberband: when Normal bot is already ahead, stop piling on
                # captures/bridges. It should still play, but not crush beginners.
                style_bonus = _bot_style_bonus(state, last, m, player)
                if _LANG == "ja":
                    bonus += _jp_word_length_priority(m.get("word", ""))
                if _jp_blue_defender_attacker(state, player):
                    # Directly influence the selected move, not just style identity.
                    bonus += _jp_blue_defender_attack_bonus(state, last, player)
                if _jp_blue_builder_early_contest(state, player):
                    bonus += _jp_blue_builder_contest_bonus(state, last, player)
                if _LANG == "ja":
                    # JP v11 anti-snowball: in large dictionaries, strong moves are common.
                    swing_penalty = (last.captureCount or 0) * 5
                    swing_penalty += 5 if "BRIDGE" in labels else 0
                    swing_penalty += 5 if "CUT" in labels else 0
                    swing_penalty += 4 if "FORTIFY CHAIN" in labels else 0
                    swing_penalty += max(0, (last.territoryGained or 0) - 3) * 1.5
                    if lead >= 6:
                        bonus -= swing_penalty
                    elif lead >= 3:
                        bonus -= swing_penalty * 0.55
                if lead >= 8:
                    bonus -= (last.captureCount or 0) * 8
                    bonus -= 7 if "BRIDGE" in labels else 0
                    bonus -= 4 if "MAJOR CAPTURE" in labels else 0
                    bonus -= max(0, (last.territoryGained or 0) - 2) * 2
                    return word_score(m["word"]) + style_bonus - bonus
                return base + bonus + style_bonus
            except Exception:
                return word_score(m["word"])
        if lead >= 8 or _river_lead_state(state, player):
            # Choose a non-crushing move from the lower-middle band, not the maximum.
            scored = sorted([(quick_score(m), m) for m in moves], key=lambda x: x[0])
            return scored[min(len(scored)-1, max(0, len(scored)//3))][1]
        return max(moves, key=quick_score)

    # Strong bot: score all candidates, pick best
    legal_moves = generate_strong_moves(state)
    if not legal_moves:
        return None
    player = state.currentPlayer
    best_move = None
    best_value = -10**9
    for move in legal_moves:
        try:
            next_state = simulate_move(state, move)
        except Exception:
            continue
        my_value = evaluate_state_for_player(next_state, player)
        last = next_state.moveHistory[-1]
        # Role bonus weighting — prefer moves that earn strategic combos
        combo_value = 0
        for label in (last.comboLabels or []):
            if label in ("BRIDGE", "CUT"):           combo_value += 8
            elif label in ("CROSS WORD", "FORTIFY CHAIN"): combo_value += 5
            elif label in ("MAJOR CAPTURE", "COMEBACK"): combo_value += 4
            elif label in ("LONG PATH", "CAPTURE"):  combo_value += 3
            elif label in ("EDGE REACH", "FIRST CAPTURE", "FRONTLINE PUSH"): combo_value += 2
            elif label in ("BEACHHEAD",):            combo_value += 3
            else:                                     combo_value += 1
        value = my_value + word_score(move["word"]) * 1.4 + combo_value + _bot_style_bonus(state, last, move, player)
        if _LANG == "ja":
            value += _jp_word_length_priority(move.get("word", ""))
        if _jp_blue_defender_attacker(state, player):
            value += _jp_blue_defender_attack_bonus(state, last, player)
        if _jp_blue_builder_early_contest(state, player):
            value += _jp_blue_builder_contest_bonus(state, last, player)
        if _LANG == "ja":
            lead_now = -get_score_gap(state, player)
            swing_penalty = (last.captureCount or 0) * 4
            swing_penalty += 5 if "BRIDGE" in (last.comboLabels or []) else 0
            swing_penalty += 5 if "CUT" in (last.comboLabels or []) else 0
            swing_penalty += 4 if "FORTIFY CHAIN" in (last.comboLabels or []) else 0
            if lead_now >= 6:
                value -= swing_penalty
            elif lead_now >= 3:
                value -= swing_penalty * 0.5
        value -= _river_opening_dampener(state, last, player) * 0.6
        if value > best_value:
            best_value = value
            best_move = move
    return best_move



def choose_demo_bot_move(state: GameState):
    """Trailer / Watch Demo move picker.

    This deliberately favors readable, map-changing turns over raw win rate.
    It makes Spectator Mode useful as a 30-second explanation tool.
    """
    legal_moves = _fast_bot_moves(state, max_len=5, max_results=80, excluded=set(state.usedWords))
    # Strict Demo Dictionary: Watch Demo should show common, readable words only.
    legal_moves = [m for m in legal_moves if _is_demo_word(m.get("word", ""))]
    if not legal_moves:
        return None

    player = state.currentPlayer
    best_move = None
    best_value = -10**9

    for move in legal_moves:
        try:
            ns = simulate_move(state, move)
            last = ns.moveHistory[-1]
        except Exception:
            continue

        word = _norm_word(last.word or "")
        combos = last.comboLabels or []
        is_demo = _is_demo_word(word)

        value = 0
        value += last.territoryGained * 2.2
        value += last.captureCount * 10
        value += last.fortifiedCellsGained * 4
        value += word_score(word) * 1.2
        value += 9 if "BRIDGE" in combos else 0
        value += 7 if "CUT" in combos else 0
        value += 6 if "FORTIFY CHAIN" in combos else 0
        value += 5 if "MAJOR CAPTURE" in combos else 0
        value += 3 if "LONG PATH" in combos else 0
        value += 10 if any(str(c).startswith("SYNERGY") for c in combos) else 0

        # demo readability
        if word in _DEMO_WORD_PROMOTE:
            value += 7
        if not is_demo:
            value -= 12
        if len(word) == 3 and last.captureCount == 0 and "BRIDGE" not in combos:
            value -= 4

        # prefer visible map changes over tiny score nudges
        if last.territoryGained < 3 and not combos:
            value -= 5

        # Don't make the same kind of tiny move again and again.
        if state.moveHistory:
            prev = state.moveHistory[-1]
            if prev.moveType == "WORD" and prev.word and len(prev.word) == len(word) == 3:
                value -= 3

        if value > best_value:
            best_value = value
            best_move = move

    return best_move


def apply_demo_bot_move(state: GameState):
    if state.winner:
        return state
    move = choose_demo_bot_move(state)
    if move:
        try:
            return validate_and_apply_move(
                state, move["row"], move["col"], move["letter"], move["path"]
            )
        except Exception:
            pass
    return apply_bot_move(state)



def choose_bot_move_rescue(state: GameState):
    """JP V3 final broad search before Seed.

    The normal bot still ranks moves. If no move is found, JP tries a wider
    Valid-dictionary search so it plays a word instead of Seed whenever possible.
    """
    if _LANG != "ja":
        return None
    used = set(state.usedWords)
    try:
        moves = _fast_bot_moves(state, max_len=5, max_results=30, excluded=used)
        if moves:
            # Prefer actual words, especially 4–5 kana, but any valid word beats Seed.
            return max(
                moves,
                key=lambda m: (
                    word_score(m.get("word", "")) * 3
                    + len(m.get("path", []) or [])
                    + (5 if len(_norm_word(m.get("word", ""))) >= 4 else 0)
                )
            )
    except Exception:
        return None
    return None


def choose_seed_move(state: GameState):
    letters = (["さ","く","ら","み","ず","そ","ら","は","な","か","ぜ","も","り"] if _LANG == "ja" else list("ETAONRISL"))
    cells = get_placeable_empty_cells(state)
    if not cells:
        return None
    r, c = random.choice(cells)
    return r, c, random.choice(letters)


def apply_bot_move(state: GameState):
    if state.winner:
        return state
    # Try word move
    move = choose_bot_move(state)
    if move:
        try:
            return validate_and_apply_move(
                state, move["row"], move["col"], move["letter"], move["path"]
            )
        except Exception:
            pass  # Fall through to rescue / seed move

    # JP V3: one more broad Valid-dictionary search before Seed.
    rescue = choose_bot_move_rescue(state)
    if rescue:
        try:
            return validate_and_apply_move(
                state, rescue["row"], rescue["col"], rescue["letter"], rescue["path"]
            )
        except Exception:
            pass

    # Fallback: seed move
    seed = choose_seed_move(state)
    if seed:
        try:
            return apply_seed_move(state, *seed)
        except Exception:
            pass
    # Last resort: pass
    return pass_turn(state)


# WT_JA_ENGINE_MARKET_RUNTIME_SANITIZER_20260606
# Safety net: Japanese version must never emit A-Z or FREE in the letter market.
def _wt_ja_is_kana_tile(x):
    return isinstance(x, str) and len(x) == 1 and ("?" <= x <= "?" or x == "?")

def _wt_ja_clean_market_seq(seq, existing=None):
    if globals().get("_LANG") != "ja":
        return seq

    import random as _r

    existing = set(existing or [])
    pool = []
    try:
        pool = [x for x in _ALL_LETTERS if _wt_ja_is_kana_tile(x)]
    except Exception:
        pool = []

    if not pool:
        pool = list("???????????????????????????????????????????????????????????????????????")

    out = []
    for x in seq or []:
        if _wt_ja_is_kana_tile(x) and x not in out:
            out.append(x)

    while len(out) < 3:
        choices = [x for x in pool if x not in existing and x not in out]
        if not choices:
            choices = pool
        out.append(_r.choice(choices))

    return out[:3]

def _wt_ja_clean_market_pair(pair):
    if globals().get("_LANG") != "ja":
        return pair

    try:
        active, preview = pair
    except Exception:
        return pair

    active2 = _wt_ja_clean_market_seq(active)
    preview2 = _wt_ja_clean_market_seq(preview, existing=set(active2))
    return active2, preview2

try:
    _wt_orig_create_initial_market = create_initial_market
    def create_initial_market(*args, **kwargs):
        return _wt_ja_clean_market_pair(_wt_orig_create_initial_market(*args, **kwargs))
except Exception:
    pass

try:
    _wt_orig_advance_market = advance_market
    def advance_market(*args, **kwargs):
        return _wt_ja_clean_market_pair(_wt_orig_advance_market(*args, **kwargs))
except Exception:
    pass


# WT_JA_UNICODE_SAFE_MARKET_FIX_20260606_V2
# Final safety net: Japanese Letter Market must never emit ASCII or mojibake "?".

def _wt_ja_unicode_pool_v2():
    try:
        from language_profiles import ja as _ja
        pool = [x for x in getattr(_ja, "ALL_KANA", []) if isinstance(x, str) and len(x) == 1]
        if pool:
            return pool
    except Exception:
        pass
    return list('あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ')

def _wt_ja_is_kana_tile_v2(x):
    if not isinstance(x, str) or len(x) != 1:
        return False
    o = ord(x)
    return (0x3041 <= o <= 0x3096) or x == "\u30fc"

def _wt_ja_clean_market_seq_v2(seq, existing=None):
    if globals().get("_LANG") != "ja":
        return seq

    import random as _r

    existing = set(existing or [])
    pool = _wt_ja_unicode_pool_v2()
    out = []

    for x in seq or []:
        if _wt_ja_is_kana_tile_v2(x) and x not in out:
            out.append(x)

    while len(out) < 3:
        choices = [x for x in pool if x not in existing and x not in out]
        if not choices:
            choices = pool
        out.append(_r.choice(choices))

    return out[:3]

def _wt_ja_clean_market_pair_v2(pair):
    if globals().get("_LANG") != "ja":
        return pair

    try:
        active, preview = pair
    except Exception:
        return pair

    active2 = _wt_ja_clean_market_seq_v2(active)
    preview2 = _wt_ja_clean_market_seq_v2(preview, existing=set(active2))
    return active2, preview2

try:
    _wt_ja_orig_create_initial_market_v2 = create_initial_market
    def create_initial_market(*args, **kwargs):
        return _wt_ja_clean_market_pair_v2(_wt_ja_orig_create_initial_market_v2(*args, **kwargs))
except Exception:
    pass

try:
    _wt_ja_orig_advance_market_v2 = advance_market
    def advance_market(*args, **kwargs):
        return _wt_ja_clean_market_pair_v2(_wt_ja_orig_advance_market_v2(*args, **kwargs))
except Exception:
    pass


# WT_JA_FINAL_STABLE_MARKET_FIX_20260606
# Japanese Letter Market must be stable and kana-only.
# It should change only when a move consumes a card or the backend advances the market.

def _wt_ja_final_pool():
    return list('あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ')

def _wt_ja_final_is_kana(x):
    if not isinstance(x, str) or len(x) != 1:
        return False
    o = ord(x)
    return (0x3041 <= o <= 0x3096) or x == "\u30fc"

def _wt_ja_final_clean_seq(seq, existing=None, offset=0):
    if globals().get("_LANG") != "ja":
        return seq

    existing = set(existing or [])
    pool = _wt_ja_final_pool()
    out = []

    for x in seq or []:
        if _wt_ja_final_is_kana(x) and x not in out:
            out.append(x)

    i = offset
    while len(out) < 3:
        c = pool[i % len(pool)]
        i += 1
        if c not in out and c not in existing:
            out.append(c)

    return out[:3]

def _wt_ja_final_clean_pair(pair):
    if globals().get("_LANG") != "ja":
        return pair

    try:
        active, preview = pair
    except Exception:
        return pair

    active2 = _wt_ja_final_clean_seq(active, offset=0)
    preview2 = _wt_ja_final_clean_seq(preview, existing=set(active2), offset=7)
    return active2, preview2

try:
    _wt_ja_orig_create_initial_market_final = create_initial_market
    def create_initial_market(*args, **kwargs):
        return _wt_ja_final_clean_pair(_wt_ja_orig_create_initial_market_final(*args, **kwargs))
except Exception:
    pass

try:
    _wt_ja_orig_advance_market_final = advance_market
    def advance_market(*args, **kwargs):
        return _wt_ja_final_clean_pair(_wt_ja_orig_advance_market_final(*args, **kwargs))
except Exception:
    pass


# WT_JA_FINAL_MARKET_STABLE_NO_ASCII_20260606
# Final guard: Japanese Letter Market must emit kana only, never A-Z or "?".

def _wt_ja_final_pool_no_ascii():
    return list('あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ')

def _wt_ja_final_is_kana_no_ascii(x):
    if not isinstance(x, str) or len(x) != 1:
        return False
    o = ord(x)
    return (0x3041 <= o <= 0x3096) or x == "\u30fc"

def _wt_ja_final_clean_seq_no_ascii(seq, existing=None, offset=0):
    if globals().get("_LANG") != "ja":
        return seq

    existing = set(existing or [])
    pool = _wt_ja_final_pool_no_ascii()
    out = []

    for x in seq or []:
        if _wt_ja_final_is_kana_no_ascii(x) and x not in out:
            out.append(x)

    i = offset
    while len(out) < 3:
        c = pool[i % len(pool)]
        i += 1
        if c not in out and c not in existing:
            out.append(c)

    return out[:3]

def _wt_ja_final_clean_pair_no_ascii(pair):
    if globals().get("_LANG") != "ja":
        return pair
    try:
        active, preview = pair
    except Exception:
        return pair
    active2 = _wt_ja_final_clean_seq_no_ascii(active, offset=0)
    preview2 = _wt_ja_final_clean_seq_no_ascii(preview, existing=set(active2), offset=7)
    return active2, preview2

try:
    _wt_orig_create_initial_market_final_no_ascii = create_initial_market
    def create_initial_market(*args, **kwargs):
        return _wt_ja_final_clean_pair_no_ascii(_wt_orig_create_initial_market_final_no_ascii(*args, **kwargs))
except Exception:
    pass

try:
    _wt_orig_advance_market_final_no_ascii = advance_market
    def advance_market(*args, **kwargs):
        return _wt_ja_final_clean_pair_no_ascii(_wt_orig_advance_market_final_no_ascii(*args, **kwargs))
except Exception:
    pass

# WT_JA_DEFINITIVE_MARKET_KANA_ONLY_20260606
def _wt_ja_def_pool():
    return list('あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ')
def _wt_ja_def_is_kana(x):
    return isinstance(x,str) and len(x)==1 and ((0x3041 <= ord(x) <= 0x3096) or x == "\u30fc")
def _wt_ja_def_clean_seq(seq, existing=None, offset=0):
    if globals().get("_LANG") != "ja": return seq
    existing=set(existing or []); pool=_wt_ja_def_pool(); out=[]
    for x in seq or []:
        if _wt_ja_def_is_kana(x) and x not in out: out.append(x)
    i=offset
    while len(out)<3:
        c=pool[i % len(pool)]; i+=1
        if c not in out and c not in existing: out.append(c)
    return out[:3]
def _wt_ja_def_clean_pair(pair):
    if globals().get("_LANG") != "ja": return pair
    try: active, preview = pair
    except Exception: return pair
    active2=_wt_ja_def_clean_seq(active, offset=0)
    preview2=_wt_ja_def_clean_seq(preview, existing=set(active2), offset=7)
    return active2, preview2
try:
    _wt_ja_orig_create_initial_market_def = create_initial_market
    def create_initial_market(*args, **kwargs):
        return _wt_ja_def_clean_pair(_wt_ja_orig_create_initial_market_def(*args, **kwargs))
except Exception: pass
try:
    _wt_ja_orig_advance_market_def = advance_market
    def advance_market(*args, **kwargs):
        return _wt_ja_def_clean_pair(_wt_ja_orig_advance_market_def(*args, **kwargs))
except Exception: pass


# WT_JA_STABLE_MARKET_AND_SOFT_BOT_20260607
# Purpose:
# 1) Letter Market should not feel like it reshuffles every operation.
#    On a successful human move, replace only the consumed tile.
# 2) Normal bot should be playable for humans, not maximizer-level.
#    Strong bot remains unchanged.

def _wt_ja_soft_pool_20260607():
    return list("あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをんがぎぐげござじずぜぞだぢづでどばびぶべぼぱぴぷぺぽ")

def _wt_ja_is_kana_20260607(x):
    return isinstance(x, str) and len(x) == 1 and ((0x3041 <= ord(x) <= 0x3096) or x == "\u30fc")

def _wt_ja_pick_fill_20260607(existing, seed_offset=0):
    pool = _wt_ja_soft_pool_20260607()
    existing = set(existing or [])
    for i in range(len(pool)):
        c = pool[(i + seed_offset) % len(pool)]
        if c not in existing:
            return c
    return pool[seed_offset % len(pool)]

try:
    _wt_ja_orig_advance_market_20260607 = advance_market

    def advance_market(state, used_letter):
        if globals().get("_LANG") != "ja":
            return _wt_ja_orig_advance_market_20260607(state, used_letter)

        active = list(getattr(state, "marketLetters", []) or [])
        preview = list(getattr(state, "previewLetters", []) or [])

        active = [x for x in active if _wt_ja_is_kana_20260607(x) or x == "*"][:3]
        preview = [x for x in preview if _wt_ja_is_kana_20260607(x) and x not in active][:3]

        while len(active) < 3:
            active.append(_wt_ja_pick_fill_20260607(active, seed_offset=len(active)))

        while len(preview) < 3:
            preview.append(_wt_ja_pick_fill_20260607(active + preview, seed_offset=7 + len(preview)))

        # Replace only the consumed tile.
        new_active = active[:3]
        try:
            idx = new_active.index(used_letter)
        except ValueError:
            idx = 0

        replacement = preview[0] if preview else _wt_ja_pick_fill_20260607(new_active, seed_offset=11)
        new_active[idx] = replacement

        new_preview = [x for x in preview[1:] if x not in new_active]
        while len(new_preview) < 3:
            new_preview.append(_wt_ja_pick_fill_20260607(new_active + new_preview, seed_offset=17 + len(new_preview)))

        return new_active[:3], new_preview[:3]

except Exception:
    pass


try:
    _wt_ja_orig_choose_bot_move_20260607 = choose_bot_move

    def _wt_ja_soft_score_move_20260607(state, move, player):
        try:
            ns = simulate_move(state, move)
            last = ns.moveHistory[-1]
            labels = set(last.comboLabels or [])

            word = _norm_word(move.get("word", ""))
            n = len(word)

            score = 0.0
            score += word_score(word) * 0.8
            score += len(move.get("path", []) or []) * 0.2
            score += max(0, (last.territoryGained or 0)) * 0.45

            # Normal bot should not crush humans with tactical bursts.
            score -= (last.captureCount or 0) * 2.8
            if "BRIDGE" in labels:
                score -= 2.5
            if "CUT" in labels:
                score -= 2.5
            if "FORTIFY CHAIN" in labels:
                score -= 1.8

            # Very long words are impressive, but Normal should not always prefer them.
            if globals().get("_LANG") == "ja":
                if n >= 5:
                    score -= 2.0
                elif n == 4:
                    score += 0.5
                elif n <= 2:
                    score -= 2.0

            # If bot/current player is already ahead, become gentler.
            try:
                gap = get_score_gap(state, player)  # positive = player is behind
                if gap < -3:
                    score -= (last.captureCount or 0) * 4.0
                    score -= max(0, (last.territoryGained or 0) - 2) * 1.5
                    if "BRIDGE" in labels or "CUT" in labels:
                        score -= 3.0
                elif gap > 5:
                    # If bot is losing badly, allow a reasonable comeback.
                    score += max(0, (last.territoryGained or 0)) * 0.35
            except Exception:
                pass

            return score
        except Exception:
            try:
                return word_score(move.get("word", "")) * 0.5
            except Exception:
                return 0.0

    def choose_bot_move(state):
        # Strong bot remains unchanged.
        if getattr(state, "botLevel", "normal") != "normal":
            return _wt_ja_orig_choose_bot_move_20260607(state)

        moves = generate_normal_moves(state)
        if not moves:
            return None

        player = state.currentPlayer
        scored = sorted(
            [(_wt_ja_soft_score_move_20260607(state, m, player), m) for m in moves],
            key=lambda x: x[0],
            reverse=True
        )

        if not scored:
            return None

        # Do not pick the best move. Pick upper-middle / middle.
        # This keeps the bot active but beatable.
        try:
            gap = get_score_gap(state, player)
        except Exception:
            gap = 0

        if gap > 6:
            # Bot/current player is losing: allow slightly stronger move.
            idx = min(len(scored) - 1, max(0, len(scored) // 4))
        elif gap < -3:
            # Bot/current player is ahead: choose weaker move.
            idx = min(len(scored) - 1, max(0, (len(scored) * 2) // 3))
        else:
            idx = min(len(scored) - 1, max(0, len(scored) // 2))

        return scored[idx][1]

except Exception:
    pass


# WT_JA_EASY_BOT_AND_T2_CAP_20260607
# Adds EASY bot and caps early T2-style bonus stacking.

def _wt_ja_cap_early_t2_bonus_20260607(before_state, temp_state, player, combos, bonus_uncapped, word):
    try:
        if globals().get("_LANG") != "ja":
            return bonus_uncapped

        turn = int(getattr(before_state, "turn", 0) or 0)
        labels = set(combos or [])

        # Opening COMEBACK suppression.
        if turn <= 6 and "COMEBACK" in labels:
            try:
                combos[:] = [c for c in combos if c != "COMEBACK"]
            except Exception:
                pass
            bonus_uncapped = max(0, int(bonus_uncapped) - 1)

        labels = set(combos or [])
        stacked = sum(1 for x in (
            "COMEBACK",
            "SECOND PLAYER INITIATIVE",
            "MEGA TERRITORY",
            "FIRST CAPTURE",
            "EDGE REACH",
        ) if x in labels)

        if turn <= 4 and stacked >= 2:
            return min(int(bonus_uncapped), 2)
        if turn <= 8 and stacked >= 3:
            return min(int(bonus_uncapped), 3)
        if stacked >= 4:
            return min(int(bonus_uncapped), 4)

        return int(bonus_uncapped)
    except Exception:
        return bonus_uncapped


def _wt_ja_easy_move_penalty_20260607(state, move, player):
    try:
        ns = simulate_move(state, move)
        last = ns.moveHistory[-1]
        labels = set(last.comboLabels or [])
        word = _norm_word(move.get("word", ""))
        n = len(word)

        penalty = 0.0

        # Easy prefers simple 3-kana words and avoids tactical bursts.
        if n <= 2:
            penalty += 2.0
        elif n == 3:
            penalty += 0.0
        elif n == 4:
            penalty += 1.5
        else:
            penalty += 5.0

        terr = max(0, int(last.territoryGained or 0))
        cap = max(0, int(last.captureCount or 0))

        penalty += terr * 2.0
        penalty += cap * 8.0

        if "BRIDGE" in labels:
            penalty += 7.0
        if "CUT" in labels:
            penalty += 7.0
        if "MEGA TERRITORY" in labels:
            penalty += 9.0
        if "FIRST CAPTURE" in labels:
            penalty += 4.0
        if "SECOND PLAYER INITIATIVE" in labels:
            penalty += 4.0
        if "COMEBACK" in labels:
            penalty += 5.0

        # If current player is already ahead, become gentler.
        try:
            lead = -get_score_gap(state, player)
            if lead >= 3:
                penalty += terr * 1.5
                penalty += cap * 6.0
                if "BRIDGE" in labels or "CUT" in labels:
                    penalty += 6.0
        except Exception:
            pass

        import random as _r
        penalty += _r.random() * 0.75
        return penalty
    except Exception:
        return 99.0


def _wt_ja_choose_easy_bot_move_20260607(state):
    moves = generate_normal_moves(state)
    if not moves:
        return None

    player = state.currentPlayer
    scored = []

    for m in moves:
        try:
            ns = simulate_move(state, m)
            last = ns.moveHistory[-1]
            labels = set(last.comboLabels or [])
            aggressive = (
                (last.captureCount or 0) > 0
                or "BRIDGE" in labels
                or "CUT" in labels
                or "MEGA TERRITORY" in labels
            )
            scored.append((_wt_ja_easy_move_penalty_20260607(state, m, player), aggressive, m))
        except Exception:
            scored.append((99.0, True, m))

    pool = [x for x in scored if not x[1]]
    if not pool:
        pool = scored

    pool = sorted(pool, key=lambda x: x[0])

    import random as _r
    top_n = min(len(pool), 4)
    return _r.choice(pool[:top_n])[2]


try:
    _wt_ja_choose_bot_move_before_easy_20260607 = choose_bot_move

    def choose_bot_move(state):
        level = str(getattr(state, "botLevel", "normal") or "normal").lower()

        if level == "easy":
            return _wt_ja_choose_easy_bot_move_20260607(state)

        return _wt_ja_choose_bot_move_before_easy_20260607(state)

except Exception:
    pass



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


# WT_QUICK_5X5_BOTH_V2
# Quick mode is a small-board runtime layer. It keeps Standard 7x7 unchanged,
# while allowing new games to be created as 5x5 sessions.
try:
    WT_STANDARD_BOARD_SIZE = int(BOARD_SIZE)
except Exception:
    WT_STANDARD_BOARD_SIZE = 7

try:
    WT_STANDARD_OPENING_COORDS = list(OPENING_COORDS)
except Exception:
    WT_STANDARD_OPENING_COORDS = [(1,3),(2,2),(2,3),(2,4),(2,5),(3,3),(4,3)]

try:
    WT_STANDARD_MAX_TURNS = int(MAX_TURNS)
except Exception:
    WT_STANDARD_MAX_TURNS = 35

WT_QUICK_BOARD_SIZE = 5
WT_QUICK_MAX_TURNS = 20
WT_QUICK_OPENING_COORDS = [(0,2), (1,1), (1,2), (1,3), (2,2)]

def _wt_quick_runtime_size(value=None):
    try:
        n = int(value)
    except Exception:
        n = WT_STANDARD_BOARD_SIZE
    return WT_QUICK_BOARD_SIZE if n == WT_QUICK_BOARD_SIZE else WT_STANDARD_BOARD_SIZE

def _wt_quick_set_runtime(size=None):
    global BOARD_SIZE, OPENING_COORDS, MAX_TURNS
    n = _wt_quick_runtime_size(size)
    BOARD_SIZE = n
    if n == WT_QUICK_BOARD_SIZE:
        OPENING_COORDS = list(WT_QUICK_OPENING_COORDS)
        MAX_TURNS = WT_QUICK_MAX_TURNS
    else:
        OPENING_COORDS = list(WT_STANDARD_OPENING_COORDS)
        MAX_TURNS = WT_STANDARD_MAX_TURNS
    return n

def sync_board_runtime(state):
    """Synchronize module-level board constants with this state's boardSize."""
    return _wt_quick_set_runtime(getattr(state, "boardSize", WT_STANDARD_BOARD_SIZE))

try:
    _WT_QUICK_ORIGINAL_BUILD_INITIAL_STATE_V1
except NameError:
    _WT_QUICK_ORIGINAL_BUILD_INITIAL_STATE_V1 = build_initial_state

def build_initial_state(bot_level: str = "normal", opening_idx: int | None = None, board_mode: str = "standard", board_size: int | None = None) -> GameState:
    mode = str(board_mode or "standard").lower()
    quick = mode in ("quick", "5", "5x5", "quick5", "quick-5x5") or board_size == WT_QUICK_BOARD_SIZE
    runtime_size = _wt_quick_set_runtime(WT_QUICK_BOARD_SIZE if quick else WT_STANDARD_BOARD_SIZE)

    try:
        state = _WT_QUICK_ORIGINAL_BUILD_INITIAL_STATE_V1(bot_level=bot_level, opening_idx=opening_idx)
    except TypeError:
        if opening_idx is None:
            state = _WT_QUICK_ORIGINAL_BUILD_INITIAL_STATE_V1(bot_level=bot_level)
        else:
            state = _WT_QUICK_ORIGINAL_BUILD_INITIAL_STATE_V1(bot_level=bot_level, opening_idx=opening_idx)

    state.boardSize = runtime_size
    try:
        state.synergyState = dict(getattr(state, "synergyState", {}) or {})
        state.synergyState["_boardMode"] = "quick" if quick else "standard"
    except Exception:
        pass
    try:
        if quick and not str(state.openingName).startswith("QUICK 5×5"):
            state.openingName = "QUICK 5×5 · " + str(state.openingName or "OPENING")
    except Exception:
        pass
    return state

def _wt_quick_wrap_state_fn(fn):
    def wrapped(state, *args, **kwargs):
        sync_board_runtime(state)
        return fn(state, *args, **kwargs)
    wrapped.__name__ = getattr(fn, "__name__", "wrapped")
    wrapped.__doc__ = getattr(fn, "__doc__", None)
    return wrapped

for _wt_name in [
    "validate_and_apply_move",
    "apply_seed_move",
    "preview_move",
    "pass_turn",
    "find_candidate_words",
    "find_almost_words",
    "apply_bot_move",
    "apply_demo_bot_move",
    "get_market_stats",
    "get_letter_preview_moves",
    "get_threat_preview",
    "get_placeable_empty_cells",
]:
    _wt_fn = globals().get(_wt_name)
    if callable(_wt_fn) and not getattr(_wt_fn, "_wt_quick_wrapped", False):
        _wt_wrapped = _wt_quick_wrap_state_fn(_wt_fn)
        _wt_wrapped._wt_quick_wrapped = True
        globals()[_wt_name] = _wt_wrapped

