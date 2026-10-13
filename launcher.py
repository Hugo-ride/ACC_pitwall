# -*- coding: utf-8 -*-
"""
ACC Pit Wall — Launcher
Lance le serveur WebSocket et affiche l'interface HTML dans une fenêtre native (pywebview).
"""

import sys
import os
import threading
import socket
import time

# ── Résolution des chemins (PyInstaller ou dev) ─────────────────
def _base_path():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

BASE_PATH = _base_path()
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

def resource_path(rel):
    return os.path.join(BASE_PATH, rel)

# ── Constantes ──────────────────────────────────────────────────
DEV_MODE    = os.environ.get("ACC_PITWALL_DEV") == "1" or (
    getattr(sys, "frozen", False)
    and os.path.basename(sys.executable).lower().endswith("_dev.exe")
)
if DEV_MODE:
    os.environ["ACC_PITWALL_DEV"] = "1"

APP_NAME    = "ACC Pit Wall Dev" if DEV_MODE else "ACC Pit Wall"
APP_VERSION = "1.0.0"
WS_HOST     = "127.0.0.1"
WS_PORT     = 8765
HTML_FILE   = resource_path("acc_pitwall.html")
ICON_FILE   = resource_path("app_icon.ico")

# ── Serveur WebSocket ────────────────────────────────────────────
_server_running = False

def _is_port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((WS_HOST, port)) != 0

def _run_server():
    global _server_running
    _server_running = True
    try:
        import asyncio
        if BASE_PATH not in sys.path:
            sys.path.insert(0, BASE_PATH)
        from server import ACCServer
        asyncio.run(ACCServer().run())
    except Exception:
        import traceback
        traceback.print_exc()
    finally:
        _server_running = False

def _wait_for_server(timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        if not _is_port_free(WS_PORT):
            return True
        time.sleep(0.1)
    return False

# ── Point d'entrée ───────────────────────────────────────────────
if __name__ == '__main__':
    # 1. Démarrer le serveur WebSocket en arrière-plan
    threading.Thread(target=_run_server, daemon=True).start()
    _wait_for_server()

    # 2. Ouvrir l'interface dans une fenêtre native via pywebview
    import webview

    url = 'file:///' + HTML_FILE.replace('\\', '/')

    webview.create_window(
        title=APP_NAME,
        url=url,
        width=1600,
        height=950,
        min_size=(1200, 700),
        background_color='#0a0b0d',
    )

    # storage_path : conserve localStorage/cookies entre les sessions
    storage_name = "ACC_PitWall_Dev" if DEV_MODE else "ACC_PitWall"
    storage = os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.join(os.path.expanduser('~'), 'AppData', 'Local')),
        storage_name,
    )
    os.makedirs(storage, exist_ok=True)

    try:
        webview.start(gui='edgechromium', icon=ICON_FILE,
                      private_mode=False, storage_path=storage)
    except Exception:
        webview.start(icon=ICON_FILE, private_mode=False, storage_path=storage)
