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


# WT_JA_LOANWORD_LONGVOWEL_PROFILE_V3
# Long vowel mark "ー" is valid inside loanwords, but must not be drawn into Letter Market.
LOAN_CHARS = {"ー"}

try:
    ALL_KANA = [ch for ch in ALL_KANA if ch != "ー"]
except Exception:
    pass

try:
    KANA_WEIGHTS.pop("ー", None)
except Exception:
    pass

try:
    _WT_JA_ORIG_NORMALIZE_V3 = normalize
except Exception:
    _WT_JA_ORIG_NORMALIZE_V3 = None

def normalize(value):
    import unicodedata
    raw = unicodedata.normalize("NFKC", str(value or "").strip())
    out = []
    for ch in raw:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            ch = chr(code - 0x60)
        if ch in KANA_WEIGHTS or ch in LOAN_CHARS:
            out.append(ch)
    return "".join(out)

try:
    _WT_JA_ORIG_IS_VALID_KANA_WORD_V3 = is_valid_kana_word
except Exception:
    _WT_JA_ORIG_IS_VALID_KANA_WORD_V3 = None

def is_valid_kana_word(word):
    w = normalize(word)
    if not w:
        return False
    if "ー" in w:
        if w.startswith("ー") or w.endswith("ー"):
            return False
        return all((ch in KANA_WEIGHTS or ch in LOAN_CHARS) for ch in w)
    if _WT_JA_ORIG_IS_VALID_KANA_WORD_V3:
        return _WT_JA_ORIG_IS_VALID_KANA_WORD_V3(w)
    return all(ch in KANA_WEIGHTS for ch in w)


# WT_JA_SMALL_KANA_WORD_ONLY_V1
# Small kana are valid inside dictionary words but are never drawn into Letter Market.
SMALL_KANA_CHARS = {"ゃ", "ゅ", "ょ", "っ"}

try:
    LOAN_CHARS
except NameError:
    LOAN_CHARS = {"ー"}

SPECIAL_WORD_CHARS = set(LOAN_CHARS) | set(SMALL_KANA_CHARS)

try:
    ALL_KANA = [ch for ch in ALL_KANA if ch not in SPECIAL_WORD_CHARS]
except Exception:
    pass

try:
    for _ch in SPECIAL_WORD_CHARS:
        KANA_WEIGHTS.pop(_ch, None)
except Exception:
    pass

_YOON_PREV = set("きしちにひみりぎじぢびぴ")
_SMALL_YOON = set("ゃゅょ")

def _wt_ja_small_kana_structure_ok(word):
    w = str(word or "")
    if not w:
        return False

    for i, ch in enumerate(w):
        if ch in _SMALL_YOON:
            if i == 0:
                return False
            if w[i - 1] not in _YOON_PREV:
                return False

        if ch == "っ":
            if i == 0 or i == len(w) - 1:
                return False
            nxt = w[i + 1]
            if nxt in set("あいうえおんーゃゅょっ"):
                return False

        if ch == "ー":
            if i == 0 or i == len(w) - 1:
                return False

    return True

try:
    _WT_JA_SMALL_ORIG_NORMALIZE_V1 = normalize
except Exception:
    _WT_JA_SMALL_ORIG_NORMALIZE_V1 = None

def normalize(value):
    import unicodedata
    raw = unicodedata.normalize("NFKC", str(value or "").strip())
    out = []
    for ch in raw:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            ch = chr(code - 0x60)
        if ch in KANA_WEIGHTS or ch in SPECIAL_WORD_CHARS:
            out.append(ch)
    return "".join(out)

try:
    _WT_JA_SMALL_ORIG_IS_VALID_KANA_WORD_V1 = is_valid_kana_word
except Exception:
    _WT_JA_SMALL_ORIG_IS_VALID_KANA_WORD_V1 = None

def is_valid_kana_word(word):
    w = normalize(word)
    if not w:
        return False

    if any(ch in SPECIAL_WORD_CHARS for ch in w):
        if not all((ch in KANA_WEIGHTS or ch in SPECIAL_WORD_CHARS) for ch in w):
            return False
        return _wt_ja_small_kana_structure_ok(w)

    if _WT_JA_SMALL_ORIG_IS_VALID_KANA_WORD_V1:
        return _WT_JA_SMALL_ORIG_IS_VALID_KANA_WORD_V1(w)

    return all(ch in KANA_WEIGHTS for ch in w)



# WT_JA_ABF_KANA_WEIGHTS_V3_BEGIN
_ABF_ALL_KANA = list(
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

_ABF_KANA_WEIGHTS = {
    "う":100, "い":95, "く":84, "し":81, "き":72, "か":70, "り":69, "る":66, "つ":63,
    "す":61, "た":59, "と":59, "こ":57, "ち":56, "あ":55, "じ":55, "ま":53, "ら":53,
    "お":51, "さ":49, "な":49, "み":49, "け":46, "が":46, "え":45, "せ":44, "は":44,
    "て":43, "れ":43, "ふ":42, "め":42, "ろ":42, "わ":42, "も":41, "だ":41, "ど":40,
    "ば":40, "そ":38, "の":37, "ひ":37, "む":37, "や":37, "ぶ":37, "に":36, "よ":34,
    "ぎ":34, "ぐ":34, "げ":34, "び":33, "ご":32, "ね":31, "ほ":31, "ぼ":31, "ず":30,
    "ざ":28, "ゆ":27, "で":27, "ん":26, "べ":24, "ぜ":23, "ぱ":23, "ぷ":23, "へ":22,
    "ぞ":22, "ぬ":19, "づ":18, "ぽ":18, "ぴ":17, "ぺ":14, "ぢ":4, "を":1,
}

ALL_KANA = [ch for ch in _ABF_ALL_KANA if ch not in {"ー", "ゃ", "ゅ", "ょ", "っ"}]
KANA_WEIGHTS = dict(_ABF_KANA_WEIGHTS)
for _ch in ALL_KANA:
    KANA_WEIGHTS.setdefault(_ch, 1)
# WT_JA_ABF_KANA_WEIGHTS_V3_END

# WT_JA_CHOONPU_PROFILE_GUARD_V1_BEGIN
# Long vowel mark / choonpu:
# - valid inside normalized kana loanwords
# - invalid at word start/end
# - never appears in random market pools
try:
    LOAN_CHARS = set(globals().get("LOAN_CHARS", set())) | {"ー"}
except Exception:
    LOAN_CHARS = {"ー"}

try:
    ALL_KANA = [ch for ch in ALL_KANA if ch != "ー"]
except Exception:
    pass

try:
    KANA_WEIGHTS.pop("ー", None)
except Exception:
    pass

def _wt_ja_choon_katakana_to_hiragana_v1(text):
    import unicodedata
    s = unicodedata.normalize("NFKC", str(text or "")).strip()
    out = []
    for ch in s:
        code = ord(ch)
        if 0x30A1 <= code <= 0x30F6:
            ch = chr(code - 0x60)
        out.append(ch)
    return "".join(out)

try:
    _wt_ja_choon_orig_normalize_v1 = normalize
except Exception:
    _wt_ja_choon_orig_normalize_v1 = None

def normalize(value):
    s = _wt_ja_choon_katakana_to_hiragana_v1(value)
    out = []
    for ch in s:
        if ch == "ー":
            out.append(ch)
        elif "ぁ" <= ch <= "ゖ":
            out.append(ch)
    return "".join(out)

try:
    _wt_ja_choon_orig_is_valid_kana_word_v1 = is_valid_kana_word
except Exception:
    _wt_ja_choon_orig_is_valid_kana_word_v1 = None

def is_valid_kana_word(word):
    w = normalize(word)
    if not w:
        return False
    try:
        if not (MIN_WORD_LEN <= len(w) <= 12):
            return False
    except Exception:
        if len(w) < 2:
            return False

    if "ー" in w:
        if w.startswith("ー") or w.endswith("ー"):
            return False
        return all((("ぁ" <= ch <= "ゖ") or ch == "ー") for ch in w)

    if _wt_ja_choon_orig_is_valid_kana_word_v1:
        return _wt_ja_choon_orig_is_valid_kana_word_v1(w)

    return all("ぁ" <= ch <= "ゖ" for ch in w)
# WT_JA_CHOONPU_PROFILE_GUARD_V1_END
