# 🏁 ACC Pit Wall

Outil de stratégie essence pour **Assetto Corsa Competizione**, avec une interface web en HTML et un serveur Python qui lit les données du jeu en temps réel.

## Utilisation de l'exécutable

Lance `dist/ACC_PitWall.exe` après avoir rejoint une session ACC. L'exécutable
contient l'interface, le serveur et leurs dépendances ; Python et les autres
fichiers du projet ne sont pas nécessaires sur le PC utilisé. L'application
retente la connexion à la mémoire partagée du jeu si celle-ci n'est pas encore
disponible. Les statistiques restent dans `Documents/ACC_pitwall_donnees/`.
Pour une installation classique, utilise plutôt
`dist/ACC_PitWall_Setup_v1.1.2.exe`.

Pour le générer sous Windows, installe Python 3.10 ou plus récent puis lance
`BUILD.bat`. Le script prépare son environnement de compilation et écrit
l'exécutable autonome dans `dist/ACC_PitWall.exe`. Seul ce fichier est à
distribuer.

### Installation, versions et mises à jour

Installe [Inno Setup 6](https://jrsoftware.org/isinfo.php), puis lance
`BUILD.bat installer` pour créer `dist/ACC_PitWall_Setup_v1.1.2.exe`.
L'installateur affiche la licence et demande les droits administrateur Windows
pour installer l'application dans `C:\Program Files\ACC Pit Wall`. Il essaie
de fermer ACC Pit Wall si l'application est encore ouverte pendant une mise à
jour ou une désinstallation. Après installation, l'application peut être
lancée depuis le menu Démarrer ou le raccourci du bureau.
Le nom de l'éditeur affiché dans les informations de l'application est
« Hugo LOYER ». Pour remplacer « Éditeur inconnu » dans l'avertissement
SmartScreen, il faut également signer les exécutables avec un certificat de
signature de code reconnu par Windows.

La version de l'application est définie dans `version.py` et suit
[SemVer](https://semver.org/) : incrémenter le dernier chiffre pour un correctif,
le chiffre du milieu pour une évolution compatible, et le premier pour une
version incompatible. Pour publier une version stable, mettre à jour
`APP_VERSION`, pousser le commit, puis créer et pousser le tag correspondant
(par exemple `v1.1.0`). GitHub Actions construit l'exécutable et l'installateur,
puis les joint à une Release. L'application signale une mise à jour disponible
au démarrage lorsqu'une Release stable plus récente existe.

La signature numérique nécessite un certificat de signature de code valide.
Sans certificat, les artefacts restent non signés. Pour activer la signature
dans GitHub Actions, configurer les secrets de dépôt
`WINDOWS_SIGNING_CERTIFICATE_BASE64` et `WINDOWS_SIGNING_CERTIFICATE_PASSWORD`.

### Version développeur avec les données fournies

Lance `BUILD.bat dev` pour générer `dist/ACC_PitWall_Dev.exe`, avec les données
du dossier `ACC_pitwall_donnees` intégrées comme jeu de départ. Au premier
lancement, elles sont copiées dans `%LOCALAPPDATA%\ACC_PitWall_Dev\data` et
l'application utilise cette copie indépendante pour ne pas modifier les
fichiers fournis. Cette version conserve ses changements de test entre les
lancements et garde son profil d'interface séparé de la version normale.
Pour tester depuis les sources dans PowerShell :

```powershell
$env:ACC_PITWALL_DEV = "1"
.\.venv\Scripts\python.exe .\launcher.py
```

## Lancement depuis les sources (développement)

---

## 📁 Structure des fichiers

```text
ACC_pitwall/
├── launcher.py                # Lanceur natif (serveur + interface)
├── server.py                  # Serveur WebSocket
├── acc_pitwall.html            # Interface intégrée à l'exécutable
├── fuel_calculator.py         # Calculs de stratégie + sauvegarde JSON
├── acc_shared_memory.py       # Lecture mémoire partagée ACC, Windows uniquement
├── track_locations.js         # Pays, drapeaux et noms des circuits reconnus
├── track_maps/                # Cartes hors ligne avec l'emplacement des circuits
├── track_flags/               # Drapeaux SVG hors ligne
├── acc_live_logger.py         # Ancien logger console / simulation, optionnel
└── README.md
```

Les cartes des circuits sont générées à partir des contours de pays Natural Earth
(données du domaine public). Cartes et drapeaux sont embarqués et apparaissent
lorsqu'un circuit reconnu est détecté dans ACC.

---

## Lancement manuel depuis les sources

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

### Lancement du serveur et de l'interface

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
- Affiche les commandes (gaz/frein) et les données pneus/freins
- Permet de rechercher les sessions dans les statistiques
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

## 🛠️ Utilisation conseillée depuis les sources

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
- En mode sources, le fichier HTML et le serveur doivent rester ouverts.
- Avec `dist/ACC_PitWall.exe`, le serveur et l'interface démarrent ensemble.
- En mode sources, si l'interface affiche serveur hors ligne, vérifier que `server.py` est bien lancé.
- Si ACC n'est pas détecté, vérifier que le jeu est bien en session active.

---

## 🧪 Fichiers optionnels

`acc_live_logger.py` peut encore servir pour tester l'ancien mode console ou simuler des tours, mais il n'est plus nécessaire pour l'utilisation normale avec l'interface HTML.

Le lancement de développement se fait avec :

```bash
python server.py
```

puis ouverture de :

```text
acc_pitwall.html
```
