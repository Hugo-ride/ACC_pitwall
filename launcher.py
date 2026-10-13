# -*- coding: utf-8 -*-
"""
ACC Pit Wall — Launcher
Lance le serveur WebSocket et affiche l'interface HTML dans une fenêtre native (pywebview).
"""

import sys
import os
import re
import hashlib
import threading
import socket
import tempfile
import time
import ctypes
from ctypes import wintypes
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from re import fullmatch
from urllib.parse import unquote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

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


class _GitHubAssetRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        redirect = urlsplit(new_url)
        if redirect.scheme != "https" or redirect.hostname not in {
            "github.com",
            "release-assets.githubusercontent.com",
            "objects.githubusercontent.com",
        }:
            raise OSError("Redirection de téléchargement GitHub non autorisée.")
        return super().redirect_request(request, file_pointer, code, message, headers, new_url)


class UpdateApi:
    def __init__(self):
        self._window = None

    def install_update(self, download_url, version, digest=""):
        expected_path = (
            f"/Hugo-ride/ACC_pitwall/releases/download/v{version}/"
            f"ACC_PitWall_Setup_v{version}.exe"
        )
        parsed_url = urlsplit(download_url)
        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname != "github.com"
            or parsed_url.netloc != "github.com"
            or parsed_url.path != expected_path
            or parsed_url.query
            or parsed_url.fragment
            or not re.fullmatch(r"\d+\.\d+\.\d+", version)
        ):
            raise ValueError("Le lien vers l’installateur de mise à jour est invalide.")

        expected_hash = None
        if digest:
            match = re.fullmatch(r"sha256:([0-9a-fA-F]{64})", digest)
            if not match:
                raise ValueError("L’empreinte de l’installateur GitHub est invalide.")
            expected_hash = match.group(1).lower()

        request = Request(
            download_url,
            headers={"User-Agent": "ACC-Pit-Wall-Updater", "Accept": "application/octet-stream"},
        )
        opener = build_opener(_GitHubAssetRedirectHandler())
        installer_path = None
        try:
            with opener.open(request, timeout=60) as response:
                final_url = urlsplit(response.geturl())
                if (
                    final_url.scheme != "https"
                    or final_url.hostname not in {
                        "github.com",
                        "release-assets.githubusercontent.com",
                        "objects.githubusercontent.com",
                    }
                ):
                    raise OSError("L’URL finale du téléchargement n’est pas autorisée.")
                content_length = int(response.headers.get("Content-Length", "0") or 0)
                if content_length > 100 * 1024 * 1024:
                    raise OSError("L’installateur dépasse la taille maximale autorisée.")
                file_descriptor, installer_path = tempfile.mkstemp(
                    prefix=f"ACC_PitWall_Update_v{version}_",
                    suffix=".exe",
                )
                digest_calculator = hashlib.sha256()
                bytes_written = 0
                with os.fdopen(file_descriptor, "wb") as installer_file:
                    while chunk := response.read(1024 * 1024):
                        bytes_written += len(chunk)
                        if bytes_written > 100 * 1024 * 1024:
                            raise OSError("L’installateur dépasse la taille maximale autorisée.")
                        installer_file.write(chunk)
                        digest_calculator.update(chunk)
            if content_length and bytes_written != content_length:
                raise OSError("Le téléchargement de l’installateur est incomplet.")
            if bytes_written < 1024 * 1024:
                raise OSError("Le fichier reçu est trop petit pour être un installateur valide.")
            if expected_hash and digest_calculator.hexdigest() != expected_hash:
                raise OSError("L’empreinte de l’installateur ne correspond pas à celle publiée par GitHub.")

            shell_execute_info = _ShellExecuteInfo()
            shell_execute_info.cbSize = ctypes.sizeof(shell_execute_info)
            shell_execute_info.fMask = 0x00000040  # SEE_MASK_NOCLOSEPROCESS
            shell_execute_info.lpVerb = "runas"
            shell_execute_info.lpFile = installer_path
            shell_execute_info.nShow = 1
            shell_execute_ex = ctypes.windll.shell32.ShellExecuteExW
            shell_execute_ex.argtypes = (ctypes.POINTER(_ShellExecuteInfo),)
            shell_execute_ex.restype = wintypes.BOOL
            if not shell_execute_ex(ctypes.byref(shell_execute_info)):
                raise ctypes.WinError(ctypes.get_last_error())

            if not shell_execute_info.hProcess:
                raise OSError("Windows n’a pas fourni le processus de l’installateur.")
            threading.Thread(
                target=_wait_for_installer,
                args=(shell_execute_info.hProcess, installer_path),
                daemon=True,
            ).start()
            if self._window is not None:
                threading.Timer(1.5, self._window.destroy).start()
            return "Téléchargement terminé. L’installateur va démarrer."
        except Exception:
            if installer_path and os.path.exists(installer_path):
                os.remove(installer_path)
            raise


class _ShellExecuteInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("fMask", wintypes.ULONG),
        ("hwnd", wintypes.HWND),
        ("lpVerb", wintypes.LPCWSTR),
        ("lpFile", wintypes.LPCWSTR),
        ("lpParameters", wintypes.LPCWSTR),
        ("lpDirectory", wintypes.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", wintypes.HINSTANCE),
        ("lpIDList", wintypes.LPVOID),
        ("lpClass", wintypes.LPCWSTR),
        ("hkeyClass", wintypes.HKEY),
        ("dwHotKey", wintypes.DWORD),
        ("hIconOrMonitor", wintypes.HANDLE),
        ("hProcess", wintypes.HANDLE),
    ]


def _wait_for_installer(process_handle, installer_path):
    wait_for_single_object = ctypes.windll.kernel32.WaitForSingleObject
    wait_for_single_object.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    wait_for_single_object.restype = wintypes.DWORD
    close_handle = ctypes.windll.kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL
    wait_for_single_object(process_handle, 0xFFFFFFFF)
    if not close_handle(process_handle):
        print(f"[!] Impossible de fermer la poignée de l’installateur : {ctypes.WinError(ctypes.get_last_error())}")
    try:
        os.remove(installer_path)
    except OSError as error:
        print(f"[!] Impossible de supprimer l’installateur temporaire : {error}")


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

    update_api = UpdateApi()
    window = webview.create_window(
        title=APP_NAME,
        url=url,
        width=1600,
        height=950,
        min_size=(1200, 700),
        background_color='#0a0b0d',
        js_api=update_api,
    )
    update_api._window = window

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
