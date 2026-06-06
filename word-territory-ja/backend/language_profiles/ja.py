"""Japanese language profile for Word Territory.

This file is required for clean checkouts because backend/engine.py and
backend/dictionary.py import it when WT_LANG=ja.

Release invariant:
  - backend/language_profiles/__init__.py must exist
  - backend/language_profiles/ja.py must exist
  - engine.py must import without relying on files left over in a developer repo
"""
from __future__ import annotations

import re
import unicodedata

BOARD_SIZE = 7
MIN_WORD_LEN = 2
MAX_WORD_LEN = 6
FRONTLINE_MIN_PATH_LEN = 3

# Common hiragana used by the JP dictionary and letter market.  Small kana are
# accepted by normalize()/is_valid_kana_word(), but are not used as random market
# seeds because they are weak standalone play letters.
ALL_KANA = list(
    "あいうえお"
    "かきくけこ"
    "さしすせそ"
    "たちつてと"
    "なにぬねの"
    "はひふへほ"
    "まみむめも"
    "やゆよ"
    "らりるれろ"
    "わをん"
    "がぎぐげご"
    "ざじずぜぞ"
    "だぢづでど"
    "ばびぶべぼ"
    "ぱぴぷぺぽ"
)

# Light frequency weights for fallback seed/letter-market behavior.  The clean
# v18 release does not use Seed as a normal move, but these values keep emergency
# fallback deterministic and language-aware.
_FREQ_ORDER = "かいきみたさまくしるなりわおこうつあのらはやもとちすんむけそひにれめねばよゆふえろびぎせずがほじぐだてぬげぶぜどごべぞぼ"
KANA_WEIGHTS = {ch: max(1, 80 - i) for i, ch in enumerate(_FREQ_ORDER)}
for ch in ALL_KANA:
    KANA_WEIGHTS.setdefault(ch, 1)

# The opening names are user-facing and appear in match results.  Each seed list
# has seven kana to match engine.OPENING_COORDS.
JP_OPENINGS = [
    ("うみかぜ（海風）", list("うみかぜなみ")),
    ("やまみち（山道）", list("やまみちきす")),
    ("そらかぜ（空）", list("そらかぜくも")),
    ("はなみ（花見）", list("はなみちさく")),
    ("もりみち（森）", list("もりみちなつ")),
    ("みずべ（水辺）", list("みずべしほか")),
    ("こころ（心）", list("こころさかな")),
    ("ほしぞら（星空）", list("ほしぞらみず")),
]

_HIRAGANA_RE = re.compile(r"^[ぁ-ゖー]+$")
_SMALL_KANA = str.maketrans({
    "ぁ": "あ", "ぃ": "い", "ぅ": "う", "ぇ": "え", "ぉ": "お",
    "ゃ": "や", "ゅ": "ゆ", "ょ": "よ", "っ": "つ", "ゎ": "わ",
})


def _katakana_to_hiragana(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            out.append(chr(code - 0x60))
        else:
            out.append(ch)
    return "".join(out)


def normalize(word: str | None) -> str:
    """Normalize user/dictionary input to hiragana-only comparison form."""
    if word is None:
        return ""
    s = unicodedata.normalize("NFKC", str(word)).strip()
    s = re.sub(r"\s+", "", s)
    s = _katakana_to_hiragana(s)
    s = s.translate(_SMALL_KANA)
    return s


def is_valid_kana_word(word: str | None) -> bool:
    w = normalize(word)
    if not (MIN_WORD_LEN <= len(w) <= 12):
        return False
    return bool(_HIRAGANA_RE.match(w))


def is_ui_word(word: str | None) -> bool:
    return is_valid_kana_word(word)


def is_demo_word(word: str | None) -> bool:
    return is_valid_kana_word(word)


# WT_JA_PROFILE_NO_ASCII_MARKET_20260606
# Force Japanese market pools to kana only.
_WT_JA_KANA_POOL = list("???????????????????????????????????????????????????????????????????????")
_WT_JA_KANA_SET = set(_WT_JA_KANA_POOL)

try:
    LETTERS = [x for x in LETTERS if isinstance(x, str) and x in _WT_JA_KANA_SET]
    if not LETTERS:
        LETTERS = list(_WT_JA_KANA_POOL)
except Exception:
    LETTERS = list(_WT_JA_KANA_POOL)

try:
    LETTER_WEIGHTS = {
        k: v for k, v in LETTER_WEIGHTS.items()
        if isinstance(k, str) and k in _WT_JA_KANA_SET
    }
    if not LETTER_WEIGHTS:
        LETTER_WEIGHTS = {k: 1 for k in _WT_JA_KANA_POOL}
except Exception:
    LETTER_WEIGHTS = {k: 1 for k in _WT_JA_KANA_POOL}

try:
    LETTER_BAG = [x for x in LETTER_BAG if isinstance(x, str) and x in _WT_JA_KANA_SET]
    if not LETTER_BAG:
        LETTER_BAG = list(_WT_JA_KANA_POOL)
except Exception:
    pass
