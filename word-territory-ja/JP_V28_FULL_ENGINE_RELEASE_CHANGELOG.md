# JP v28 FULL ENGINE RELEASE changelog

- Replaced dictionary-only distribution with full backend distribution.
- Includes clean v18 `engine.py` to prevent local v26/v27 contaminated engine from surviving.
- Adds source engine validation:
  - requires `JP_V28_FULL_ENGINE_CLEAN_V18_RELEASE`
  - rejects `-14.0`
  - rejects `_JP_V26_BANNED_WORDS`
- Applies v28 dictionary guard:
  - banned: `やか`, `くもの`, `くりから`, `やさいか`, `うみか`
  - required: `やきもの`, `よみもの`, `のみもの`, `たべもの`, `かきもの`, `うみかぜ`, `うみかつき`, `うみからまつ`, `うみかわ`, `うみかわうそ`
- Adds strict result validator:
  - seed must be 0
  - pass must be 0
  - word rate must be >= 99%
  - 3-letter rate must be <= 70%
  - avg gap must be <= 6.0
  - banned best_word hits must be 0
- Uses 90-game validation output name: `bot_match_results_ja_v28_full_engine.*`
