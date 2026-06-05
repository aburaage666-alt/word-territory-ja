# Word Territory JP v29 Territory Feedback UI

This release keeps the v28 FULL ENGINE balance fixed and adds English-version-style territory feedback to the Japanese build.

## What changed

1. Big move result overlay
   - Shows the played word and a large `+N` for captured cells or territory swing.
   - Example: `+3 マス奪取`.

2. Board combo effects
   - CUT path pulse
   - BRIDGE path line / glow
   - ENCIRCLE ring pulse
   - SWING MOVE pulse
   - CAPTURE cells already use the v28 capture animation.

3. RED / BLUE territory delta strip
   - After each turn, shows current RED and BLUE territory counts.
   - When a new turn is applied, the strip briefly displays deltas such as `+2` or `-1`.

## Balance policy

No engine balance logic was changed. Backend is the v28 FULL ENGINE clean release. The UI additions are presentation-only.

## Recommended apply method

Use `RUN_NO_POWERSHELL.bat` or `RUN_APPLY_AND_TEST_JP_V28_FULL_ENGINE_NO_POWERSHELL.bat` as before. The frontend will be copied together with backend.


## v30 visual clarity add-on

- Captured cells now show a visible 「奪取」 stamp on the board.
- Newly changed non-capture cells show a compact 「+1」 stamp.
- CUT / BRIDGE / ENCIRCLE / SWING MOVE path cells display small effect tokens.
- A board-level effect ribbon explains whether the move cut, connected, surrounded, or swung territory.
- The RED/BLUE territory panel now shows before → after and an animated ownership bar.
