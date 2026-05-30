# -*- coding: utf-8 -*-
"""
ACC Pit Wall — Launcher principal
Gère le démarrage du serveur WebSocket et l'interface graphique.
"""

import sys
import os
import time
import threading
import webbrowser
import socket

# ── Résoudre le chemin des ressources (PyInstaller ou dev) ──────
def resource_path(relative_path):
    """Retourne le chemin absolu vers une ressource (compatible PyInstaller)."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative_path)

# ── Imports GUI ─────────────────────────────────────────────────
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

# ── Constantes ──────────────────────────────────────────────────
APP_NAME    = "ACC Pit Wall"
APP_VERSION = "1.0.0"
WS_PORT     = 8765
WS_HOST     = "localhost"
HTML_FILE   = resource_path("acc_pitwall.html")
ICON_FILE   = resource_path("app_icon.ico")
ICON_PNG    = resource_path("app_icon_512.png")

# ══════════════════════════════════════════════════════════════════
#  SERVEUR — lancé dans un thread séparé
# ══════════════════════════════════════════════════════════════════
server_process  = None
server_thread   = None
server_running  = False
server_log_lines = []
log_callbacks   = []

def add_log(line):
    server_log_lines.append(line)
    if len(server_log_lines) > 200:
        server_log_lines.pop(0)
    for cb in log_callbacks:
        try: cb(line)
        except: pass

def is_port_free(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((WS_HOST, port)) != 0

def start_server():
    """Démarre le serveur WebSocket dans le même processus que l'application.

    Dans un .exe PyInstaller, relancer sys.executable pour lancer server.py
    relance en réalité ACC_PitWall.exe lui-même. Cela créait une boucle
    infinie de fenêtres/pages navigateur. On importe donc server.py et on lance
    ACCServer directement dans ce thread.
    """
    global server_running

    if server_running:
        add_log("[APW] Serveur déjà démarré.")
        return

    add_log("[APW] Démarrage du serveur...")
    server_running = True

    try:
        import asyncio
        from server import ACCServer

        srv = ACCServer()
        add_log(f"[APW] Serveur actif sur ws://{WS_HOST}:{WS_PORT}")
        asyncio.run(srv.run())

    except Exception as e:
        add_log(f"[APW] ERREUR serveur : {e}")

    finally:
        server_running = False
        add_log("[APW] Serveur arrêté.")

def launch_server_thread():
    global server_thread
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

def wait_for_server(timeout=10):
    """Attend que le serveur soit prêt sur le port WS."""
    start = time.time()
    while time.time() - start < timeout:
        if not is_port_free(WS_PORT):
            return True
        time.sleep(0.2)
    return False

def open_interface():
    """Ouvre l'interface HTML dans le navigateur par défaut."""
    html_path = HTML_FILE
    if sys.platform == 'win32':
        url = 'file:///' + html_path.replace('\\', '/')
    else:
        url = 'file://' + html_path
    webbrowser.open(url)

# ══════════════════════════════════════════════════════════════════
#  INTERFACE TKINTER — fenêtre de contrôle
# ══════════════════════════════════════════════════════════════════
class APWApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(APP_NAME)
        self.resizable(False, False)
        self.configure(bg='#0d0f12')

        # Icône
        try:
            self.iconbitmap(ICON_FILE)
        except:
            pass

        # Centrer la fenêtre
        w, h = 520, 620
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

        self._build_ui()
        self._state = 'stopped'   # stopped | starting | running | acc_live
        self._server_started = False
        self._server_starting = False
        self._interface_opened = False

        # Démarrer le serveur immédiatement en arrière-plan
        self.after(200, self._auto_start)

        # Polling status
        self.after(500, self._poll_status)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ── BUILD UI ────────────────────────────────────────────────
    def _build_ui(self):
        C = {
            'bg0': '#0d0f12', 'bg1': '#131619', 'bg2': '#191d22', 'bg3': '#1f252c',
            'red': '#e8354a', 'green': '#2ecc8a', 'amber': '#f5a623',
            'text0': '#eef0f3', 'text1': '#9ba5b4', 'text2': '#4e5a6a',
        }
        self.C = C

        # Logo
        try:
            logo_img = Image.open(ICON_PNG).convert('RGBA')
            logo_img = logo_img.resize((256, 256), Image.LANCZOS)
            self._logo_photo = ImageTk.PhotoImage(logo_img)
            tk.Label(self, image=self._logo_photo, bg=C['bg0']).pack(pady=(22, 6))
        except:
            pass

        # Titre
        tk.Label(self, text="ACC PIT WALL", font=('Segoe UI', 20, 'bold'),
                 fg=C['red'], bg=C['bg0']).pack()
        tk.Label(self, text=f"v{APP_VERSION}", font=('Segoe UI', 9),
                 fg=C['text2'], bg=C['bg0']).pack(pady=(0, 16))

        # ── Status card ──
        card = tk.Frame(self, bg=C['bg1'], bd=0, highlightthickness=1,
                        highlightbackground=C['bg3'])
        card.pack(fill='x', padx=24, pady=(0, 14))

        row1 = tk.Frame(card, bg=C['bg1'])
        row1.pack(fill='x', padx=16, pady=(14, 6))

        self._dot = tk.Canvas(row1, width=12, height=12, bg=C['bg1'],
                              highlightthickness=0)
        self._dot.pack(side='left', padx=(0, 8))
        self._dot_oval = self._dot.create_oval(1, 1, 11, 11, fill='#444', outline='')

        self._status_var = tk.StringVar(value="Démarrage...")
        tk.Label(row1, textvariable=self._status_var, font=('Segoe UI', 11, 'bold'),
                 fg=C['text0'], bg=C['bg1']).pack(side='left')

        self._substatus_var = tk.StringVar(value="Initialisation en cours")
        tk.Label(card, textvariable=self._substatus_var, font=('Segoe UI', 9),
                 fg=C['text1'], bg=C['bg1']).pack(padx=16, pady=(0, 14), anchor='w')

        # ── Bouton ouvrir interface ──
        self._open_btn = tk.Button(
            self, text="⬛  OUVRIR L'INTERFACE",
            font=('Segoe UI', 11, 'bold'), fg='white', bg=C['red'],
            activeforeground='white', activebackground='#ff5566',
            relief='flat', cursor='hand2', pady=10,
            command=self._open_interface, state='disabled'
        )
        self._open_btn.pack(fill='x', padx=24, pady=(0, 8))

        # ── ACC Status ──
        acc_card = tk.Frame(self, bg=C['bg2'], bd=0, highlightthickness=1,
                            highlightbackground=C['bg3'])
        acc_card.pack(fill='x', padx=24, pady=(0, 14))

        tk.Label(acc_card, text="STATUT ACC", font=('Segoe UI', 8, 'bold'),
                 fg=C['text2'], bg=C['bg2']).pack(anchor='w', padx=14, pady=(10, 3))

        self._acc_var = tk.StringVar(value="En attente du jeu...")
        tk.Label(acc_card, textvariable=self._acc_var, font=('Segoe UI', 10),
                 fg=C['text1'], bg=C['bg2']).pack(anchor='w', padx=14, pady=(0, 10))

        # ── Log console ──
        log_lbl = tk.Frame(self, bg=C['bg0'])
        log_lbl.pack(fill='x', padx=24, pady=(0, 4))
        tk.Label(log_lbl, text="JOURNAL", font=('Segoe UI', 8, 'bold'),
                 fg=C['text2'], bg=C['bg0']).pack(side='left')

        log_frame = tk.Frame(self, bg=C['bg1'], highlightthickness=1,
                             highlightbackground=C['bg3'])
        log_frame.pack(fill='both', expand=True, padx=24, pady=(0, 16))

        self._log_text = tk.Text(
            log_frame, bg=C['bg1'], fg=C['text2'],
            font=('Consolas', 8), relief='flat', state='disabled',
            wrap='word', bd=0, padx=8, pady=6, insertbackground=C['text0']
        )
        scrollbar = tk.Scrollbar(log_frame, command=self._log_text.yview,
                                 bg=C['bg2'], troughcolor=C['bg1'])
        self._log_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')
        self._log_text.pack(fill='both', expand=True)

        # Tags de couleur pour le log
        self._log_text.tag_configure('green',  foreground=C['green'])
        self._log_text.tag_configure('red',    foreground=C['red'])
        self._log_text.tag_configure('amber',  foreground=C['amber'])
        self._log_text.tag_configure('normal', foreground=C['text2'])

        # Enregistrer le callback log
        log_callbacks.append(self._append_log)

    # ── ACTIONS ────────────────────────────────────────────────
    def _auto_start(self):
        if self._server_starting or self._server_started:
            return
        self._server_starting = True
        self._set_status('starting', "Démarrage du serveur...", "Initialisation")
        launch_server_thread()
        # Attendre que le port soit ouvert
        self.after(300, self._check_server_ready)

    def _check_server_ready(self, attempt=0):
        if not is_port_free(WS_PORT):
            self._server_started = True
            self._server_starting = False
            self._set_status('running', "Serveur actif", "Prêt — Ouvrez l'interface")
            self._open_btn.config(state='normal')
            # Ouvrir automatiquement le navigateur une seule fois
            if not self._interface_opened:
                self.after(400, self._open_interface)
        elif attempt < 30:
            self.after(300, lambda: self._check_server_ready(attempt + 1))
        else:
            self._server_starting = False
            self._set_status('error', "Erreur de démarrage",
                             "Le serveur n'a pas pu démarrer")

    def _open_interface(self):
        if not self._interface_opened:
            open_interface()
            self._interface_opened = True
        self._set_status('running', "Interface ouverte", "Le navigateur est lancé")

    def _set_status(self, state, label, sublabel):
        self._state = state
        self._status_var.set(label)
        self._substatus_var.set(sublabel)
        colors = {
            'stopped':  '#555',
            'starting': self.C['amber'],
            'running':  self.C['green'],
            'error':    self.C['red'],
            'acc_live': self.C['green'],
        }
        color = colors.get(state, '#555')
        self._dot.itemconfig(self._dot_oval, fill=color)

    def _append_log(self, line):
        """Ajoute une ligne dans le log (thread-safe via after)."""
        self.after(0, lambda l=line: self._do_append_log(l))

    def _do_append_log(self, line):
        self._log_text.config(state='normal')
        tag = 'normal'
        lo = line.lower()
        if '✅' in line or 'ok' in lo or 'connecté' in lo or 'démarr' in lo or 'vert' in lo or '🟢' in line:
            tag = 'green'
        elif '❌' in line or 'erreur' in lo or 'error' in lo or 'crash' in lo:
            tag = 'red'
        elif '⚠️' in line or 'warn' in lo or 'attente' in lo or '🟡' in line:
            tag = 'amber'
        # Détecter ACC live
        if 'session active' in lo or '🟢' in line:
            self._acc_var.set("Session active ✓")
            self._set_status('acc_live', "ACC détecté !", "Session en cours")
        elif 'offline' in lo or 'hors ligne' in lo:
            self._acc_var.set("ACC hors ligne")
        self._log_text.insert('end', line + '\n', tag)
        self._log_text.see('end')
        self._log_text.config(state='disabled')

    def _poll_status(self):
        """Vérifie le statut du serveur toutes les 2s."""
        if self._server_started and is_port_free(WS_PORT):
            self._set_status('error', "Serveur arrêté", "Redémarrage en cours...")
            self._server_started = False
            self._server_starting = False
            self.after(1000, self._auto_start)
        self.after(2000, self._poll_status)

    def _on_close(self):
        if messagebox.askokcancel("Quitter", "Fermer ACC Pit Wall ?"):
            self.destroy()
            os._exit(0)


# ══════════════════════════════════════════════════════════════════
#  POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    app = APWApp()
    app.mainloop()
