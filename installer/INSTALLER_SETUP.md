# ID Colis Support App - Installation Wizard Setup Guide

## Overview

This guide explains how to create a professional Windows installer for ID Colis Support App using **Inno Setup**, which creates an installer wizard similar to MSIX.

## What You Get

The installer wizard will:
- ✅ Display a welcome screen
- ✅ Show license agreement
- ✅ Ask for installation directory
- ✅ Create Start Menu shortcuts
- ✅ Create optional Desktop shortcut
- ✅ Launch the application after installation
- ✅ Provide an uninstaller for easy removal

## Prerequisites

### 1. Install Inno Setup
Download and install **Inno Setup 6 or 7** (free & open-source):
- **Download**: https://jrsoftware.org/isdl.php
- Install to one of the standard locations:
  - `C:\Program Files (x86)\Inno Setup 6`
  - `C:\Program Files\Inno Setup 7`
  - `C:\Program Files (x86)\Inno Setup 7`

### 2. Python Virtual Environment
Set up the venv as normal:
```batch
setup.bat
```

## Files Created

The setup includes these files:

| File | Purpose |
|------|---------|
| `build_inno.bat` | Build the Inno Setup installer from an existing application executable |
| `ID ColisSetup.iss` | Inno Setup configuration script |
| `LICENSE.txt` | License agreement shown during install |
| `BEFORE_INSTALL.txt` | Pre-installation information |
| `AFTER_INSTALL.txt` | Post-installation information |

## Building the Installer

### Build the installer
```batch
build_inno.bat
```

This will:
1. Package the application executable specified by `ID ColisSetup.iss`
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
DefaultDirName={commonpf}\{#MyAppName}
```

Other options:
- `{pf}` - 32-bit Program Files
- `{commonpf}` - 64-bit Program Files (shared)
- `{userdocs}` - User's Documents folder
- `{localappdata}` - AppData\Local

### Modify License & Info Text

Edit these files to customize what users see:
- `LICENSE.txt` - License agreement screen
- `BEFORE_INSTALL.txt` - Info before installation
- `AFTER_INSTALL.txt` - Info after installation

### Add Application Icon

1. Get a `.ico` file (convert PNG using online tool or ImageMagick)
2. Place it in the project root
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

## Installer Workflow

1. **Welcome Screen**
   - User clicks "Next"

2. **License Screen**
   - User reads and accepts license

3. **Installation Folder**
   - User can change installation directory
   - Default: `C:\Program Files\ID Colis Support App`

4. **Select Tasks**
   - Option: Create Desktop shortcut

5. **Ready to Install**
   - User reviews choices

6. **Installation Progress**
   - Files are copied
   - Shortcuts are created

7. **Completion**
   - Option to launch application
   - Info screen is displayed

## Distribution

Once built, distribute `dist\installer\ID ColisSetup.exe`:
- Single file (standalone installer)
- No additional files needed
- Works on Windows 10+
- File size: ~200-400MB (includes Python runtime)

## Troubleshooting

### "Inno Setup not found"
- Download from https://jrsoftware.org/isdl.php
- Install to Inno Setup 6 or 7
- Verify one of these exists:
  - `C:\Program Files (x86)\Inno Setup 6\iscc.exe`
  - `C:\Program Files\Inno Setup 7\iscc.exe`
  - `C:\Program Files (x86)\Inno Setup 7\iscc.exe`

### Installer is too large
- This is expected (includes Python runtime + all dependencies)
- For smaller installer, you could require Python pre-installation
- See "Advanced Setup" section below

### "dist\installer\ID ColisSetup.exe" not found
- Run `build_inno.bat`
- Check that the application executable path in `ID ColisSetup.iss` is correct

## Advanced Setup (Optional)

### Require Pre-installed Python
To reduce installer size, require Python to be installed:

1. Modify `launcher.py` to not bundle Python
2. Update `ID ColisSetup.iss` to check for Python
3. Install only your app files

### Auto-Updates
For automatic updates, integrate with:
- **Sparkle** (open-source)
- **Windows Update** (enterprise)
- **Custom update mechanism**

### Different Installation Types
Modify `ID ColisSetup.iss` to offer:
- Compact install
- Full install
- Custom install

## Reference

- **Inno Setup Documentation**: https://jrsoftware.org/isinfo.php
- **Inno Setup Script Examples**: https://jrsoftware.org/files/is/files/

## Summary

Your ID Colis Support App now has a professional Windows installer that provides:
- Professional appearance
- User-friendly wizard
- Proper uninstallation
- Start Menu integration
- Distribution-ready single .exe file

Users can now install your app like any other Windows application!


