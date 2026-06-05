# Word Territory JP v28 FULL ENGINE RELEASE

This package physically replaces `backend/engine.py` with the clean v18 engine and applies the v28 guarded Japanese dictionaries.

Use this package instead of dictionary-only RC packages. Previous RC attempts failed because the local `backend/engine.py` remained contaminated by v26/v27 seed/length experiments.

## Included

- `backend/engine.py` — clean v18 engine with marker `JP_V28_FULL_ENGINE_CLEAN_V18_RELEASE`
- `backend/dictionary.py`
- `backend/bot_match_test_ja.py`
- `backend/bot_match_test_synergy.py`
- `backend/models.py`
- `backend/main.py`
- `backend/spectator_seed.py`
- `backend/ja_words.txt`
- `backend/ja_words_ui.txt`
- `backend/dictionaries/ja_words.txt`
- `backend/dictionaries/ja_words_ui.txt`
- `scorecard.py`
- strict validators
- clean v18 90-game baseline results

## Expected clean result

- seed_uses = 0
- word rate ≈ 100%
- 3-letter rate <= 70%
- avg gap <= 6.0
- SC = 8/8

## Run

Extract to:

```text
C:\Users\info\Downloads\word_territory_ja_v28_FULL_ENGINE_RELEASE
```

Then run:

```powershell
powershell -ExecutionPolicy Bypass -File "$env:USERPROFILE\Downloads\word_territory_ja_v28_FULL_ENGINE_RELEASE\RUN_APPLY_AND_TEST_JP_V28_FULL_ENGINE.ps1"
```

If validation fails, the script renames outputs to `*_FAILED.*` and stops.


## Release completeness rule

A FULL ENGINE release must include `backend/language_profiles/__init__.py` and `backend/language_profiles/ja.py`. The backend imports `from language_profiles import ja` when `WT_LANG=ja`; omitting these files can work only on a developer repo that already has leftovers, but fails on a blank checkout.
