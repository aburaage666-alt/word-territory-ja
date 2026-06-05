from pathlib import Path
import sys

root = Path(__file__).resolve().parent
engine = root / 'backend' / 'engine.py'
if not engine.exists():
    print(f'ERROR: missing {engine}')
    sys.exit(1)
s = engine.read_text(encoding='utf-8')
checks = {
    'marker': 'JP_V28_FULL_ENGINE_CLEAN_V18_RELEASE' in s,
    'no_punitive_minus14': '-14.0' not in s,
    'no_v26_banned_refs': '_JP_V26_BANNED_WORDS' not in s,
    'v18_marker': 'JP_PROTOTYPE_V18_LENGTH_CURVE_BORDER_FIX' in s,
}

# Release completeness check: blank checkouts must include JP language profile.
profile_dir = root / 'backend' / 'language_profiles'
profile_init = profile_dir / '__init__.py'
profile_ja = profile_dir / 'ja.py'
checks.update({
    'language_profiles_dir': profile_dir.exists(),
    'language_profiles_init': profile_init.exists(),
    'language_profiles_ja': profile_ja.exists(),
})
for k,v in checks.items():
    print(f'{k}: {v}')
if not all(checks.values()):
    sys.exit(1)
print('FULL ENGINE source validation OK')
