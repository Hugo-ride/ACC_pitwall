# -*- coding: utf-8 -*-
"""
ACC Pit Wall Calculator
Calcule la stratégie essence pour Assetto Corsa Competizione.
Supporte le calcul manuel et la lecture des données en temps réel via Shared Memory.
"""

import math
import json
import os
from datetime import datetime
from pathlib import Path


# ──────────────────────────────────────────────
# CALCUL DE STRATÉGIE
# ──────────────────────────────────────────────

def parse_time(time_str: str) -> float:
    """
    Convertit un temps au format MM:SS.mmm ou SS.mmm en secondes.
    Ex: '1:45.234' → 105.234 | '105.234' → 105.234
    """
    time_str = time_str.strip()
    if ':' in time_str:
        parts = time_str.split(':')
        minutes = int(parts[0])
        seconds = float(parts[1])
        return minutes * 60 + seconds
    else:
        return float(time_str)


def format_time(seconds: float) -> str:
    """Convertit des secondes en format MM:SS.mmm"""
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:06.3f}"


def calculate_fuel_strategy(
    race_duration_minutes: float,
    lap_time_seconds: float,
    fuel_per_lap: float,
    fuel_tank_capacity: float = 120.0,
    safety_margin: float = 1.0,
    formation_lap: bool = False
) -> dict:
    """
    Calcule la stratégie essence complète pour une course.

    Args:
        race_duration_minutes: Durée de la course en minutes
        lap_time_seconds: Temps au tour en secondes
        fuel_per_lap: Consommation par tour en litres
        fuel_tank_capacity: Capacité du réservoir (défaut 120L)
        safety_margin: Tours supplémentaires de sécurité (défaut 1)
        formation_lap: Ajouter un tour de formation

    Returns:
        dict avec tous les détails de stratégie
    """
    race_duration_sec = race_duration_minutes * 60

    # Nombre de tours estimés (arrondi au supérieur)
    estimated_laps = math.ceil(race_duration_sec / lap_time_seconds)

    # Tours avec marge de sécurité
    laps_with_margin = estimated_laps + safety_margin
    if formation_lap:
        laps_with_margin += 1

    # Carburant nécessaire
    fuel_needed = laps_with_margin * fuel_per_lap
    fuel_to_load = min(math.ceil(fuel_needed), int(fuel_tank_capacity))

    # Nombre de pit stops nécessaires
    max_laps_per_tank = fuel_tank_capacity / fuel_per_lap
    pit_stops_needed = max(0, math.ceil(estimated_laps / max_laps_per_tank) - 1)

    # Fenêtre de pit stop optimale
    pit_windows = []
    if pit_stops_needed > 0:
        laps_per_stint = estimated_laps / (pit_stops_needed + 1)
        for i in range(1, pit_stops_needed + 1):
            pit_lap = round(laps_per_stint * i)
            pit_windows.append(pit_lap)

    return {
        "race_duration_min": race_duration_minutes,
        "lap_time": format_time(lap_time_seconds),
        "lap_time_sec": lap_time_seconds,
        "fuel_per_lap": fuel_per_lap,
        "estimated_laps": estimated_laps,
        "laps_with_margin": laps_with_margin,
        "fuel_needed_raw": round(fuel_needed, 2),
        "fuel_to_load": fuel_to_load,
        "tank_capacity": fuel_tank_capacity,
        "pit_stops_needed": pit_stops_needed,
        "pit_windows": pit_windows,
        "formation_lap": formation_lap,
        "safety_margin_laps": safety_margin,
    }


def print_strategy(result: dict):
    """Affiche la stratégie de façon lisible dans le terminal."""
    print("\n" + "=" * 50)
    print("  [*]  ACC PIT WALL CALCULATOR")
    print("=" * 50)
    print(f"  Durée course       : {result['race_duration_min']} min")
    print(f"  Temps au tour      : {result['lap_time']}")
    print(f"  Conso par tour     : {result['fuel_per_lap']} L")
    print(f"  Tour de formation  : {'Oui' if result['formation_lap'] else 'Non'}")
    print("-" * 50)
    print(f"  Tours estimés      : {result['estimated_laps']}")
    print(f"  Tours avec marge   : {result['laps_with_margin']:.1f}")
    print(f"  Carburant brut     : {result['fuel_needed_raw']} L")
    print(f"  [OK] CHARGER       : {result['fuel_to_load']} L")
    print("-" * 50)
    if result['pit_stops_needed'] == 0:
        print("  Pit stops          : Aucun (no-stop)")
    else:
        print(f"  Pit stops          : {result['pit_stops_needed']}")
        print(f"  Fenêtres pit       : Tours {result['pit_windows']}")
    print("=" * 50 + "\n")


# ──────────────────────────────────────────────
# SAUVEGARDE DES DONNÉES
# ──────────────────────────────────────────────

DATA_DIR = Path.home() / "Documents" / "ACC_pitwall_donnees"


def get_data_file(car: str, track: str) -> Path:
    """Retourne le chemin du fichier de données pour une voiture/circuit."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # Nettoyer les noms pour le système de fichiers
    safe_car = "".join(c if c.isalnum() or c in "-_ " else "_" for c in car)
    safe_track = "".join(c if c.isalnum() or c in "-_ " else "_" for c in track)
    return DATA_DIR / f"{safe_car}__{safe_track}.json"


def load_session_data(car: str, track: str) -> dict:
    """Charge les données existantes pour une voiture/circuit."""
    filepath = get_data_file(car, track)
    if filepath.exists():
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "car": car,
        "track": track,
        "sessions": [],
        "stats": {}
    }


def save_lap_data(car: str, track: str, lap_data: dict):
    """
    Sauvegarde les données d'un tour pour une voiture/circuit.

    lap_data doit contenir:
        - lap_number: int
        - lap_time_sec: float
        - fuel_used: float
        - session_type: str (Practice / Qualifying / Race)
        - timestamp: str (auto-généré si absent)
    """
    data = load_session_data(car, track)
    lap_data.setdefault("timestamp", datetime.now().isoformat())
    lap_data.setdefault("session_type", "Unknown")

    data["sessions"].append(lap_data)

    # Recalculer les stats
    valid_laps = [s for s in data["sessions"]
                  if s.get("lap_time_sec", 0) > 0 and s.get("fuel_used", 0) > 0]

    if valid_laps:
        lap_times = [s["lap_time_sec"] for s in valid_laps]
        fuel_used = [s["fuel_used"] for s in valid_laps]

        data["stats"] = {
            "total_laps": len(valid_laps),
            "avg_lap_time_sec": round(sum(lap_times) / len(lap_times), 3),
            "best_lap_time_sec": round(min(lap_times), 3),
            "avg_fuel_per_lap": round(sum(fuel_used) / len(fuel_used), 3),
            "min_fuel_per_lap": round(min(fuel_used), 3),
            "max_fuel_per_lap": round(max(fuel_used), 3),
            "last_updated": datetime.now().isoformat()
        }

    filepath = get_data_file(car, track)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    return filepath


def print_stats(car: str, track: str):
    """Affiche les statistiques pour une voiture/circuit."""
    data = load_session_data(car, track)
    stats = data.get("stats", {})

    if not stats:
        print(f"\nAucune donnée pour {car} @ {track}")
        return

    print(f"\n{'='*50}")
    print(f"  [STAT]  STATS : {car}")
    print(f"  [CAR]  Circuit : {track}")
    print(f"{'='*50}")
    print(f"  Tours enregistrés  : {stats['total_laps']}")
    print(f"  Meilleur tour      : {format_time(stats['best_lap_time_sec'])}")
    print(f"  Temps moyen        : {format_time(stats['avg_lap_time_sec'])}")
    print(f"  Conso moyenne      : {stats['avg_fuel_per_lap']} L/tour")
    print(f"  Conso min/max      : {stats['min_fuel_per_lap']} / {stats['max_fuel_per_lap']} L")
    print(f"{'='*50}\n")


def list_all_data():
    """Liste toutes les combinaisons voiture/circuit sauvegardées."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    files = list(DATA_DIR.glob("*.json"))
    if not files:
        print("  Aucune donnée sauvegardée.")
        return []

    print(f"\n{'='*50}")
    print("  [SAVE]  DONNÉES SAUVEGARDÉES")
    print(f"{'='*50}")
    entries = []
    for f in sorted(files):
        with open(f, 'r', encoding='utf-8') as fp:
            d = json.load(fp)
        stats = d.get("stats", {})
        laps = stats.get("total_laps", 0)
        avg_fuel = stats.get("avg_fuel_per_lap", "?")
        print(f"  - {d['car']} @ {d['track']} — {laps} tours, {avg_fuel} L/tour moy.")
        entries.append(d)
    print(f"{'='*50}\n")
    return entries


# ──────────────────────────────────────────────
# MODE INTERACTIF (terminal)
# ──────────────────────────────────────────────

def interactive_mode():
    """Mode interactif dans le terminal pour calculer une stratégie."""
    print("\n" + "=" * 50)
    print("  [*]  ACC PIT WALL — Mode manuel")
    print("=" * 50)

    try:
        duration = float(input("  Durée de course (minutes) : "))
        lap_time_str = input("  Temps au tour (ex: 1:45.234) : ")
        lap_time = parse_time(lap_time_str)
        fuel_per_lap = float(input("  Consommation par tour (L) : "))
        tank_cap = input("  Capacité réservoir (défaut 120L) : ").strip()
        tank_cap = float(tank_cap) if tank_cap else 120.0
        formation = input("  Tour de formation ? (o/n, défaut n) : ").strip().lower()
        formation = formation in ('o', 'oui', 'y', 'yes')

        result = calculate_fuel_strategy(
            race_duration_minutes=duration,
            lap_time_seconds=lap_time,
            fuel_per_lap=fuel_per_lap,
            fuel_tank_capacity=tank_cap,
            formation_lap=formation
        )
        print_strategy(result)

        save = input("  Sauvegarder ces données ? (o/n) : ").strip().lower()
        if save in ('o', 'oui', 'y', 'yes'):
            car = input("  Voiture : ").strip()
            track = input("  Circuit : ").strip()
            lap_data = {
                "lap_number": 0,
                "lap_time_sec": lap_time,
                "fuel_used": fuel_per_lap,
                "session_type": "Manual"
            }
            path = save_lap_data(car, track, lap_data)
            print(f"\n  [OK] Données sauvegardées : {path}\n")

    except (ValueError, KeyboardInterrupt) as e:
        print(f"\n  [ERR] Erreur : {e}\n")


if __name__ == "__main__":
    interactive_mode()
