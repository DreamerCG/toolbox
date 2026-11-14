# Gestion des Installers

Les installers sont maintenant externalisés dans le fichier `toolbox/installers.json`, permettant d'ajouter ou de modifier des installers sans modifier le code Python.

## Structure d'un Installer

Chaque installer doit suivre la structure suivante :

```json
{
    "name": "Nom de l'Installer",
    "author": "By AuthorName",
    "tag": "CATÉGORIE",
    "description": [
        "Description ligne 1",
        "Description ligne 2",
        "Description ligne 3"
    ],
    "command": "curl -Ls https://... | bash",
    "warning": "Message d'avertissement pour l'utilisateur"
}
```

### Champs obligatoires

| Champ | Type | Description |
|-------|------|-------------|
| `name` | string | Nom affiché de l'installer |
| `author` | string | Auteur de l'installer |
| `tag` | string | Catégorie/Tag (ex: "ARCADE · TEKNOPARROT") |
| `description` | array | Tableau de 3 lignes de description |
| `command` | string | Commande bash à exécuter |
| `warning` | string | Message d'avertissement pour l'utilisateur |

## Ajouter un Nouvel Installer

1. Ouvrez `toolbox/installers.json`
2. Ajoutez un nouvel objet JSON avant la dernière accolade fermante `]`
3. Assurez-vous que le JSON reste valide (virgule après le dernier installer existant)

### Exemple

```json
{
    "name": "Mon Nouvel Installer",
    "author": "By MonNom",
    "tag": "CATÉGORIE SPÉCIALE",
    "description": [
        "Première ligne de description",
        "Deuxième ligne de description",
        "Troisième ligne de description"
    ],
    "command": "curl -Ls https://mon-url.com/install.sh | bash",
    "warning": "Message d'avertissement personnalisé"
}
```

## Validation

Pour valider que votre fichier JSON est correct :

```bash
python -m json.tool toolbox/installers.json
```

## Notes Importantes

- ⚠️ Les caractères accentués sont supportés (UTF-8)
- ⚠️ La description doit contenir exactement 3 lignes
- ⚠️ Assurez-vous que la virgule est présente après chaque installer sauf le dernier
- ⚠️ Les guillemets simples dans les descriptions doivent être échappés ou utiliser les guillemets doubles

## Modification du Code Python

Aucune modification du code Python n'est nécessaire ! La fonction `load_installers()` dans `toolbox_ui.py` charge automatiquement le fichier JSON au démarrage.
