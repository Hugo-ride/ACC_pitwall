# -*- mode: python ; coding: utf-8 -*-
# ACC Pit Wall - PyInstaller spec (pywebview)

import os

block_cipher = None
BASE_DIR = os.path.abspath(os.getcwd())

def p(name):
    return os.path.join(BASE_DIR, name)

datas = []

required_files = [
    "acc_pitwall.html",
    "app_icon.ico",
    "app_icon_512.png",
    "server.py",
    "acc_shared_memory.py",
]

for filename in required_files:
    filepath = p(filename)
    if os.path.exists(filepath):
        datas.append((filepath, "."))
    else:
        print(f"ATTENTION : fichier manquant ignore : {filename}")

circuits_dir = p("carte_circuits")
if os.path.isdir(circuits_dir):
    datas.append((circuits_dir, "carte_circuits"))

hiddenimports = [
    "server",
    "acc_shared_memory",

    "websockets",
    "websockets.legacy",
    "websockets.legacy.server",
    "websockets.legacy.client",
    "websockets.server",
    "websockets.client",
    "websockets.exceptions",

    "webview",
    "webview.platforms",
    "webview.platforms.winforms",
    "webview.js",
    "webview.js.css",
    "webview.js.dom",

    "clr",
    "System",
    "System.Windows.Forms",

    "asyncio",
    "ctypes",
    "ctypes.wintypes",
    "mmap",
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
    excludes=["matplotlib", "numpy", "scipy", "pandas", "PyQt5", "wx", "pygame",
              "tkinter", "PIL"],
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
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=p("app_icon.ico"),
    version=None,
)
