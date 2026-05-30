# -*- mode: python ; coding: utf-8 -*-
# ACC Pit Wall - PyInstaller spec
# Pour compiler : double-cliquer sur BUILD.bat

import os

block_cipher = None

BASE_DIR = os.path.abspath(os.getcwd())

def p(name):
    return os.path.join(BASE_DIR, name)

# Fichiers a inclure dans le .exe
datas = []
required_files = [
    "acc_pitwall.html",
    "app_icon.ico",
    "app_icon_512.png",
    "server.py",
    "acc_shared_memory.py",
    "fuel_calculator.py",
]

for filename in required_files:
    filepath = p(filename)
    if os.path.exists(filepath):
        datas.append((filepath, "."))
    else:
        print(f"ATTENTION : fichier manquant ignore : {filename}")

# Dossier optionnel des images circuits : on l'ajoute seulement s'il existe.
circuits_dir = p("carte_circuits")
if os.path.isdir(circuits_dir):
    datas.append((circuits_dir, "carte_circuits"))
else:
    print("INFO : dossier optionnel carte_circuits absent, compilation sans images circuits.")

hiddenimports = [
    "websockets",
    "websockets.legacy",
    "websockets.legacy.server",
    "websockets.legacy.client",
    "websockets.server",
    "websockets.client",
    "websockets.exceptions",
    "websockets.frames",
    "websockets.http11",
    "websockets.protocol",
    "asyncio",
    "ctypes",
    "ctypes.wintypes",
    "mmap",
    "tkinter",
    "tkinter.ttk",
    "tkinter.messagebox",
    "PIL",
    "PIL.Image",
    "PIL.ImageTk",
    "json",
    "math",
    "pathlib",
]

a = Analysis(
    [p("launcher.py")],
    pathex=[BASE_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "numpy", "scipy", "pandas", "PyQt5", "wx"],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="ACC_PitWall",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=p("app_icon.ico") if os.path.exists(p("app_icon.ico")) else None,
    version=p("version_info.txt") if os.path.exists(p("version_info.txt")) else None,
)
