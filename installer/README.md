# Windows Installer (Inno Setup)

This folder contains files for building a professional Windows installer using Inno Setup 7.

## Overview

The installer wizard will:
- ✅ Display a welcome screen
- ✅ Show license agreement
- ✅ Ask for installation directory
- ✅ Create Start Menu shortcuts
- ✅ Create optional Desktop shortcut
- ✅ Launch the application after installation
- ✅ Provide an uninstaller for easy removal

## Installation Method

This installer installs the **source code** and dependencies on the user's machine. Users must have Python 3.12+ installed.

## Prerequisites

### 1. Install Inno Setup 7
Download and install **Inno Setup 7** (free & open-source):
- **Download**: https://jrsoftware.org/isdl.php
- Install to default location: `C:\Program Files (x86)\Inno Setup 7` or `C:\Program Files\Inno Setup 7`

## Building the Installer

```batch
build_installer.bat
```

This will:
1. Package the source code from the project root
2. Create the Inno Setup installer into `dist\installer\ID ColisSetup.exe`

Output will be in `dist\installer\ID ColisSetup.exe`

## Customizing the Installer

### Change Application Name, Version, etc.

Edit `ID ColisSetup.iss`:
```ini
#define MyAppName "ID Colis Support App"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "ID Colis"
#define MyAppURL "https://example.com"
```

### Change Installation Directory

Edit `ID ColisSetup.iss`:
```ini
DefaultDirName={localappdata}\{#MyAppName}
```

Other options:
- `{pf}` - 32-bit Program Files
- `{commonpf}` - 64-bit Program Files (shared)
- `{userdocs}` - User's Documents folder
- `{localappdata}` - AppData\Local (current default - no admin required)

### Modify License & Info Text

Edit these files to customize what users see:
- `LICENSE.txt` - License agreement screen
- `BEFORE_INSTALL.txt` - Info before installation
- `AFTER_INSTALL.txt` - Info after installation

### Add Application Icon

1. Get a `.ico` file (convert PNG using online tool or ImageMagick)
2. Place it in the installer folder
3. Update `ID ColisSetup.iss`:
   ```ini
   SetupIconFile={SourcePath}\your_icon.ico
   ```

## Installer Features Included

### ✅ Start Menu Shortcut
Automatically created in Start Menu → ID Colis Support App

### ✅ Desktop Shortcut (Optional)
Users can choose to create a desktop shortcut during installation

### ✅ Uninstaller
- Available in Control Panel → Programs and Features
- Properly removes all files and shortcuts
- Registered in Windows Registry

### ✅ Auto-Launch
After installation, the application launches automatically

### ✅ Admin Privileges
Installer runs with admin privileges (required for Program Files installation)

## Distribution

Once built, distribute `dist\installer\ID ColisSetup.exe`:
- Single file (standalone installer)
- No additional files needed
- Works on Windows 10+
- File size: ~10-50MB (source code only)

## User Requirements

Users installing this application must have:
- Python 3.12+ installed
- "Add Python to PATH" checked during Python installation
- Internet connection (for downloading dependencies and ML models)

## Troubleshooting

### "Inno Setup not found"
- Download from https://jrsoftware.org/isdl.php
- Install to default location
- Verify: `C:\Program Files (x86)\Inno Setup 7\iscc.exe` or `C:\Program Files\Inno Setup 7\iscc.exe` exists

### "dist\installer\ID ColisSetup.exe" not found
- Run `build_installer.bat`
- Check for compilation errors in the output

## Notes

- This method installs source code, not a frozen executable
- Users need Python installed on their machines
- First launch will create a virtual environment and install dependencies
- First launch will download ML model (~100MB) - this may take a few minutes
- The launcher script (`launch.bat`) handles virtual environment creation and dependency installation

For detailed information, see `INSTALLER_SETUP.md`.


