# Two-Way Slab Tributary Area

Local V1 web app for:
- DXF upload
- layer / unit review
- async tributary processing
- DXF + XLSX download
- desktop packaging for non-technical users

## Run Local
```bash
uv venv --clear --seed --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/uvicorn app.main:app --reload
```

Open:
`http://127.0.0.1:8000`

## Current Flow
1. Upload DXF
2. Review inferred layers
3. Confirm inches or feet
4. Queue job
5. Download `tributary_output.dxf` and `column_load_takedown.xlsx`

## Desktop App
The desktop build starts the same FastAPI app locally and opens it for the user. Runtime data is written to a user-writable app-data folder instead of the install directory.

Runtime data locations:
- Windows: `%LOCALAPPDATA%\\TributaryAreaTool`
- macOS: `~/Library/Application Support/TributaryAreaTool`
- Linux: `${XDG_DATA_HOME:-~/.local/share}/TributaryAreaTool`

### Run Desktop App From Source
```bash
uv venv --clear --seed --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python desktop_app.py
```

### Build Desktop Bundle
```bash
uv venv --clear --seed --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements.txt -r requirements-build.txt
.venv/bin/python scripts/build_desktop.py
```

Build output:
- macOS: `dist/Tributary Area Tool.app`
- Windows / Linux: `dist/Tributary Area Tool/`

### Build macOS DMG
```bash
.venv/bin/python scripts/build_desktop.py
./scripts/build_macos_dmg.sh
```

macOS release artifacts:
- `dist/Tributary Area Tool.app`
- `dist/TributaryAreaTool-macOS.dmg`

### Test macOS Bundle
This launches the packaged app on a fixed local port without auto-opening a browser:

```bash
TRIBUTARY_APP_PORT=8010 \
TRIBUTARY_APP_NO_BROWSER=1 \
"dist/Tributary Area Tool.app/Contents/MacOS/Tributary Area Tool"
```

Then open:
- `http://127.0.0.1:8010`

### macOS Signing / Notarization
Unsigned local packaging is supported now. For an employee-ready signed release, follow:
- `packaging/macos/NOTARIZATION.md`

### Build Windows Installer
1. Build the desktop bundle on Windows.
2. Install Inno Setup.
3. Run:

```powershell
iscc packaging/windows/TributaryAreaTool.iss
```

Installer output:
- `dist/installer/TributaryAreaToolInstaller.exe`
