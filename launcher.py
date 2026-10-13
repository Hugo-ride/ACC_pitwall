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
import ctypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from re import fullmatch
from urllib.parse import unquote, urlencode, urlsplit

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


class _UIRequestHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        route = unquote(urlsplit(path).path).lstrip("/")
        if not route:
            route = "acc_pitwall.html"
        if route in {"acc_pitwall.html", "app_icon_512.png", "track_locations.js"}:
            return os.path.join(BASE_PATH, route)
        if fullmatch(r"track_(?:maps|flags)/[A-Za-z0-9_-]+\.svg", route):
            return os.path.join(BASE_PATH, route)
        return os.path.join(BASE_PATH, "__not_found__")


def _start_ui_server():
    if not os.path.isfile(HTML_FILE):
        raise FileNotFoundError(f"Interface ACC Pit Wall introuvable : {HTML_FILE}")
    server = ThreadingHTTPServer(("127.0.0.1", 0), _UIRequestHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


# ── Constantes ──────────────────────────────────────────────────
DEV_MODE    = os.environ.get("ACC_PITWALL_DEV") == "1" or (
    getattr(sys, "frozen", False)
    and os.path.basename(sys.executable).lower().endswith("_dev.exe")
)
if DEV_MODE:
    os.environ["ACC_PITWALL_DEV"] = "1"

APP_NAME    = "ACC Pit Wall Dev" if DEV_MODE else "ACC Pit Wall"
from version import APP_VERSION
WS_HOST     = "127.0.0.1"
WS_PORT     = 8765
HTML_FILE   = resource_path("acc_pitwall.html")
ICON_FILE   = resource_path("app_icon.ico")

# ── Serveur WebSocket ────────────────────────────────────────────
_server_running = False
_server_error = None

def _is_port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((WS_HOST, port)) != 0

def _run_server():
    global _server_error, _server_running
    _server_running = True
    try:
        import asyncio
        if BASE_PATH not in sys.path:
            sys.path.insert(0, BASE_PATH)
        from server import ACCServer
        asyncio.run(ACCServer().run())
    except Exception as exc:
        _server_error = exc
        import traceback
        traceback.print_exc()
    finally:
        _server_running = False

def _wait_for_server(server_thread, timeout=10.0):
    end = time.time() + timeout
    while time.time() < end:
        if not _is_port_free(WS_PORT):
            return True
        if not server_thread.is_alive():
            return False
        time.sleep(0.1)
    return False

# ── Point d'entrée ───────────────────────────────────────────────
if __name__ == '__main__':
    # 1. Démarrer le serveur WebSocket en arrière-plan
    server_thread = threading.Thread(target=_run_server, daemon=True)
    server_thread.start()
    if not _wait_for_server(server_thread):
        reason = f"\n\nDétail : {_server_error}" if _server_error else ""
        message = (
            "Le serveur ACC Pit Wall n'a pas démarré. "
            "Vérifie les données de l'application et que le port local 8765 est libre."
            f"{reason}"
        )
        ctypes.windll.user32.MessageBoxW(None, message, APP_NAME, 0x10)
        raise SystemExit(1)

    # 2. Servir l'interface sur localhost pour éviter les erreurs de chemins file://.
    ui_server = _start_ui_server()

    # 3. Ouvrir l'interface dans une fenêtre native via pywebview
    import webview

    query = urlencode({
        "version": APP_VERSION,
        "channel": "dev" if DEV_MODE else "stable",
    })
    url = f"http://127.0.0.1:{ui_server.server_port}/acc_pitwall.html?{query}"

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
