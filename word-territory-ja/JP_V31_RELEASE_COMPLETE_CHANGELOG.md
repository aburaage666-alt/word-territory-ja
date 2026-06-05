# JP v31 Release Complete Full Engine

Fixes the v30 packaging defect: `backend/language_profiles/ja.py` and `backend/language_profiles/__init__.py` are now bundled.

This is a packaging/release-completeness fix only. Engine balance and frontend territory-clarity behavior are unchanged from v30.

Release invariant from v31 onward:

- FULL ENGINE ZIP must include `backend/engine.py`
- FULL ENGINE ZIP must include `backend/language_profiles/__init__.py`
- FULL ENGINE ZIP must include `backend/language_profiles/ja.py`
- Installer must compile/import `language_profiles.ja`, `dictionary`, and `engine` under `WT_LANG=ja` before test execution
