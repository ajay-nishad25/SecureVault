# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification file for SecureVault desktop application.

Configures standalone Windows executable bundling:
- GUI application without console window (console=False)
- SecureVault.ico embedded as executable icon and bundled in assets/
- Complete exclusion of test suites, test runners, and developer infrastructure
- Inclusion of cryptographic backends (Argon2, AES-GCM) and PySide6 Qt GUI
"""

import sys
from pathlib import Path

block_cipher = None

# Project root directory (one level up from packaging/)
spec_dir = Path(SPECPATH).resolve()
project_root = spec_dir.parent

datas = [
    (str(project_root / 'assets' / 'SecureVault.ico'), 'assets'),
]

hiddenimports = [
    'argon2',
    'argon2.low_level',
    '_cffi_backend',
    'cryptography',
    'cryptography.hazmat.primitives.ciphers.aead',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'PySide6.QtNetwork',
]

excludes = [
    'tests',
    'pytest',
    '_pytest',
    'pyinstaller',
    'tkinter',
    'sqlite3',
    'unittest',
    'IPython',
    'pdb',
]

a = Analysis(
    [str(project_root / 'main.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SecureVault',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / 'assets' / 'SecureVault.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='SecureVault',
)
