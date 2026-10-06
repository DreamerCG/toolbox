# Batocera Ultimate Toolbox

Interface Pygame plein écran pour lancer les installateurs DreamerCG sur Batocera.
Navigation clavier, manette et souris. `install.sh` reste à la racine du dépôt ;
les fichiers de l’application sont séparés dans `toolbox/`.

## Installation

Depuis Batocera, lancez l’installateur avec :

```bash
curl -fsSL https://raw.githubusercontent.com/DreamerCG/toolbox/main/install.sh | bash
```

Le script installe l’application dans `/userdata/roms/ports/dcgtoolbox` et crée
le lanceur `/userdata/roms/ports/Batocera Ultimate Toolbox.sh`. Il ne télécharge que les
fichiers de `toolbox/`, pas l’archive complète du dépôt.

## Mises à jour

Le fichier `toolbox/version` contient la version publiée. Au démarrage,
l’application compare cette valeur à celle du dépôt GitHub
`DreamerCG/toolbox`. Si une version plus récente est publiée, seuls les fichiers
de `toolbox/` sont téléchargés et remplacés automatiquement.

Pour publier une mise à jour, augmentez `toolbox/version` (par exemple `0.1.1`)
et publiez les fichiers mis à jour dans `toolbox/` sur la branche `main`.
