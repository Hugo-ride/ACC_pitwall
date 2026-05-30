# 🏁 ACC Pit Wall

Outil de stratégie essence pour **Assetto Corsa Competizione**, avec une interface web en HTML et un serveur Python qui lit les données du jeu en temps réel.

---

## 📁 Structure des fichiers

```text
ACC_pitwall/
├── server.py                  # Serveur WebSocket à lancer
├── acc_pitwall.html     # Interface web à ouvrir dans le navigateur
├── fuel_calculator.py         # Calculs de stratégie + sauvegarde JSON
├── acc_shared_memory.py       # Lecture mémoire partagée ACC, Windows uniquement
├── acc_live_logger.py         # Ancien logger console / simulation, optionnel
└── README.md
```

---

## 🚀 Installation

### Prérequis

- Python 3.10 ou plus récent
- Windows 10/11 pour le mode temps réel avec ACC
- Assetto Corsa Competizione lancé avec une session active
- Le module Python `websockets`

Installation du module nécessaire :

```bash
pip install websockets
```

---

## ▶️ Lancement

### 1. Lancer le serveur Python

Dans le dossier du projet, lancer :

```bash
python server.py
```

Le serveur démarre sur :

```text
ws://localhost:8765
```

Il lit les données d'ACC toutes les 500 ms et les envoie à l'interface HTML.

---

### 2. Ouvrir l'interface

Ouvrir le fichier suivant dans un navigateur :

```text
acc_pitwall.html
```

L'interface se connecte automatiquement au serveur WebSocket.

---

## 📊 Ce que l'outil fait

### Interface web

- Affiche les données live d'ACC
- Détecte automatiquement la voiture et le circuit
- Affiche le carburant restant
- Affiche le dernier tour, le meilleur tour et la consommation moyenne
- Calcule la stratégie essence
- Affiche le nombre de tours estimés
- Affiche le carburant à charger
- Indique si un arrêt aux stands est nécessaire
- Affiche les fenêtres de pit stop

---

### Lecture en temps réel d'ACC

Le serveur lit les données d'ACC via la mémoire partagée Windows.

Données récupérées :

| Donnée | Source |
|---|---|
| Voiture | Mémoire partagée ACC |
| Circuit | Mémoire partagée ACC |
| Temps du dernier tour | Données graphiques ACC |
| Meilleur tour | Données graphiques ACC |
| Consommation par tour | Données graphiques ACC |
| Carburant restant | Données physiques ACC |
| Capacité du réservoir | Données statiques ACC |
| Temps restant de session | Données graphiques ACC |
| Position | Données graphiques ACC |
| Température air / piste | Données physiques ACC |

---

## 🧮 Calcul de stratégie

L'outil utilise :

- La durée de course
- Le temps moyen au tour
- La consommation moyenne par tour
- La capacité du réservoir
- L'option tour de formation
- L'option tour de sécurité supplémentaire

Il calcule ensuite :

- Le nombre de tours estimés
- Le carburant brut nécessaire
- Le carburant à charger, arrondi au litre supérieur
- Le nombre d'arrêts nécessaires
- Les tours conseillés pour les arrêts

---

## 💾 Sauvegarde des données

Les tours sont sauvegardés automatiquement dans :

```text
Documents/ACC_pitwall_donnees/
```

Chaque combinaison voiture / circuit possède son propre fichier JSON.

Exemple :

```text
Documents/ACC_pitwall_donnees/ferrari_488_gt3_evo__monza.json
```

Les données sauvegardées permettent de retrouver automatiquement :

- Le nombre total de tours enregistrés
- Le meilleur tour
- Le temps moyen
- La consommation moyenne
- La consommation minimale et maximale

---

## 📂 Exemple de fichier JSON

```json
{
  "car": "ferrari_488_gt3_evo",
  "track": "monza",
  "sessions": [
    {
      "lap_number": 5,
      "lap_time_sec": 105.234,
      "fuel_used": 2.85,
      "fuel_remaining": 92.4,
      "session_type": "Race",
      "tyre_compound": "DHE",
      "air_temp": 22.0,
      "road_temp": 35.0,
      "timestamp": "2026-05-24T14:32:10"
    }
  ],
  "stats": {
    "total_laps": 42,
    "best_lap_sec": 104.8,
    "avg_lap_time_sec": 106.1,
    "avg_fuel_per_lap": 2.83,
    "min_fuel_per_lap": 2.71,
    "max_fuel_per_lap": 3.12
  }
}
```

---

## 🛠️ Utilisation conseillée

1. Lancer ACC
2. Entrer dans une session Practice, Qualifying ou Race
3. Lancer le serveur avec :

```bash
python server.py
```

4. Ouvrir `acc_pitwall.html`
5. Faire quelques tours pour obtenir une consommation moyenne fiable
6. Entrer la durée de course
7. Cliquer sur **Calculer**

---

## ⚠️ Notes importantes

- Le mode live fonctionne uniquement sous Windows.
- ACC doit être lancé et une session doit être active.
- Le fichier HTML doit rester ouvert pendant l'utilisation.
- Le serveur doit rester lancé pendant l'utilisation.
- Si l'interface affiche serveur hors ligne, vérifier que `server.py` est bien lancé.
- Si ACC n'est pas détecté, vérifier que le jeu est bien en session active.

---

## 🧪 Fichiers optionnels

`acc_live_logger.py` peut encore servir pour tester l'ancien mode console ou simuler des tours, mais il n'est plus nécessaire pour l'utilisation normale avec l'interface HTML.

L'utilisation principale est maintenant :

```bash
python server.py
```

puis ouverture de :

```text
acc_pitwall.html
```
