# -*- coding: utf-8 -*-
"""
ACC Shared Memory Reader
Lit les données télémétriques d'Assetto Corsa Competizione en temps réel
via la mémoire partagée Windows (mmap).

Nécessite : pip install mmap (inclus dans Python standard)
Fonctionne UNIQUEMENT sous Windows quand ACC est en cours d'exécution.
"""

import struct
import ctypes
import sys
import os
from ctypes import wintypes

# ──────────────────────────────────────────────
# STRUCTURES DE MÉMOIRE PARTAGÉE ACC
# Source : SDK ACC officiel Kunos
# ──────────────────────────────────────────────

class SPageFilePhysics(ctypes.Structure):
    """Données physiques en temps réel (mises à jour chaque frame)."""
    _pack_ = 4
    _fields_ = [
        ("packetId",            ctypes.c_int),
        ("gas",                 ctypes.c_float),
        ("brake",               ctypes.c_float),
        ("fuel",                ctypes.c_float),      # Carburant restant (L)
        ("gear",                ctypes.c_int),
        ("rpms",                ctypes.c_int),
        ("steerAngle",          ctypes.c_float),
        ("speedKmh",            ctypes.c_float),
        ("velocity",            ctypes.c_float * 3),
        ("accG",                ctypes.c_float * 3),
        ("wheelSlip",           ctypes.c_float * 4),
        ("wheelLoad",           ctypes.c_float * 4),
        ("wheelsPressure",      ctypes.c_float * 4),
        ("wheelAngularSpeed",   ctypes.c_float * 4),
        ("tyreWear",            ctypes.c_float * 4),
        ("tyreDirtyLevel",      ctypes.c_float * 4),
        ("tyreCoreTemperature", ctypes.c_float * 4),
        ("camberRAD",           ctypes.c_float * 4),
        ("suspensionTravel",    ctypes.c_float * 4),
        ("drs",                 ctypes.c_float),
        ("tc",                  ctypes.c_float),
        ("heading",             ctypes.c_float),
        ("pitch",               ctypes.c_float),
        ("roll",                ctypes.c_float),
        ("cgHeight",            ctypes.c_float),
        ("carDamage",           ctypes.c_float * 5),
        ("numberOfTyresOut",    ctypes.c_int),
        ("pitLimiterOn",        ctypes.c_int),
        ("abs",                 ctypes.c_float),
        ("kersCharge",          ctypes.c_float),
        ("kersInput",           ctypes.c_float),
        ("autoShifterOn",       ctypes.c_int),
        ("rideHeight",          ctypes.c_float * 2),
        ("turboBoost",          ctypes.c_float),
        ("ballast",             ctypes.c_float),
        ("airDensity",          ctypes.c_float),
        ("airTemp",             ctypes.c_float),
        ("roadTemp",            ctypes.c_float),
        ("localAngularVel",     ctypes.c_float * 3),
        ("finalFF",             ctypes.c_float),
        ("performanceMeter",    ctypes.c_float),
        ("engineBrake",         ctypes.c_int),
        ("ersRecoveryLevel",    ctypes.c_int),
        ("ersPowerLevel",       ctypes.c_int),
        ("ersHeatCharging",     ctypes.c_int),
        ("ersIsCharging",       ctypes.c_int),
        ("kersCurrentKJ",       ctypes.c_float),
        ("drsAvailable",        ctypes.c_int),
        ("drsEnabled",          ctypes.c_int),
        ("brakeTemp",           ctypes.c_float * 4),
        ("clutch",              ctypes.c_float),
        ("tyreTempI",           ctypes.c_float * 4),
        ("tyreTempM",           ctypes.c_float * 4),
        ("tyreTempO",           ctypes.c_float * 4),
        ("isAIControlled",      ctypes.c_int),
        ("tyreContactPoint",    ctypes.c_float * 4 * 3),
        ("tyreContactNormal",   ctypes.c_float * 4 * 3),
        ("tyreContactHeading",  ctypes.c_float * 4 * 3),
        ("brakeBias",           ctypes.c_float),
        ("localVelocity",       ctypes.c_float * 3),
        ("P2PActivations",      ctypes.c_int),
        ("P2PStatus",           ctypes.c_int),
        ("currentMaxRpm",       ctypes.c_int),
        ("mz",                  ctypes.c_float * 4),
        ("fx",                  ctypes.c_float * 4),
        ("fy",                  ctypes.c_float * 4),
        ("slipRatio",           ctypes.c_float * 4),
        ("slipAngle",           ctypes.c_float * 4),
        ("tcinAction",          ctypes.c_int),
        ("absInAction",         ctypes.c_int),
        ("suspensionDamage",    ctypes.c_float * 4),
        ("tyreTemp",            ctypes.c_float * 4),
        ("waterTemp",           ctypes.c_float),
        ("brakePressure",       ctypes.c_float * 4),
        ("frontBrakeCompound",  ctypes.c_int),
        ("rearBrakeCompound",   ctypes.c_int),
        ("padLife",             ctypes.c_float * 4),
        ("discLife",            ctypes.c_float * 4),
        ("ignitionOn",          ctypes.c_int),
        ("starterEngineOn",     ctypes.c_int),
        ("isEngineRunning",     ctypes.c_int),
        ("kerbVibration",       ctypes.c_float),
        ("slipVibrations",      ctypes.c_float),
        ("gVibrations",         ctypes.c_float),
        ("absVibrations",       ctypes.c_float),
    ]


class SPageFileGraphic(ctypes.Structure):
    """Données graphiques / état de la session."""
    _pack_ = 4
    _fields_ = [
        ("packetId",             ctypes.c_int),
        ("status",               ctypes.c_int),    # 0=OFF 1=REPLAY 2=LIVE 3=PAUSE
        ("session",              ctypes.c_int),    # 0=Unknown 1=Practice 2=Qualify 3=Race 4=Hotlap 5=TimeAttack 6=Drift 7=Drag
        ("currentTime",          ctypes.c_wchar * 15),
        ("lastTime",             ctypes.c_wchar * 15),
        ("bestTime",             ctypes.c_wchar * 15),
        ("split",                ctypes.c_wchar * 15),
        ("completedLaps",        ctypes.c_int),
        ("position",             ctypes.c_int),
        ("iCurrentTime",         ctypes.c_int),    # Temps tour actuel (ms)
        ("iLastTime",            ctypes.c_int),    # Temps dernier tour (ms)
        ("iBestTime",            ctypes.c_int),    # Meilleur tour (ms)
        ("sessionTimeLeft",      ctypes.c_float),  # Temps restant session (ms)
        ("distanceTraveled",     ctypes.c_float),
        ("isInPit",              ctypes.c_int),
        ("currentSectorIndex",   ctypes.c_int),
        ("lastSectorTime",       ctypes.c_int),
        ("numberOfLaps",         ctypes.c_int),
        ("tyreCompound",         ctypes.c_wchar * 33),
        ("replayTimeMultiplier", ctypes.c_float),
        ("normalizedCarPosition",ctypes.c_float),
        ("activeCars",           ctypes.c_int),
        ("carCoordinates",       ctypes.c_float * 60 * 3),
        ("carID",                ctypes.c_int * 60),
        ("playerCarID",          ctypes.c_int),
        ("penaltyTime",          ctypes.c_float),
        ("flag",                 ctypes.c_int),
        ("penalty",              ctypes.c_int),
        ("idealLineOn",          ctypes.c_int),
        ("isInPitLane",          ctypes.c_int),
        ("surfaceGrip",          ctypes.c_float),
        ("mandatoryPitDone",     ctypes.c_int),
        ("windSpeed",            ctypes.c_float),
        ("windDirection",        ctypes.c_float),
        ("isSetupMenuVisible",   ctypes.c_int),
        ("mainDisplayIndex",     ctypes.c_int),
        ("secondaryDisplayIndex",ctypes.c_int),
        ("TC",                   ctypes.c_int),
        ("TCCut",                ctypes.c_int),
        ("EngineMap",            ctypes.c_int),
        ("ABS",                  ctypes.c_int),
        ("fuelXLap",             ctypes.c_float),  # ← Consommation prévue L/tour
        ("rainLights",           ctypes.c_int),
        ("flashingLights",       ctypes.c_int),
        ("lightsStage",          ctypes.c_int),
        ("exhaustTemperature",   ctypes.c_float),
        ("wiperLV",              ctypes.c_int),
        ("driverStintTotalTimeLeft", ctypes.c_int),
        ("driverStintTimeLeft",  ctypes.c_int),
        ("rainTyres",            ctypes.c_int),
    ]


class SPageFileStatic(ctypes.Structure):
    """Données statiques (voiture, circuit, config)."""
    _pack_ = 4
    _fields_ = [
        ("smVersion",            ctypes.c_wchar * 15),
        ("acVersion",            ctypes.c_wchar * 15),
        ("numberOfSessions",     ctypes.c_int),
        ("numCars",              ctypes.c_int),
        ("carModel",             ctypes.c_wchar * 33),   # ← Modèle voiture
        ("track",                ctypes.c_wchar * 33),   # ← Circuit
        ("playerName",           ctypes.c_wchar * 33),
        ("playerSurname",        ctypes.c_wchar * 33),
        ("playerNick",           ctypes.c_wchar * 33),
        ("sectorCount",          ctypes.c_int),
        ("maxTorque",            ctypes.c_float),
        ("maxPower",             ctypes.c_float),
        ("maxRpm",               ctypes.c_int),
        ("maxFuel",              ctypes.c_float),        # ← Capacité réservoir
        ("suspensionMaxTravel",  ctypes.c_float * 4),
        ("tyreRadius",           ctypes.c_float * 4),
        ("maxTurboBoost",        ctypes.c_float),
        ("deprecated_1",         ctypes.c_float),
        ("deprecated_2",         ctypes.c_float),
        ("penaltiesEnabled",     ctypes.c_int),
        ("aidFuelRate",          ctypes.c_float),
        ("aidTireRate",          ctypes.c_float),
        ("aidMechanicalDamage",  ctypes.c_float),
        ("aidAllowTyreBlankets", ctypes.c_int),
        ("aidStability",         ctypes.c_float),
        ("aidAutoClutch",        ctypes.c_int),
        ("aidAutoBlip",          ctypes.c_int),
        ("hasDRS",               ctypes.c_int),
        ("hasERS",               ctypes.c_int),
        ("hasKERS",              ctypes.c_int),
        ("kersMaxJ",             ctypes.c_float),
        ("engineBrakeSettingsCount", ctypes.c_int),
        ("ersPowerControllerCount",  ctypes.c_int),
        ("trackSPlineLength",    ctypes.c_float),
        ("trackConfiguration",   ctypes.c_wchar * 33),
        ("ersMaxJ",              ctypes.c_float),
        ("isTimedRace",          ctypes.c_int),
        ("hasExtraLap",          ctypes.c_int),
        ("carSkin",              ctypes.c_wchar * 33),
        ("reversedGridPositions",ctypes.c_int),
        ("PitWindowStart",       ctypes.c_int),
        ("PitWindowEnd",         ctypes.c_int),
        ("isOnline",             ctypes.c_int),
        ("dryTyresName",         ctypes.c_wchar * 33),
        ("wetTyresName",         ctypes.c_wchar * 33),
    ]


# ──────────────────────────────────────────────
# LECTEUR SHARED MEMORY
# ──────────────────────────────────────────────

class ACCSharedMemoryReader:
    """
    Lit les données ACC via la mémoire partagée Windows.
    Fonctionne uniquement quand ACC tourne sur le même PC.
    """

    SHM_PHYSICS  = "Local\\acpmf_physics"
    SHM_GRAPHICS = "Local\\acpmf_graphics"
    SHM_STATIC   = "Local\\acpmf_static"

    def __init__(self):
        self._physics_mm  = None
        self._graphics_mm = None
        self._static_mm   = None
        self._connected   = False

    def connect(self) -> bool:
        """Tente de se connecter à la mémoire partagée d'ACC."""
        if sys.platform != "win32":
            print("[!] La mémoire partagée ACC est uniquement disponible sous Windows.")
            return False
        try:
            import mmap
            self._physics_mm  = mmap.mmap(-1, ctypes.sizeof(SPageFilePhysics),
                                           self.SHM_PHYSICS,  access=mmap.ACCESS_READ)
            self._graphics_mm = mmap.mmap(-1, ctypes.sizeof(SPageFileGraphic),
                                           self.SHM_GRAPHICS, access=mmap.ACCESS_READ)
            self._static_mm   = mmap.mmap(-1, ctypes.sizeof(SPageFileStatic),
                                           self.SHM_STATIC,   access=mmap.ACCESS_READ)
            self._connected = True
            return True
        except Exception as e:
            print(f"[!] Impossible de se connecter à ACC : {e}")
            print("    -> Assurez-vous qu'ACC est lancé et qu'une session est active.")
            self._connected = False
            return False

    def disconnect(self):
        for mm in [self._physics_mm, self._graphics_mm, self._static_mm]:
            if mm:
                try:
                    mm.close()
                except:
                    pass
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def _read_struct(self, mm, struct_type):
        if not mm:
            return None
        mm.seek(0)
        data = mm.read(ctypes.sizeof(struct_type))
        return struct_type.from_buffer_copy(data)

    def get_physics(self) -> SPageFilePhysics | None:
        return self._read_struct(self._physics_mm, SPageFilePhysics)

    def get_graphics(self) -> SPageFileGraphic | None:
        return self._read_struct(self._graphics_mm, SPageFileGraphic)

    def get_static(self) -> SPageFileStatic | None:
        return self._read_struct(self._static_mm, SPageFileStatic)

    def get_snapshot(self) -> dict | None:
        """Retourne un snapshot complet des données ACC."""
        if not self._connected:
            return None
        try:
            phys  = self.get_physics()
            graph = self.get_graphics()
            stat  = self.get_static()
            if not phys or not graph or not stat:
                return None

            # Mapping corrigé pour ACC :
            # 0 = Practice, 1 = Qualifying, 2 = Race.
            # L'ancien mapping décalait tout d'un cran : une qualif pouvait apparaître en Practice.
            session_names = {
                0: "Practice", 1: "Qualifying", 2: "Race",
                3: "Hotlap", 4: "TimeAttack", 5: "Unknown"
            }
            status_names = {0: "OFF", 1: "Replay", 2: "Live", 3: "Pause"}

            def _clean_lap_ms(value):
                try:
                    value = int(value)
                except Exception:
                    return 0
                # Valeurs invalides fréquentes : 2147483647 ms / -1 / 0.
                # On garde seulement des temps de tour crédibles.
                if value <= 0 or value >= 3600 * 1000:
                    return 0
                return value

            last_lap_ms = _clean_lap_ms(graph.iLastTime)
            best_lap_ms = _clean_lap_ms(graph.iBestTime)

            def _r(value, nd=2):
                try:
                    return round(float(value), nd)
                except Exception:
                    return 0.0

            def _arr(values, nd=2):
                return [_r(v, nd) for v in values]

            return {
                # Identification
                "car":               stat.carModel.strip() or "Unknown",
                "track":             stat.track.strip() or "Unknown",
                "player":            f"{stat.playerName.strip()} {stat.playerSurname.strip()}".strip(),
                "session_type":      session_names.get(graph.session, "Unknown"),
                "status":            status_names.get(graph.status, "Unknown"),
                # Tour
                "completed_laps":    graph.completedLaps,
                "current_lap_ms":    graph.iCurrentTime,
                "last_lap_ms":       last_lap_ms,
                "best_lap_ms":       best_lap_ms,
                "last_lap_sec":      last_lap_ms / 1000.0 if last_lap_ms > 0 else 0,
                "best_lap_sec":      best_lap_ms / 1000.0 if best_lap_ms > 0 else 0,
                # Carburant
                "fuel_remaining":    round(phys.fuel, 2),
                "fuel_per_lap":      round(graph.fuelXLap, 3),
                "tank_capacity":     round(stat.maxFuel, 1),
                # Session
                "session_time_left_sec": round(graph.sessionTimeLeft / 1000.0, 1) if graph.sessionTimeLeft > 0 else 0,
                "position":          graph.position,
                "is_in_pit":         bool(graph.isInPit or graph.isInPitLane),
                "completed_laps_total": graph.numberOfLaps,
                "current_sector_index": graph.currentSectorIndex,
                "last_sector_time_ms": int(graph.lastSectorTime),
                "normalized_car_position": _r(graph.normalizedCarPosition, 4),
                "active_cars": int(graph.activeCars),
                "flag": int(graph.flag),
                "penalty": int(graph.penalty),
                "penalty_time_sec": _r(graph.penaltyTime, 2),
                "mandatory_pit_done": bool(graph.mandatoryPitDone),
                "driver_stint_total_time_left_sec": int(graph.driverStintTotalTimeLeft / 1000) if graph.driverStintTotalTimeLeft > 0 else 0,
                "driver_stint_time_left_sec": int(graph.driverStintTimeLeft / 1000) if graph.driverStintTimeLeft > 0 else 0,
                # Conditions
                "speed_kmh":         round(phys.speedKmh, 1),
                "air_temp":          round(phys.airTemp, 1),
                "road_temp":         round(phys.roadTemp, 1),
                "tyre_compound":     graph.tyreCompound.strip(),
                "wind_speed":        _r(graph.windSpeed, 2),
                "wind_direction":    _r(graph.windDirection, 1),
                "surface_grip":      _r(graph.surfaceGrip, 3),

                # Inputs / dynamique
                "throttle":          _r(phys.gas, 3),
                "brake":             _r(phys.brake, 3),
                "clutch":            _r(phys.clutch, 3),
                "steer_angle_deg":   _r(phys.steerAngle, 2),
                "gear":              int(phys.gear),
                "rpm":               int(phys.rpms),
                "current_max_rpm":   int(phys.currentMaxRpm),
                "is_engine_running": bool(phys.isEngineRunning),
                "pit_limiter_on":    bool(phys.pitLimiterOn),
                "abs_level":         _r(phys.abs, 2),
                "tc_level":          _r(phys.tc, 2),
                "tc_in_action":      bool(phys.tcinAction),
                "abs_in_action":     bool(phys.absInAction),
                "engine_brake":      int(phys.engineBrake),
                "brake_bias":        _r(phys.brakeBias, 2),
                "g_force":           {"x": _r(phys.accG[0], 3), "y": _r(phys.accG[1], 3), "z": _r(phys.accG[2], 3)},
                "velocity":          {"x": _r(phys.velocity[0], 3), "y": _r(phys.velocity[1], 3), "z": _r(phys.velocity[2], 3)},
                "local_velocity":    {"x": _r(phys.localVelocity[0], 3), "y": _r(phys.localVelocity[1], 3), "z": _r(phys.localVelocity[2], 3)},
                "orientation":       {"heading": _r(phys.heading, 3), "pitch": _r(phys.pitch, 3), "roll": _r(phys.roll, 3)},

                # Pneus / freins / suspension
                "wheel_slip":        _arr(phys.wheelSlip, 3),
                "wheel_load":        _arr(phys.wheelLoad, 1),
                "wheels_pressure":   _arr(phys.wheelsPressure, 2),
                "wheel_speed":       _arr(phys.wheelAngularSpeed, 2),
                "tyre_wear":         _arr(phys.tyreWear, 3),
                "tyre_dirty_level":  _arr(phys.tyreDirtyLevel, 3),
                "tyre_core_temp":    _arr(phys.tyreCoreTemperature, 1),
                "tyre_temp_i":       _arr(phys.tyreTempI, 1),
                "tyre_temp_m":       _arr(phys.tyreTempM, 1),
                "tyre_temp_o":       _arr(phys.tyreTempO, 1),
                "tyre_temp":         _arr(phys.tyreTemp, 1),
                "camber_rad":        _arr(phys.camberRAD, 4),
                "slip_ratio":        _arr(phys.slipRatio, 3),
                "slip_angle":        _arr(phys.slipAngle, 3),
                "brake_temp":        _arr(phys.brakeTemp, 1),
                "brake_pressure":    _arr(phys.brakePressure, 1),
                "pad_life":          _arr(phys.padLife, 3),
                "disc_life":         _arr(phys.discLife, 3),
                "suspension_travel": _arr(phys.suspensionTravel, 3),
                "suspension_damage": _arr(phys.suspensionDamage, 3),
                "ride_height":       {"front": _r(phys.rideHeight[0], 3), "rear": _r(phys.rideHeight[1], 3)},

                # Moteur / dégâts / assistances
                "water_temp":        _r(phys.waterTemp, 1),
                "turbo_boost":       _r(phys.turboBoost, 3),
                "car_damage":        _arr(phys.carDamage, 3),
                "drs_available":     bool(phys.drsAvailable),
                "drs_enabled":       bool(phys.drsEnabled),
                "rain_lights":       bool(graph.rainLights),
                "flashing_lights":   bool(graph.flashingLights),
                "lights_stage":      int(graph.lightsStage),
                "wiper_level":       int(graph.wiperLV),
                "rain_tyres":        bool(graph.rainTyres),

                # Réglages voiture/session
                "setup_tc":          int(graph.TC),
                "setup_tccut":       int(graph.TCCut),
                "setup_abs":         int(graph.ABS),
                "setup_engine_map":  int(graph.EngineMap),
                "front_brake_compound": int(phys.frontBrakeCompound),
                "rear_brake_compound":  int(phys.rearBrakeCompound),
                "track_configuration": stat.trackConfiguration.strip(),
                "track_spline_length": _r(stat.trackSPlineLength, 1),
                "sector_count":      int(stat.sectorCount),
                "pit_window_start":  int(stat.PitWindowStart),
                "pit_window_end":    int(stat.PitWindowEnd),
                "is_timed_race":     bool(stat.isTimedRace),
                "has_extra_lap":     bool(stat.hasExtraLap),
            }
        except Exception as e:
            print(f"[!] Erreur lecture snapshot : {e}")
            return None
