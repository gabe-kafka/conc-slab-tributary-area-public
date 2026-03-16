## Windows Desktop Release

This page is the single place for employees to download, install, and run the Windows desktop app.

### Download
- Download `TributaryAreaToolInstaller.exe` from the Assets section on this release.

### Install
1. Double-click `TributaryAreaToolInstaller.exe`.
2. If Windows SmartScreen appears, click `More info`, then `Run anyway`.
3. Leave the default install location as:
   - `%LOCALAPPDATA%\Programs\Two-Way Slab Tributary Area`
4. Optionally enable the desktop shortcut during install.
5. Finish install.

### Launch
- Open `Two-Way Slab Tributary Area` from the Start menu.
- If installed, the desktop shortcut works too.
- Keep the small launcher window open while using the app.
- The launcher opens the app locally in your browser and shows the local URL.

### Run The Demo
1. Click `USE DEMO DXF`.
2. Review the suggested layers.
3. Click `QUEUE JOB`.
4. Download:
   - `tributary_output.dxf`
   - `column_load_takedown.xlsx`

### Run Your Own DXF
1. Use the top navigation upload control.
2. Select a `.dxf` file.
3. Review the layer mapping.
4. Click `QUEUE JOB`.
5. Download the DXF and XLSX outputs when the job completes.

### Rerun
- Use the top navigation upload control to start another run from the top without reinstalling or restarting the app.

### Files And Data
- Installed app files:
  - `%LOCALAPPDATA%\Programs\Two-Way Slab Tributary Area`
- Runtime data:
  - `%LOCALAPPDATA%\TributaryAreaTool`

### Uninstall
- Uninstall from Windows Apps, or run:
  - `%LOCALAPPDATA%\Programs\Two-Way Slab Tributary Area\unins000.exe`

### Current Windows Notes
- This installer is validated on Windows for:
  - install
  - Start menu launch
  - desktop shortcut launch
  - demo DXF run
  - manual DXF upload
  - DXF download
  - XLSX download
  - rerun flow
  - uninstall
- Code signing is still pending, so SmartScreen warnings may still appear until the installer is signed.
