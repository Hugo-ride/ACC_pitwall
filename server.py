"""
ACC Fuel Strategy — Serveur WebSocket
Lit la mémoire partagée d'ACC toutes les 500ms et diffuse
les données en temps réel à l'interface HTML.

Installation (une seule fois) :
    pip install websockets

Lancement :
    python server.py

Puis ouvrir acc_fuel_strategy.html dans le navigateur.
"""

import asyncio
import json
import math
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

try:
    import websockets  # type: ignore
except ImportError:
    print("=" * 55)
    print("  Installation requise :")
    print("  pip install websockets")
    print("=" * 55)
    sys.exit(1)

try:
    from acc_shared_memory import ACCSharedMemoryReader
    SHM_AVAILABLE = True
except ImportError:
    print("⚠️  acc_shared_memory.py introuvable — mode simulation activé")
    SHM_AVAILABLE = False

# ── SAUVEGARDE JSON ──────────────────────────────────────────────
DEV_MODE = os.environ.get("ACC_PITWALL_DEV") == "1"
if DEV_MODE:
    local_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    DATA_DIR = local_data / "ACC_PitWall_Dev" / "data"
    RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    DEV_SEED_DIR = RESOURCE_DIR / "ACC_pitwall_donnees"
else:
    DATA_DIR = Path.home() / "Documents" / "ACC_pitwall_donnees"


def _seed_dev_data() -> None:
    if not DEV_MODE:
        return
    if not DEV_SEED_DIR.is_dir():
        raise FileNotFoundError(f"Dossier de données développeur introuvable : {DEV_SEED_DIR}")

    seed_files = sorted(DEV_SEED_DIR.glob("*.json"))
    if not seed_files:
        raise FileNotFoundError(f"Aucun fichier JSON dans les données développeur : {DEV_SEED_DIR}")

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    copied = 0
    for source in seed_files:
        target = DATA_DIR / source.name
        if not target.exists():
            shutil.copy2(source, target)
            copied += 1
    if copied:
        print(f"  Données développeur initialisées : {copied} fichiers copiés dans {DATA_DIR}")

LAP_STATUS = {
    "valid": "Valide",
    "track_limits": "Limites de piste",
    "manual_excluded": "Exclu manuellement",
    "auto_outlier": "Exclu auto (aberrant)",
}
INCLUDED_STATUSES = {"valid"}


def get_data_file(car: str, track: str) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    safe = lambda s: "".join(c if c.isalnum() or c in "-_ " else "_" for c in s)
    return DATA_DIR / f"{safe(car)}__{safe(track)}.json"


def load_session_data(car: str, track: str) -> dict:
    """Charge les données existantes pour une voiture/circuit."""
    filepath = get_data_file(car, track)
    if filepath.exists():
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"car": car, "track": track, "sessions": [], "stats": {}}


def _make_lap_id(lap: dict, index: int) -> str:
    ts = lap.get("timestamp") or datetime.now().isoformat()
    lap_no = lap.get("lap_number", index + 1)
    return f"{lap_no}_{ts}".replace(":", "-").replace(".", "-")


def _normalize_lap(lap: dict, index: int) -> dict:
    lap.setdefault("lap_id", _make_lap_id(lap, index))
    lap.setdefault("lap_number", index + 1)
    lap.setdefault("session_type", "Unknown")
    lap.setdefault("status", "valid")
    lap.setdefault("status_locked", False)
    if lap.get("status") not in LAP_STATUS:
        lap["status"] = "valid"
    return lap


def _detect_auto_outliers(sessions: list[dict]) -> None:
    """
    Marque automatiquement les tours aberrants, sans écraser les choix manuels.
    L'objectif est d'exclure les tours beaucoup trop longs des moyennes.
    """
    candidates = [
        s for s in sessions
        if s.get("lap_time_sec", 0) > 0
        and s.get("fuel_used", 0) > 0
        and s.get("status") in ("valid", "auto_outlier")
        and not s.get("status_locked", False)
    ]
    if len(candidates) < 4:
        for s in candidates:
            if s.get("status") == "auto_outlier":
                s["status"] = "valid"
                s.pop("excluded_reason", None)
        return

    times = sorted(s["lap_time_sec"] for s in candidates)
    fuels = sorted(s["fuel_used"] for s in candidates)

    def median(values):
        n = len(values)
        mid = n // 2
        return values[mid] if n % 2 else (values[mid - 1] + values[mid]) / 2

    med_time = median(times)
    med_fuel = median(fuels)

    # Seuil volontairement large : on exclut surtout les tours vraiment anormaux.
    time_limit = max(med_time + 10.0, med_time * 1.12)
    fuel_limit = max(med_fuel + 0.8, med_fuel * 1.25)

    for s in candidates:
        too_slow = s.get("lap_time_sec", 0) > time_limit
        too_fuel = s.get("fuel_used", 0) > fuel_limit
        if too_slow or too_fuel:
            s["status"] = "auto_outlier"
            reasons = []
            if too_slow:
                reasons.append("tour trop long")
            if too_fuel:
                reasons.append("conso aberrante")
            s["excluded_reason"] = ", ".join(reasons)
        else:
            s["status"] = "valid"
            s.pop("excluded_reason", None)


def _compute_session_stats(laps: list[dict]) -> dict:
    """Calcule les stats pour une liste de tours (une session)."""
    counted = [
        l for l in laps
        if l.get("lap_time_sec", 0) > 0
        and l.get("fuel_used", 0) > 0
        and l.get("status", "valid") in INCLUDED_STATUSES
    ]
    
    excluded = [
        l for l in laps
        if l.get("lap_time_sec", 0) > 0
        and l.get("fuel_used", 0) > 0
        and l.get("status", "valid") not in INCLUDED_STATUSES
    ]
    
    if counted:
        times = [l["lap_time_sec"] for l in counted]
        fuels = [l["fuel_used"] for l in counted]
        return {
            "total_laps": len(counted),
            "total_laps_all": len(counted) + len(excluded),
            "excluded_laps": len(excluded),
            "best_lap_sec": round(min(times), 3),
            "avg_lap_time_sec": round(sum(times) / len(times), 3),
            "avg_fuel_per_lap": round(sum(fuels) / len(fuels), 3),
            "min_fuel_per_lap": round(min(fuels), 3),
            "max_fuel_per_lap": round(max(fuels), 3),
        }
    else:
        return {
            "total_laps": 0,
            "total_laps_all": len(excluded),
            "excluded_laps": len(excluded),
        }



def _recompute_stats(data: dict) -> dict:
    sessions = data.setdefault("sessions", [])
    for i, lap in enumerate(sessions):
        _normalize_lap(lap, i)

    _detect_auto_outliers(sessions)

    counted = [
        s for s in sessions
        if s.get("lap_time_sec", 0) > 0
        and s.get("fuel_used", 0) > 0
        and s.get("status", "valid") in INCLUDED_STATUSES
    ]

    excluded = [
        s for s in sessions
        if s.get("lap_time_sec", 0) > 0
        and s.get("fuel_used", 0) > 0
        and s.get("status", "valid") not in INCLUDED_STATUSES
    ]

    if counted:
        times = [s["lap_time_sec"] for s in counted]
        fuels = [s["fuel_used"] for s in counted]
        data["stats"] = {
            "total_laps": len(counted),
            "total_laps_all": len(counted) + len(excluded),
            "excluded_laps": len(excluded),
            "best_lap_sec": round(min(times), 3),
            "avg_lap_time_sec": round(sum(times) / len(times), 3),
            "avg_fuel_per_lap": round(sum(fuels) / len(fuels), 3),
            "min_fuel_per_lap": round(min(fuels), 3),
            "max_fuel_per_lap": round(max(fuels), 3),
            "last_updated": datetime.now().isoformat(),
        }
    else:
        data["stats"] = {
            "total_laps": 0,
            "total_laps_all": len(excluded),
            "excluded_laps": len(excluded),
            "last_updated": datetime.now().isoformat(),
        }
    return data["stats"]



def _session_day(lap: dict) -> str:
    ts = lap.get("timestamp") or datetime.now().isoformat()
    return str(ts)[:10]


def _session_kind(session_type: str) -> str:
    st = (session_type or "Unknown").lower()
    if st.startswith("qual"):
        return "qualifying"
    if st.startswith("race"):
        return "race"
    if st.startswith("prac"):
        return "practice"
    return "session"


def _session_display_name(session_type: str, index: int) -> str:
    kind = _session_kind(session_type)
    if kind == "race":
        return f"Course {index}"
    if kind == "qualifying":
        return f"Qualifications {index}"
    if kind == "practice":
        return f"Essais libres {index}"
    return f"Session {index}"



def _lap_number(lap: dict) -> int:
    try:
        return int(lap.get("lap_number", 0))
    except Exception:
        return 0


def _assign_session_metadata(data: dict, lap: dict, force_new_session: bool = False) -> None:
    sessions = data.setdefault("sessions", [])
    stype = lap.get("session_type") or "Unknown"
    day = _session_day(lap)
    kind = _session_kind(stype)

    last = sessions[-1] if sessions else None
    if last and not force_new_session:
        if (
            last.get("session_type") == stype
            and (last.get("session_day") or _session_day(last)) == day
            and last.get("session_id")
            and _lap_number(lap) > _lap_number(last)
        ):
            lap["session_id"] = last["session_id"]
            lap["session_name"] = last.get("session_name")
            lap["session_index"] = last.get("session_index", 1)
            lap["session_day"] = day
            return

    existing = []
    prefix = f"{kind}_{day}_"
    for old in sessions:
        if (old.get("session_day") or _session_day(old)) == day and _session_kind(old.get("session_type")) == kind:
            sid = str(old.get("session_id", ""))
            if sid.startswith(prefix):
                try:
                    existing.append(int(sid.split("_")[-1]))
                except Exception:
                    pass
    index = max(existing) + 1 if existing else 1
    lap["session_id"] = f"{kind}_{day}_{index}"
    lap["session_name"] = _session_display_name(stype, index)
    lap["session_index"] = index
    lap["session_day"] = day



def _split_raw_session_groups(sessions: list[dict]) -> list[list[dict]]:
    """
    Découpe les tours en sessions logiques.
    On garde les anciennes limites si session_id existe, sinon on découpe si :
    - le type change,
    - la date change,
    - le compteur de tours repart à 1 ou baisse.
    """
    groups = []
    cur = []
    last = None

    for lap in sessions:
        if not cur:
            cur = [lap]
        else:
            same_existing_session = (
                lap.get("session_id")
                and last
                and last.get("session_id")
                and lap.get("session_id") == last.get("session_id")
            )
            should_split = False
            if not same_existing_session:
                should_split = (
                    lap.get("session_type") != last.get("session_type")
                    or _session_day(lap) != _session_day(last)
                    or _lap_number(lap) <= _lap_number(last)
                )

            if should_split:
                groups.append(cur)
                cur = [lap]
            else:
                cur.append(lap)
        last = lap

    if cur:
        groups.append(cur)
    return groups


def _renumber_sessions_by_day(data: dict) -> None:
    """
    Renumérote toutes les sessions par JOUR et par TYPE.
    Exemple :
    29/05 : Course 1, Qualifications 1, Essais libres 1...
    30/05 : Course 1, Qualifications 1...
    """
    sessions = data.setdefault("sessions", [])
    raw_groups = _split_raw_session_groups(sessions)
    counters = {}

    for group in raw_groups:
        if not group:
            continue

        first = group[0]
        stype = first.get("session_type") or "Unknown"
        kind = _session_kind(stype)
        day = _session_day(first)
        key = (day, kind)
        counters[key] = counters.get(key, 0) + 1
        index = counters[key]

        session_id = f"{kind}_{day}_{index}"
        session_name = _session_display_name(stype, index)

        for lap in group:
            lap["session_day"] = day
            lap["session_id"] = session_id
            lap["session_name"] = session_name
            lap["session_index"] = index


def normalize_all_sessions(data: dict) -> None:
    sessions = data.setdefault("sessions", [])

    for i, lap in enumerate(sessions):
        _normalize_lap(lap, i)
        lap.setdefault("position", None)
        lap["session_day"] = _session_day(lap)
        lap["is_counted"] = (
            lap.get("lap_time_sec", 0) > 0
            and lap.get("fuel_used", 0) > 0
            and lap.get("status", "valid") in INCLUDED_STATUSES
        )

    # Très important : on renumérote même les anciennes données pour que
    # chaque journée reparte bien à Course 1 / Qualifications 1 / etc.
    _renumber_sessions_by_day(data)

    groups = {}
    for lap in sessions:
        sid = lap.get("session_id", "unknown")
        groups.setdefault(sid, {
            "session_id": sid,
            "session_name": lap.get("session_name", "Session"),
            "session_type": lap.get("session_type", "Unknown"),
            "session_index": lap.get("session_index", 0),
            "session_day": lap.get("session_day") or _session_day(lap),
            "start_time": lap.get("timestamp"),
            "end_time": lap.get("timestamp"),
            "position": lap.get("position"),
            "best_position": lap.get("position"),
            "laps": [],
        })
        groups[sid]["laps"].append(lap)
        groups[sid]["end_time"] = lap.get("timestamp") or groups[sid]["end_time"]

        pos = lap.get("position")
        if pos is not None:
            groups[sid]["position"] = pos
            best = groups[sid].get("best_position")
            if best is None or pos < best:
                groups[sid]["best_position"] = pos

    data["session_groups"] = []
    for g in groups.values():
        stats = _compute_session_stats(g["laps"])
        clean = dict(g)
        clean.pop("laps", None)
        clean["lap_count"] = len(g["laps"])
        clean["valid_laps"] = stats.get("total_laps", 0)
        clean["excluded_laps"] = stats.get("excluded_laps", 0)
        clean["stats"] = stats
        data["session_groups"].append(clean)

    data["session_groups"].sort(
        key=lambda g: (g.get("session_day", ""), g.get("start_time") or "", g.get("session_type", ""), g.get("session_index", 0))
    )


def save_session_data(data: dict) -> None:
    car = data.get("car", "Unknown")
    track = data.get("track", "Unknown")
    _recompute_stats(data)
    with open(get_data_file(car, track), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_lap(car: str, track: str, lap: dict, force_new_session: bool = False):
    data = load_session_data(car, track)
    lap.setdefault("timestamp", datetime.now().isoformat())
    lap.setdefault("session_type", "Unknown")
    lap.setdefault("status", "valid")
    lap.setdefault("status_locked", False)
    lap.setdefault("position", None)
    _normalize_lap(lap, len(data["sessions"]))
    _assign_session_metadata(data, lap, force_new_session=force_new_session)
    data["sessions"].append(lap)
    normalize_all_sessions(data)
    save_session_data(data)
    return data["stats"], lap



def update_lap_status(car: str, track: str, lap_id: str, status: str):
    if status not in LAP_STATUS:
        raise ValueError("Statut invalide")
    data = load_session_data(car, track)
    updated = None
    for lap in data.get("sessions", []):
        if str(lap.get("lap_id")) == str(lap_id):
            lap["status"] = status
            lap["status_locked"] = True
            lap["status_updated_at"] = datetime.now().isoformat()
            updated = lap
            break
    if updated is None:
        raise ValueError("Tour introuvable")
    save_session_data(data)
    return data, updated


def merge_sessions(car: str, track: str, session_id_keep: str, session_id_merge: str):
    """Fusionne session_id_merge dans session_id_keep."""
    data = load_session_data(car, track)
    sessions = data.get("sessions", [])
    target = next((l for l in sessions if l.get("session_id") == session_id_keep), None)
    if target is None:
        raise ValueError(f"Session '{session_id_keep}' introuvable")
    merged = 0
    for lap in sessions:
        if lap.get("session_id") == session_id_merge:
            lap["session_id"]    = session_id_keep
            lap["session_name"]  = target.get("session_name")
            lap["session_index"] = target.get("session_index")
            lap["session_day"]   = target.get("session_day")
            merged += 1
    if merged == 0:
        raise ValueError(f"Session '{session_id_merge}' introuvable ou déjà fusionnée")
    normalize_all_sessions(data)
    save_session_data(data)
    return data


def update_session_type(car: str, track: str, session_type: str):
    data = load_session_data(car, track)
    for lap in data.get("sessions", []):
        lap["session_type"] = session_type
    save_session_data(data)
    return data


def load_all_stats() -> list:
    """Charge tous les fichiers JSON et retourne les sessions groupées."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    result = []
    for fp in sorted(DATA_DIR.glob("*.json")):
        try:
            with open(fp, "r", encoding="utf-8") as f:
                d = json.load(f)
            car = d.get("car", "?")
            track = d.get("track", "?")
            d.setdefault("car", car)
            d.setdefault("track", track)
            d.setdefault("sessions", [])
            normalize_all_sessions(d)
            _recompute_stats(d)
            for group in d.get("session_groups", []):
                laps = [lap for lap in d.get("sessions", []) if lap.get("session_id") == group.get("session_id")]
                item = dict(group)
                item.update({"car": car, "track": track, "laps": laps})
                result.append(item)
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(d, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"  ⚠️  Impossible de charger {fp.name} : {e}")
    return result


# ── SERVEUR ──────────────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 8765


class ACCServer:
    def __init__(self):
        self.reader = ACCSharedMemoryReader() if SHM_AVAILABLE else None
        self.clients = set()

        self.current_car = None
        self.current_track = None
        self.last_laps = -1
        self.session_laps = []
        self.connected = False
        self.session_type_override = None
        self._force_new_session = False
        self._last_saved_lap_signature = None
        self._last_seen_lap_signature = None
        self._last_acc_status = "waiting" if self.reader else "unavailable"

        # Enregistrement robuste des tours :
        # ACC peut mettre à jour completed_laps avant iLastTime/fuelXLap.
        # On garde donc un tour "en attente" jusqu'à recevoir un chrono valide.
        self._pending_lap_number = None
        self._pending_lap_started_at = None
        self._last_fuel_remaining = None

    async def register(self, ws):
        self.clients.add(ws)
        print(f"  🔌  Interface HTML connectée ({len(self.clients)} client(s))")
        await self.send(ws, {"type": "all_stats", "data": load_all_stats()})
        await self.send(ws, self._acc_status_message())

    def _acc_status_message(self):
        if not self.reader:
            return {
                "type": "acc_status",
                "status": "unavailable",
                "detail": "Le lecteur de mémoire partagée ACC n'est pas chargé.",
            }
        if self.connected:
            return {"type": "acc_status", "status": "live"}
        if self.reader.is_connected():
            return {"type": "acc_status", "status": "connected"}
        detail = getattr(self.reader, "last_connection_error", None)
        return {
            "type": "acc_status",
            "status": "error" if detail else "waiting",
            "detail": detail or "En attente de la mémoire partagée d'Assetto Corsa Competizione.",
        }

    def unregister(self, ws):
        self.clients.discard(ws)
        print(f"  🔌  Client déconnecté ({len(self.clients)} actif(s))")

    async def send(self, ws, payload):
        try:
            await ws.send(json.dumps(payload))
        except Exception:
            pass

    async def broadcast(self, payload):
        if not self.clients:
            return
        msg = json.dumps(payload)
        await asyncio.gather(*[ws.send(msg) for ws in list(self.clients)], return_exceptions=True)

    async def handle_message(self, ws, raw):
        try:
            msg = json.loads(raw)
        except Exception:
            return

        mtype = msg.get("type")

        if mtype == "get_stats":
            car = msg.get("car", "")
            track = msg.get("track", "")
            data = load_session_data(car, track)
            await self.send(ws, {
                "type": "stats",
                "car": car,
                "track": track,
                "stats": data.get("stats", {}),
                "sessions": data.get("sessions", []),
            })

        elif mtype == "save_lap":
            car = msg.get("car", "Unknown")
            track = msg.get("track", "Unknown")
            lap = msg.get("lap", {})
            if self.session_type_override:
                lap["session_type"] = self.session_type_override
            stats, saved_lap = save_lap(car, track, lap)
            await self.broadcast({"type": "lap_saved", "car": car, "track": track, "lap": saved_lap, "stats": stats})
            await self.broadcast({"type": "all_stats", "data": load_all_stats()})
            print(f"  💾  Tour sauvegardé : {car} @ {track}")

        elif mtype == "update_lap_status":
            try:
                car = msg.get("car", "")
                track = msg.get("track", "")
                lap_id = msg.get("lap_id", "")
                status = msg.get("status", "valid")
                data, updated = update_lap_status(car, track, lap_id, status)
                await self.broadcast({
                    "type": "lap_status_updated",
                    "car": car,
                    "track": track,
                    "lap": updated,
                    "stats": data.get("stats", {}),
                    "sessions": data.get("sessions", []),
                })
                await self.broadcast({"type": "all_stats", "data": load_all_stats()})
            except Exception as e:
                await self.send(ws, {"type": "error", "message": str(e)})

        elif mtype == "set_session_type":
            self.session_type_override = msg.get("session_type") or None
            if msg.get("force_new_session"):
                self._force_new_session = True
            await self.broadcast({"type": "session_type_override", "session_type": self.session_type_override})

        elif mtype == "update_session_type":
            try:
                car = msg.get("car", self.current_car or "")
                track = msg.get("track", self.current_track or "")
                session_type = msg.get("session_type", "Race")
                self.session_type_override = session_type
                if car and track:
                    data = update_session_type(car, track, session_type)
                    await self.broadcast({
                        "type": "stats",
                        "car": car,
                        "track": track,
                        "stats": data.get("stats", {}),
                        "sessions": data.get("sessions", []),
                    })
                    await self.broadcast({"type": "all_stats", "data": load_all_stats()})
            except Exception as e:
                await self.send(ws, {"type": "error", "message": str(e)})

        elif mtype == "merge_sessions":
            try:
                car           = msg.get("car",            self.current_car   or "")
                track         = msg.get("track",          self.current_track or "")
                session_keep  = msg.get("session_keep",  "")
                session_merge = msg.get("session_merge", "")
                data = merge_sessions(car, track, session_keep, session_merge)
                await self.broadcast({
                    "type":     "stats",
                    "car":      car,
                    "track":    track,
                    "stats":    data.get("stats", {}),
                    "sessions": data.get("sessions", []),
                })
                await self.broadcast({"type": "all_stats", "data": load_all_stats()})
                print(f"  🔗  Sessions fusionnées : {session_merge} → {session_keep}")
            except Exception as e:
                await self.send(ws, {"type": "error", "message": str(e)})

        elif mtype == "calculate":
            result = self.compute_strategy(msg)
            await self.send(ws, {"type": "strategy_result", "data": result})

    def compute_strategy(self, params) -> dict:
        duration = float(params.get("race_duration_min", 60))
        lap_time_sec = float(params.get("lap_time_sec", 100))
        fuel_per_lap = float(params.get("fuel_per_lap", 2.8))
        tank = float(params.get("tank_capacity", 120))
        formation = bool(params.get("formation_lap", False))
        extra = bool(params.get("extra_lap", False))

        race_sec = duration * 60
        est_laps = math.ceil(race_sec / lap_time_sec)
        margin = 1 + (1 if extra else 0) + (1 if formation else 0)
        total_laps = est_laps + margin
        fuel_raw = total_laps * fuel_per_lap
        fuel_load = min(math.ceil(fuel_raw), int(tank))

        max_laps = tank / fuel_per_lap
        pit_stops = max(0, math.ceil(est_laps / max_laps) - 1)
        pit_wins = []
        if pit_stops > 0:
            lps = est_laps / (pit_stops + 1)
            for i in range(1, pit_stops + 1):
                pit_wins.append(round(lps * i))

        return {
            "fuel_to_load": fuel_load,
            "fuel_raw": round(fuel_raw, 2),
            "estimated_laps": est_laps,
            "pit_stops": pit_stops,
            "pit_windows": pit_wins,
            "lap_time_sec": lap_time_sec,
            "fuel_per_lap": fuel_per_lap,
            "tank_capacity": tank,
            "race_duration_min": duration,
        }

    async def acc_loop(self):
        print("  🔄  Boucle ACC démarrée — en attente du jeu...")
        while True:
            try:
                await self._tick()
            except Exception as e:
                print(f"  ⚠️  Erreur tick : {e}")
            await asyncio.sleep(0.5)

    async def _tick(self):
        if not self.reader:
            return

        if not self.reader.is_connected():
            ok = self.reader.connect()
            if ok:
                print("  🟢  ACC détecté !")
                await self.broadcast({"type": "acc_status", "status": "connected"})
                self._last_acc_status = "connected"
            else:
                status = self._acc_status_message()
                if status["status"] != self._last_acc_status:
                    await self.broadcast(status)
                    self._last_acc_status = status["status"]
            return

        snap = self.reader.get_snapshot()
        if snap is None:
            self.connected = False
            status = self._acc_status_message()
            if status["status"] != self._last_acc_status:
                await self.broadcast(status)
                self._last_acc_status = status["status"]
            return

        status = snap.get("status", "OFF")

        if status == "Live":
            if not self.connected:
                self.connected = True
                await self.broadcast({"type": "acc_status", "status": "live"})
                self._last_acc_status = "live"

            car = snap["car"]
            track = snap["track"]
            session_type = self.session_type_override or snap.get("session_type", "Unknown")

            if car != self.current_car or track != self.current_track:
                self.current_car = car
                self.current_track = track
                self.last_laps = snap["completed_laps"]
                self.session_laps = []
                session_type = self.session_type_override or snap.get("session_type", "Unknown")

                hist = load_session_data(car, track)
                await self.broadcast({
                    "type": "new_session",
                    "car": car,
                    "track": track,
                    "session": session_type,
                    "tank": snap["tank_capacity"],
                    "hist_stats": hist.get("stats", {}),
                    "sessions": hist.get("sessions", []),
                })
                print(f"  🚗  {car} @ {track} — {session_type}")

            snap["session_type"] = session_type
            await self.broadcast({"type": "telemetry", "data": snap})

            laps = int(snap.get("completed_laps", 0) or 0)
            lap_time = float(snap.get("last_lap_sec", 0) or 0)
            fuel_used = float(snap.get("fuel_per_lap", 0) or 0)
            fuel_remaining = float(snap.get("fuel_remaining", 0) or 0)

            def _lap_time_ok(value: float) -> bool:
                return 20 < value < 3600

            # 1) Méthode normale : le compteur ACC augmente.
            # On ne sauvegarde pas forcément tout de suite, car ACC peut mettre
            # iLastTime/fuelXLap à jour quelques ticks après completed_laps.
            if laps > self.last_laps and self.last_laps >= 0:
                self._pending_lap_number = laps
                self._pending_lap_started_at = datetime.now().isoformat()
                print(f"  🟡  Nouveau tour détecté par compteur ACC : {laps}, attente chrono valide...")

            # 2) Fallback : si le chrono du dernier tour change, même sans compteur.
            lap_signature = (
                laps,
                round(lap_time, 3),
                session_type,
                car,
                track,
            )
            if (
                _lap_time_ok(lap_time)
                and lap_signature != self._last_seen_lap_signature
                and lap_signature != self._last_saved_lap_signature
            ):
                self._pending_lap_number = laps if laps > 0 else len(self.session_laps) + 1
                self._pending_lap_started_at = datetime.now().isoformat()

            # Si on a un tour en attente et un chrono valide, on sauvegarde.
            if self._pending_lap_number is not None and _lap_time_ok(lap_time):
                lap_no = int(self._pending_lap_number)

                # Si ACC ne donne pas fuelXLap, on tente une estimation avec la variation du carburant restant.
                if fuel_used <= 0 and self._last_fuel_remaining is not None:
                    delta_fuel = float(self._last_fuel_remaining) - fuel_remaining
                    if 0 < delta_fuel < 15:
                        fuel_used = delta_fuel

                # On accepte quand même le tour si la conso est absente :
                # il apparaîtra dans l'historique, mais ne comptera pas dans les moyennes carburant.
                if fuel_used < 0:
                    fuel_used = 0

                save_signature = (
                    lap_no,
                    round(lap_time, 3),
                    round(fuel_used, 3),
                    session_type,
                    car,
                    track,
                )

                if save_signature != self._last_saved_lap_signature:
                    lap_data = {
                        "lap_number": lap_no,
                        "lap_time_sec": round(lap_time, 3),
                        "fuel_used": round(fuel_used, 3),
                        "fuel_remaining": fuel_remaining,
                        "session_type": session_type,
                        "tyre_compound": snap["tyre_compound"],
                        "air_temp": snap["air_temp"],
                        "road_temp": snap["road_temp"],
                        "position": snap.get("position"),
                        "status": "valid",
                        "status_locked": False,
                    }
                    stats, saved_lap = save_lap(car, track, lap_data, force_new_session=self._force_new_session)
                    self._force_new_session = False
                    self._last_saved_lap_signature = save_signature
                    self._last_seen_lap_signature = lap_signature
                    self._pending_lap_number = None
                    self._pending_lap_started_at = None
                    self.session_laps.append(saved_lap)

                    await self.broadcast({
                        "type": "new_lap",
                        "lap": saved_lap,
                        "stats": stats,
                        "session_laps": self.session_laps,
                    })
                    await self.broadcast({"type": "all_stats", "data": load_all_stats()})
                    print(f"  ✅  Tour {lap_no} enregistré | {self._fmt(lap_time)} | {fuel_used:.2f} L | {LAP_STATUS.get(saved_lap.get('status'), 'Valide')}")

            self._last_fuel_remaining = fuel_remaining if fuel_remaining > 0 else self._last_fuel_remaining
            self.last_laps = max(self.last_laps, laps)

        else:
            if self.connected:
                self.connected = False
                self.current_car = None
                self.current_track = None
                self.session_laps = []
                self.session_type_override = None
                self._last_saved_lap_signature = None
                self._last_seen_lap_signature = None
                self._pending_lap_number = None
                self._pending_lap_started_at = None
                self._last_fuel_remaining = None
                status_message = self._acc_status_message()
                await self.broadcast(status_message)
                self._last_acc_status = status_message["status"]

    def _fmt(self, sec):
        m = int(sec // 60)
        s = sec % 60
        return f"{m}:{s:06.3f}"

    async def ws_handler(self, ws):
        await self.register(ws)
        try:
            async for message in ws:
                await self.handle_message(ws, message)
        except websockets.exceptions.ConnectionClosedOK:
            pass
        except websockets.exceptions.ConnectionClosedError:
            pass
        finally:
            self.unregister(ws)

    async def run(self):
        _seed_dev_data()
        print("\n" + "=" * 55)
        print("  🏁  ACC FUEL STRATEGY — Serveur")
        print("=" * 55)
        print(f"  WebSocket : ws://{HOST}:{PORT}")
        print("  Mode      : serveur local de ACC Pit Wall")
        print(f"  Données   : {DATA_DIR}")
        print("  Lancez launcher.py pour ouvrir l'interface native")
        print("  Ctrl+C pour arrêter")
        print("=" * 55 + "\n")

        acc_task = asyncio.create_task(self.acc_loop())
        async with websockets.serve(self.ws_handler, HOST, PORT):
            await acc_task


if __name__ == "__main__":
    server = ACCServer()
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\n  ⛔  Serveur arrêté.\n")
