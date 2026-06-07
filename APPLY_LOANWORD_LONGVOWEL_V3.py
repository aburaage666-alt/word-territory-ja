from pathlib import Path
import re
import shutil
import subprocess
import sys

root = Path(sys.argv[1]).resolve()

if (root / "word-territory-ja" / "backend").exists():
    app = root / "word-territory-ja"
    rel_prefix = "word-territory-ja/"
elif (root / "backend").exists():
    app = root
    rel_prefix = ""
else:
    raise SystemExit("backend が見つかりません。clone構造を確認してください。")

backend = app / "backend"
index = app / "frontend" / "pages" / "index.js"
profile = backend / "language_profiles" / "ja.py"

print("APP:", app)
print("BACKEND:", backend)
print("INDEX:", index)
print("PROFILE:", profile)

if not index.exists():
    raise SystemExit(f"frontend/pages/index.js が見つかりません: {index}")

# ------------------------------------------------------------
# 1. 外来語辞書追加：「ー」は単語内では有効。ただし市場には出さない。
# ------------------------------------------------------------
loanwords = """
かーど
かーてん
かーと
かーなび
かーぺっと
けーき
けーす
けーむ
こーす
こーひー
こーら
さーくる
さーびす
すきー
すたー
すたーと
すぴーど
すぽーつ
すーつ
すーぷ
せーたー
せーる
ちーず
てーぶる
てーま
でーた
でーと
どあ
のーと
ばー
ばす
ばたー
ぱーく
ぱーてぃー
ぱーと
ぱん
びーる
ぷーる
ぺーじ
ぼーる
ほてる
まーく
まーけっと
めーる
めにゅー
もーる
ゆーざー
らーめん
りーだー
るーる
れーる
ろーか
ろーる
げーむ
ごーる
じゅーす
たくしー
てれび
らじお
れもん
みるく
""".strip().splitlines()

dict_files = [
    backend / "ja_words.txt",
    backend / "ja_words_ui.txt",
    backend / "dictionaries" / "ja_words.txt",
    backend / "dictionaries" / "ja_words_ui.txt",
]

for fp in dict_files:
    if not fp.exists():
        continue

    shutil.copy2(fp, fp.with_suffix(fp.suffix + ".loanword_v3.bak"))

    raw = fp.read_text(encoding="utf-8").splitlines()
    words = []
    seen = set()
    removed_oha = 0

    for line in raw:
        w = line.strip()
        if not w:
            continue
        if w == "おは":
            removed_oha += 1
            continue
        if w not in seen:
            seen.add(w)
            words.append(w)

    added = 0
    for w in loanwords + ["おはよう"]:
        if w not in seen:
            seen.add(w)
            words.append(w)
            added += 1

    words = sorted(words, key=lambda x: (len(x), x))
    fp.write_text("\n".join(words) + "\n", encoding="utf-8")

    print("DICT", fp, "total", len(words), "added", added, "removed_oha", removed_oha)

# ------------------------------------------------------------
# 2. language_profiles/ja.py：
#    ーは単語内では有効。ただし Letter Market 用 ALL_KANA には入れない。
# ------------------------------------------------------------
if profile.exists():
    shutil.copy2(profile, profile.with_suffix(profile.suffix + ".loanword_v3.bak"))
    text = profile.read_text(encoding="utf-8")

    marker = "# WT_JA_LOANWORD_LONGVOWEL_PROFILE_V3"
    if marker in text:
        text = text[:text.index(marker)].rstrip() + "\n"

    patch = r'''
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
'''

    text = text.rstrip() + "\n\n" + patch + "\n"
    profile.write_text(text, encoding="utf-8")

# ------------------------------------------------------------
# 3. frontend/index.js：
#    FREE / Wild 入力で、ひらがな + ー だけを受け付ける。
#    通常市場には影響させない。
# ------------------------------------------------------------
idx = index.read_text(encoding="utf-8")
shutil.copy2(index, index.with_suffix(index.suffix + ".loanword_v3.bak"))

helper = r'''
// WT_JA_LOANWORD_FREE_INPUT_V3
function wtJaKatakanaToHiraganaLongVowel(value) {
  return String(value || "").normalize("NFKC").replace(/[\u30a1-\u30f6]/g, ch =>
    String.fromCharCode(ch.charCodeAt(0) - 0x60)
  );
}

function wtJaNormalizeKanaInput(value) {
  const hira = wtJaKatakanaToHiraganaLongVowel(value);
  const chars = Array.from(hira).filter(ch => /^[\u3041-\u3096\u30fc]$/.test(ch));
  return chars.length ? chars[chars.length - 1] : "";
}

function wtJaHasKana(value) {
  return !!wtJaNormalizeKanaInput(value);
}

'''

# 既存の wtJaNormalizeKanaInput があれば置き換え。なければ export default 前へ挿入。
if "function wtJaNormalizeKanaInput" in idx:
    idx = re.sub(
        r'function\s+wtJaKatakanaToHiragana[\s\S]*?function\s+wtJaHasKana\s*\([^)]*\)\s*\{[\s\S]*?\n\}',
        helper.strip(),
        idx,
        count=1
    )
    idx = re.sub(
        r'function\s+wtJaNormalizeKanaInput\s*\([^)]*\)\s*\{[\s\S]*?\n\}',
        helper.strip(),
        idx,
        count=1
    )
else:
    pos = idx.find("export default function")
    if pos == -1:
        pos = 0
    idx = idx[:pos] + helper + "\n" + idx[pos:]

# 旧A-Zフィルターを除去
idx = idx.replace(
    "setFreeLetter(e.target.value.toUpperCase().replace(/[^A-Z]/g,''))",
    "setFreeLetter(wtJaNormalizeKanaInput(e.target.value))"
)

idx = idx.replace(
    "setFreeLetter(e.target.value.toUpperCase().slice(0,1))",
    "setFreeLetter(wtJaNormalizeKanaInput(e.target.value))"
)

idx = idx.replace(
    "placeholder={market.active.length > 0 ? \"—\" : \"A\"}",
    "placeholder={market.active.length > 0 ? \"—\" : \"あ/ー\"}"
)

idx = idx.replace(
    "placeholder=\"A\"",
    "placeholder=\"あ/ー\""
)

idx = idx.replace(
    "ひらがな1文字",
    "ひらがな1文字またはー"
)

# FREE / Wild に英字混入を許すパターンを可能な範囲で除去
idx = idx.replace("|[a-zA-Z]", "")
idx = idx.replace("[a-zA-Z]|", "")
idx = idx.replace("|[A-Z]", "")
idx = idx.replace("[A-Z]|", "")

# 使う文言の最低限調整
idx = idx.replace("Use ★ Wild", "★を使う")
idx = idx.replace("Use ⭐", "自由札を使う")
idx = idx.replace("Use ★", "★を使う")
idx = idx.replace("Use", "使う")

bad_tokens = [
    "get脅威",
    "normalize脅威",
    "wtJaTo脅威",
    "value.マス",
    "function Cell({ マス",
    'className="マス"',
    "captured_マス",
    "affected_マス",
    "threat_マス",
    "{/* move controls */}}",
]

for b in bad_tokens:
    if b in idx:
        raise SystemExit(f"frontendに危険な破損トークンがあります: {b}")

index.write_text(idx, encoding="utf-8")

# ------------------------------------------------------------
# 4. verification
# ------------------------------------------------------------
index_now = index.read_text(encoding="utf-8")
profile_now = profile.read_text(encoding="utf-8") if profile.exists() else ""

def dict_has(word):
    for fp in dict_files:
        if fp.exists() and word in fp.read_text(encoding="utf-8").splitlines():
            return True
    return False

def dict_not_has(word):
    for fp in dict_files:
        if fp.exists() and word in fp.read_text(encoding="utf-8").splitlines():
            return False
    return True

checks = {
    "DICT_HAS_KEEKI": dict_has("けーき"),
    "DICT_HAS_COFFEE": dict_has("こーひー"),
    "DICT_HAS_RAMEN": dict_has("らーめん"),
    "DICT_HAS_OHAYO": dict_has("おはよう"),
    "DICT_NO_OHA": dict_not_has("おは"),
    "PROFILE_MARKER_OR_NO_PROFILE": (not profile.exists()) or ("WT_JA_LOANWORD_LONGVOWEL_PROFILE_V3" in profile_now),
    "PROFILE_LONG_NOT_MARKET": (not profile.exists()) or ('ALL_KANA = [ch for ch in ALL_KANA if ch != "ー"]' in profile_now),
    "INDEX_HELPER": "WT_JA_LOANWORD_FREE_INPUT_V3" in index_now,
    "INDEX_ACCEPTS_LONG_VOWEL": "\\u30fc" in index_now or "ー" in index_now,
    "INDEX_NO_AZ_FILTER": "replace(/[^A-Z]/g" not in index_now,
    "INDEX_NO_FREE_AZ_MIX": "|[a-zA-Z]" not in index_now,
    "NO_BAD_IDENTIFIER": "get脅威" not in index_now,
    "NO_EXTRA_JSX_BRACE": "{/* move controls */}}" not in index_now,
}

print("VERIFY loanword long-vowel V3")
for k, v in checks.items():
    print(k, "=", v)

if not all(checks.values()):
    raise SystemExit("loanword V3 verification failed. 上の False を貼ってください。")

if profile.exists():
    subprocess.run([sys.executable, "-m", "py_compile", str(profile)], check=True)

print("DONE: loanword long-vowel V3 patch applied")
