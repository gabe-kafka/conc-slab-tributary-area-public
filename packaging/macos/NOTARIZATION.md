# macOS Signing And Notarization

This repo can build an unsigned `.app` and `.dmg` locally. To ship a normal employee-facing macOS release, finish these steps on a Mac with Apple Developer credentials.

## Prerequisites
- Apple Developer ID Application certificate installed in Keychain
- Apple Developer Team ID
- `xcrun notarytool` available
- App-specific password or keychain profile configured for notarization

## 1. Build The App And DMG
```bash
.venv/bin/python scripts/build_desktop.py
./scripts/build_macos_dmg.sh
```

Artifacts:
- `dist/Tributary Area Tool.app`
- `dist/TributaryAreaTool-macOS.dmg`

## 2. Sign The App Bundle
Replace the identity value with your actual Developer ID Application certificate.

```bash
codesign --force --deep --options runtime \
  --sign "Developer ID Application: YOUR COMPANY, INC. (TEAMID)" \
  "dist/Tributary Area Tool.app"
```

Verify:
```bash
codesign --verify --deep --strict --verbose=2 "dist/Tributary Area Tool.app"
spctl --assess --type exec --verbose=2 "dist/Tributary Area Tool.app"
```

## 3. Rebuild And Sign The DMG
After signing the app, rebuild the DMG so the signed app is embedded:

```bash
./scripts/build_macos_dmg.sh
codesign --force --sign "Developer ID Application: YOUR COMPANY, INC. (TEAMID)" \
  "dist/TributaryAreaTool-macOS.dmg"
```

## 4. Submit For Notarization
Recommended: use a saved keychain profile.

```bash
xcrun notarytool submit "dist/TributaryAreaTool-macOS.dmg" \
  --keychain-profile "AC_NOTARY_PROFILE" \
  --wait
```

## 5. Staple The Ticket
```bash
xcrun stapler staple "dist/TributaryAreaTool-macOS.dmg"
xcrun stapler validate "dist/TributaryAreaTool-macOS.dmg"
```

## 6. Final Gatekeeper Check
```bash
spctl --assess --type open --verbose=2 "dist/TributaryAreaTool-macOS.dmg"
```

## Expected Employee Flow
- Open `TributaryAreaTool-macOS.dmg`
- Drag `Tributary Area Tool.app` into `Applications`
- Launch from `Applications`
- Approve any first-run permission prompts if macOS asks
