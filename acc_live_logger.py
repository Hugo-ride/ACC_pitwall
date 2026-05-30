# -*- coding: utf-8 -*-
"""
ACC Live Logger
- Lance ACC, fait des tours, le logger enregistre tout automatiquement.
- Tape S + Entrée à tout moment pour calculer la stratégie essence.
- Tape Q + Entrée pour quitter.
"""

import time
import sys
import threading
from fuel_calculator import (
    save_lap_data, print_stats, format_time,
    calculate_fuel_strategy, print_strategy, parse_time, load_session_data
)

try:
    from acc_shared_memory import ACCSharedMemoryReader
    SHM_AVAILABLE = True
except ImportError:
    SHM_AVAILABLE = False


class ACCLiveLogger:

    POLL_INTERVAL = 0.5

    def __init__(self):
        self.reader = ACCSharedMemoryReader() if SHM_AVAILABLE else None

        self.last_lap_count = -1
        self.current_car    = None
        self.current_track  = None
        self.tank_capacity  = 120.0
        self.session_laps   = []
        self.running        = False
        self.fuel_strategy  = None
        self._live_counter  = 0
        self._acc_detected  = False

        # Commandes clavier reçues depuis le thread
        self._cmd_queue = []
        self._cmd_lock  = threading.Lock()

    # ──────────────────────────────────────────
    # DÉMARRAGE
    # ──────────────────────────────────────────

    def start(self):
        if not SHM_AVAILABLE:
            print("[ERR]  Module acc_shared_memory non disponible.")
            return

        print("\n" + "=" * 60)
        print("  [OK]  ACC LIVE LOGGER demarré")
        print("  Le logger enregistre chaque tour automatiquement.")
        print()
        print("  Commandes disponibles à tout moment :")
        print("    S  ->  Calculer la stratégie essence")
        print("    Q  ->  Quitter")
        print("=" * 60 + "\n")

        # Thread clavier (tourne en parallèle, ne bloque pas le logger)
        kb_thread = threading.Thread(target=self._keyboard_loop, daemon=True)
        kb_thread.start()

        self.running = True
        self._run_loop()

    # ──────────────────────────────────────────
    # THREAD CLAVIER
    # ──────────────────────────────────────────

    def _keyboard_loop(self):
        """Lit le clavier en continu dans un thread séparé."""
        while self.running:
            try:
                cmd = input().strip().lower()
                with self._cmd_lock:
                    self._cmd_queue.append(cmd)
            except EOFError:
                break

    def _process_commands(self, snap):
        """Traite les commandes clavier en attente."""
        with self._cmd_lock:
            cmds = list(self._cmd_queue)
            self._cmd_queue.clear()

        for cmd in cmds:
            if cmd == "q":
                print("\n  [STOP]  Arrêt demandé.")
                self.running = False

            elif cmd == "s":
                self._interactive_strategy(snap)

    def _interactive_strategy(self, snap):
        """Calcule la stratégie à la demande — pose juste les questions nécessaires."""
        print("\n" + "-" * 60)
        print("  [CALC]  CALCUL DE STRATÉGIE")
        print("-" * 60)

        # Données réelles de la session en cours
        if self.session_laps:
            times     = [l["lap_time_sec"] for l in self.session_laps]
            fuels     = [l["fuel_used"]    for l in self.session_laps]
            avg_time  = sum(times) / len(times)
            avg_fuel  = sum(fuels) / len(fuels)
            best_time = min(times)
            print(f"  Données de cette session ({len(self.session_laps)} tours) :")
            print(f"    Temps moy  : {format_time(avg_time)}  |  Meilleur : {format_time(best_time)}")
            print(f"    Conso moy  : {avg_fuel:.3f} L/tour")
        else:
            # Pas encore de tours — chercher l'historique
            hist     = load_session_data(self.current_car or "?", self.current_track or "?")
            avg_fuel_h = hist.get("stats", {}).get("avg_fuel_per_lap")
            avg_time_h = hist.get("stats", {}).get("avg_lap_time_sec")
            if avg_fuel_h:
                avg_fuel = avg_fuel_h
                avg_time = avg_time_h
                print(f"  Données historiques utilisées :")
                print(f"    Temps moy  : {format_time(avg_time)}")
                print(f"    Conso moy  : {avg_fuel:.3f} L/tour")
            else:
                avg_fuel = None
                avg_time = None
                print("  Aucun tour enregistré pour l'instant.")

        print("-" * 60)

        # Durée de course — toujours demandée
        while True:
            raw = input("  [TIME]  Durée de la course (minutes) : ").strip()
            if not raw:
                print("  (Annulé)")
                print("-" * 60 + "\n")
                return
            try:
                duration = float(raw)
                break
            except ValueError:
                print("  [!]  Entrez un nombre, ex: 60")

        # Conso — demander seulement si on n'a pas de données
        if avg_fuel is None:
            raw_fuel = input("  [FUEL]  Conso estimée par tour (L) : ").strip()
            try:
                avg_fuel = float(raw_fuel)
            except ValueError:
                print("  [!]  Valeur invalide, annulé.")
                print("-" * 60 + "\n")
                return

        # Temps au tour — demander seulement si on n'a pas de données
        if avg_time is None:
            raw_lap = input("  [LAP]  Temps au tour estimé (ex: 1:47.500) : ").strip()
            try:
                avg_time = parse_time(raw_lap)
            except ValueError:
                print("  [!]  Format invalide, annulé.")
                print("-" * 60 + "\n")
                return

        # Tour de formation
        formation_raw = input("  Tour de formation ? (o/n, défaut n) : ").strip().lower()
        formation = formation_raw in ("o", "oui", "y", "yes")

        # Calcul et affichage
        result = calculate_fuel_strategy(
            race_duration_minutes=duration,
            lap_time_seconds=avg_time,
            fuel_per_lap=avg_fuel,
            fuel_tank_capacity=snap["tank_capacity"] if snap else self.tank_capacity,
            formation_lap=formation,
        )
        self.fuel_strategy = result
        print_strategy(result)

    # ──────────────────────────────────────────
    # BOUCLE PRINCIPALE
    # ──────────────────────────────────────────

    def _run_loop(self):
        try:
            while self.running:
                if not self.reader.is_connected():
                    self.reader.connect()
                    time.sleep(1)
                    continue

                snap = self.reader.get_snapshot()

                if snap is None:
                    self._process_commands(None)
                    time.sleep(1)
                    continue

                status = snap.get("status", "OFF")

                if status == "Live":
                    if not self._acc_detected:
                        print("  [OK]  ACC détecté — session active !\n")
                        self._acc_detected = True
                    self._process_snapshot(snap)
                    self._process_commands(snap)

                else:
                    if self._acc_detected and self.current_car:
                        print("\n  [PAUSE]  Session terminée.")
                        self._print_session_summary()
                        print_stats(self.current_car, self.current_track)
                        self._reset_session()
                    self._acc_detected = False
                    self._process_commands(None)

                time.sleep(self.POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n  [STOP]  Logger arrêté.")
            if self.current_car:
                self._print_session_summary()
                print_stats(self.current_car, self.current_track)
        finally:
            self.running = False
            if self.reader:
                self.reader.disconnect()

    # ──────────────────────────────────────────
    # TRAITEMENT SESSION
    # ──────────────────────────────────────────

    def _process_snapshot(self, snap):
        car   = snap["car"]
        track = snap["track"]
        laps  = snap["completed_laps"]

        # Nouvelle voiture / circuit
        if car != self.current_car or track != self.current_track:
            self._reset_session()
            self.current_car   = car
            self.current_track = track
            self.tank_capacity = snap["tank_capacity"]
            self.last_lap_count = laps

            hist     = load_session_data(car, track)
            n_hist   = hist.get("stats", {}).get("total_laps", 0)
            avg_fuel = hist.get("stats", {}).get("avg_fuel_per_lap", "-")

            print(f"{'='*60}")
            print(f"  [CAR]  {car}  @  {track}")
            print(f"  [SESSION]  Session : {snap['session_type']}  |  Réservoir : {snap['tank_capacity']} L")
            if n_hist:
                print(f"  [STAT]  Historique : {n_hist} tours, conso moy. {avg_fuel} L/tour")
            else:
                print(f"  [STAT]  Pas encore d'historique pour cette combinaison")
            print(f"  [HELP]  Tape  S + Entrée  pour calculer la stratégie essence")
            print(f"{'='*60}\n")
            return

        # Nouveau tour
        if laps > self.last_lap_count and self.last_lap_count >= 0:
            self._record_lap(snap, laps)

        self.last_lap_count = laps
        self._display_live_status(snap)

    def _record_lap(self, snap, lap_number):
        lap_time_sec = snap["last_lap_sec"]
        fuel_used    = snap["fuel_per_lap"]

        if lap_time_sec <= 0:
            return

        lap_data = {
            "lap_number":     lap_number,
            "lap_time_sec":   round(lap_time_sec, 3),
            "fuel_used":      round(fuel_used, 3),
            "session_type":   snap["session_type"],
            "fuel_remaining": snap["fuel_remaining"],
            "tyre_compound":  snap["tyre_compound"],
            "air_temp":       snap["air_temp"],
            "road_temp":      snap["road_temp"],
        }
        self.session_laps.append(lap_data)
        save_lap_data(self.current_car, self.current_track, lap_data)

        print(f"  [LAP]  Tour {lap_number:3d} | "
              f"{format_time(lap_time_sec)} | "
              f"Conso {fuel_used:.2f} L | "
              f"Fuel {snap['fuel_remaining']:.1f} L restant")

        # Rappel après chaque tour si stratégie pas encore calculée
        if not self.fuel_strategy and len(self.session_laps) >= 1:
            print(f"       [HELP]  Tape  S + Entrée  pour calculer la stratégie")

        # En course : suggestion pit
        if snap["session_type"] == "Race" and snap["session_time_left_sec"] > 0 and self.fuel_strategy:
            self._suggest_pit_fuel(snap, fuel_used)

    def _suggest_pit_fuel(self, snap, fuel_per_lap):
        time_left = snap["session_time_left_sec"]
        last_lap  = snap["last_lap_sec"]
        fuel_left = snap["fuel_remaining"]
        if last_lap <= 0 or fuel_per_lap <= 0:
            return
        laps_left = time_left / last_lap
        to_add    = max(0, (laps_left + 1) * fuel_per_lap - fuel_left)
        if to_add > 0:
            print(f"       [FUEL]  ~{laps_left:.1f} tours restants -> Ajouter {to_add:.0f} L au prochain arrêt")

    def _display_live_status(self, snap):
        self._live_counter += 1
        if self._live_counter % 20 == 0:
            tl   = snap["session_time_left_sec"]
            mins = int(tl // 60)
            secs = int(tl % 60)
            print(f"  [TIME]  {mins}:{secs:02d} restant | "
                  f"Pos {snap['position']} | "
                  f"Fuel {snap['fuel_remaining']:.1f} L | "
                  f"{snap['speed_kmh']:.0f} km/h")

    def _reset_session(self):
        self.current_car    = None
        self.current_track  = None
        self.last_lap_count = -1
        self.session_laps   = []
        self.fuel_strategy  = None
        self._live_counter  = 0

    def _print_session_summary(self):
        if not self.session_laps:
            return
        times = [l["lap_time_sec"] for l in self.session_laps if l["lap_time_sec"] > 0]
        fuels = [l["fuel_used"]    for l in self.session_laps if l["fuel_used"] > 0]
        print(f"\n  📋  Résumé — {len(self.session_laps)} tours enregistrés")
        if times:
            print(f"      Meilleur : {format_time(min(times))} | "
                  f"Moyen : {format_time(sum(times)/len(times))}")
        if fuels:
            print(f"      Conso moy : {sum(fuels)/len(fuels):.3f} L/tour")


# ──────────────────────────────────────────────
# MODE SIMULATION
# ──────────────────────────────────────────────

def simulate_session():
    import random

    print("\n  [TEST]  MODE SIMULATION")
    car    = input("  Voiture (ex: ferrari_488_gt3_evo) : ").strip() or "ferrari_488_gt3_evo"
    track  = input("  Circuit (ex: monza) : ").strip() or "monza"
    n_laps = int(input("  Nombre de tours (défaut 10) : ") or "10")

    print(f"\n  Simulation de {n_laps} tours...\n")
    for i in range(1, n_laps + 1):
        lap_data = {
            "lap_number":    i,
            "lap_time_sec":  round(105.5 + random.uniform(-1.5, 3.0), 3),
            "fuel_used":     round(2.8   + random.uniform(-0.2, 0.4), 3),
            "session_type":  "Race",
            "tyre_compound": "DHE",
            "air_temp":      22.0,
            "road_temp":     35.0,
        }
        save_lap_data(car, track, lap_data)
        print(f"  Tour {i:3d} | {format_time(lap_data['lap_time_sec'])} | "
              f"{lap_data['fuel_used']:.2f} L")
        time.sleep(0.05)

    print(f"\n  [OK]  Terminé !\n")
    print_stats(car, track)


# ──────────────────────────────────────────────
# POINT D'ENTRÉE
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  ACC LIVE LOGGER")
    print("  " + "-" * 39)
    print("  1. Démarrer le logger")
    print("  2. Simulation (test sans ACC)")
    print("  3. Afficher les statistiques")

    choice = input("\n  Choix (1/2/3) : ").strip()

    if choice == "1":
        logger = ACCLiveLogger()
        logger.start()

    elif choice == "2":
        simulate_session()

    elif choice == "3":
        from fuel_calculator import list_all_data
        entries = list_all_data()
        if entries:
            car   = input("  Voiture : ").strip()
            track = input("  Circuit : ").strip()
            print_stats(car, track)
