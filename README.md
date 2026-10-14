# ACC Pit Wall

Application compagnon pour **Assetto Corsa Competizione** : stratégie carburant, télémétrie et historique des sessions.

## Installation (joueurs)

1. Télécharge **ACC_PitWall_Setup_vX.Y.Z.exe** depuis la [dernière version publiée](https://github.com/Hugo-ride/ACC_pitwall/releases/latest).
2. Lance l’installateur et suis les étapes. Il installe l’application et crée ses raccourcis.
3. Ouvre ACC Pit Wall depuis le menu Démarrer ou le raccourci du bureau. Python et les fichiers du dépôt ne sont pas nécessaires.

**Ne télécharge pas `ACC_PitWall.exe` seul** : choisis le fichier `ACC_PitWall_Setup_...exe` dans la page de la Release.

L’application vérifie les mises à jour disponibles. Lorsqu’une nouvelle version est proposée, confirme son installation ; l’installateur est téléchargé et lancé automatiquement. Une confirmation Windows peut être demandée.

Tu peux démarrer ACC Pit Wall avant ou après avoir rejoint une session de jeu. L’application attend ACC et se connecte lorsqu’il est disponible.

La carte télémétrique est orientée dans le sens de circulation et distingue les voitures par couleur et numéro. Le numéro correspond à leur ordre estimé sur le tracé, pas au classement officiel ACC ; seul le classement du joueur est fourni par le jeu. Les secteurs sont appris avec ACC lors de l'enregistrement du tracé. Les anciennes cartes utilisent des limites estimées jusqu'à ce qu'un tour complet permette de les mettre à jour.

## Données et confidentialité

Les tours, statistiques, sessions et tracés de circuits appris sont conservés localement sur le PC, dans `Documents\ACC_pitwall_donnees`. Ils ne sont pas envoyés à un serveur distant. La carte d'un circuit apparaît après qu'un tour complet a permis d'enregistrer son tracé. La connexion à Internet sert notamment à vérifier et télécharger les mises à jour.
