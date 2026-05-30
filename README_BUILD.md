# 🏁 ACC Pit Wall — Créer le logiciel (.exe)

## Structure nécessaire avant de compiler

Ton dossier doit contenir **exactement** ces fichiers :

```
ACC_pitwall/
├── BUILD.bat                ← Double-cliquer pour compiler
├── ACC_PitWall.spec         ← Configuration PyInstaller
├── version_info.txt         ← Métadonnées Windows
├── launcher.py              ← Point d'entrée du logiciel
│
├── acc_pitwall.html         ← Ton interface web
├── server.py                ← Serveur WebSocket
├── acc_shared_memory.py     ← Lecture mémoire ACC
├── fuel_calculator.py       ← Calculs essence
│
├── app_icon.ico             ← Icône Windows (.ico)
├── app_icon_512.png         ← Icône haute résolution
│
└── carte_circuits/          ← Dossier images circuits (optionnel)
    ├── Monza2010.png
    ├── Spa-Francorchamps-2022.png
    └── ...
```

---

## Compiler le .exe

### Étape 1 — Prérequis
- Python 3.10 ou plus (https://python.org)
- Cocher **"Add Python to PATH"** lors de l'installation

### Étape 2 — Compiler
Double-cliquer sur **`BUILD.bat`**

Le script installe automatiquement PyInstaller et toutes les dépendances, puis compile.

### Étape 3 — Résultat
Le fichier **`dist/ACC_PitWall.exe`** est créé.

**Ce fichier seul suffit.** Tes amis n'ont besoin de rien d'autre.

---

## Distribuer à tes amis

Envoie simplement `ACC_PitWall.exe`.

Aucune installation de Python requise.  
Aucune dépendance à installer.  
Double-clic → L'application démarre.

---

## Ce que fait le logiciel au démarrage

1. Une fenêtre de contrôle s'ouvre avec le logo ACC Pit Wall
2. Le serveur WebSocket démarre automatiquement en arrière-plan
3. Le navigateur s'ouvre sur l'interface
4. Dès qu'ACC est lancé et qu'une session est active, la connexion se fait automatiquement

**Ton ami n'a jamais à toucher à Python ou au terminal.**

---

## Taille finale estimée

Entre **25 et 40 Mo** selon les dépendances Python incluses.

---

## Notes techniques

- Le serveur ne démarre **qu'après** que l'interface graphique soit prête,
  ce qui évite les crashs d'ACC lors du démarrage.
- Si le serveur plante, il redémarre automatiquement.
- Les données sont sauvegardées dans `Documents/ACC_pitwall_donnees/`
  sur le PC de chaque utilisateur, séparément.
