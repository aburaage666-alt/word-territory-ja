"""
Word Territory — dictionary module with Language Profile support.

EN:
  - words are stored and compared as UPPERCASE.

JA:
  - words are normalized through language_profiles.ja.normalize()
  - hiragana is kept as-is; never .upper()
  - supports 3 dictionary layers:
      ja_words.txt
      ja_words_ui.txt
      ja_demo_words.txt
"""
from __future__ import annotations
import os
from pathlib import Path

_HERE = Path(__file__).resolve().parent
LANG = os.environ.get("WT_LANG", "en").lower()

if LANG == "ja":
    from language_profiles import ja as _profile
else:
    _profile = None


def _wordfile(name: str) -> Path:
    """Find language-specific word files.

    Preferred:
      backend/dictionaries/{lang}_{name}

    Compatibility fallback:
      backend/{lang}_{name}
      backend/{name}
    """
    candidates = [
        _HERE / "dictionaries" / f"{LANG}_{name}",
        _HERE / f"{LANG}_{name}",
        _HERE / name,
    ]
    for path in candidates:
        if path.exists():
            return path
    return candidates[-1]


_words_cache: set[str] | None = None
_ui_words_cache: set[str] | None = None
_demo_words_cache: set[str] | None = None


def _process(raw: str) -> set[str]:
    words = set(raw.split())
    if LANG == "ja":
        out = set()
        for w in words:
            nw = _profile.normalize(w)
            if nw and _profile.is_valid_kana_word(nw):
                out.add(nw)
        return out
    return {w.upper().strip() for w in words if w.strip()}


def _read_layer(filename: str) -> set[str]:
    path = _wordfile(filename)
    if not path.exists():
        return set()
    return _process(path.read_text(encoding="utf-8"))


def get_words() -> set[str]:
    global _words_cache
    if _words_cache is None:
        _words_cache = _read_layer("words.txt")
    return _words_cache


def get_ui_words() -> set[str]:
    global _ui_words_cache
    if _ui_words_cache is None:
        ui = _read_layer("words_ui.txt")
        _ui_words_cache = ui if ui else get_words()
    return _ui_words_cache


def get_demo_words() -> set[str]:
    global _demo_words_cache
    if _demo_words_cache is None:
        demo = _read_layer("demo_words.txt")
        # For ja/en file naming, _wordfile("demo_words.txt") checks ja_demo_words.txt.
        _demo_words_cache = demo if demo else get_ui_words()
    return _demo_words_cache


def normalize_word(word: str) -> str:
    if LANG == "ja":
        return _profile.normalize(word)
    return str(word or "").upper().strip()


def is_valid_word(word: str, words: set[str] | None = None) -> bool:
    if words is None:
        words = get_words()
    key = normalize_word(word)
    return bool(key and key in words)


def is_ui_word(word: str, words: set[str] | None = None) -> bool:
    if words is None:
        words = get_ui_words()
    key = normalize_word(word)
    if not key or key not in words:
        return False
    if LANG == "ja":
        return _profile.is_ui_word(key)
    return True


def is_demo_word(word: str, words: set[str] | None = None) -> bool:
    if words is None:
        words = get_demo_words()
    key = normalize_word(word)
    if not key or key not in words:
        return False
    if LANG == "ja":
        return _profile.is_demo_word(key) or key in words
    return True


def reset_cache():
    global _words_cache, _ui_words_cache, _demo_words_cache
    _words_cache = _ui_words_cache = _demo_words_cache = None
