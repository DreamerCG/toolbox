#!/usr/bin/env bash
set -euo pipefail

REPOSITORY="DreamerCG/toolbox"
BRANCH="main"
PORTS_DIR="/userdata/roms/ports"
APP_DIR="$PORTS_DIR/dcgtoolbox"
PORT_SCRIPT="$PORTS_DIR/Batocera Ultimate Toolbox.sh"
OLD_PORT_SCRIPT="$PORTS_DIR/DreamerCG Toolbox.sh"

if [[ ! -d /userdata ]]; then
    echo "Erreur : cet installateur doit être lancé sur Batocera."
    exit 1
fi
mkdir -p "$PORTS_DIR"

command -v python3 >/dev/null 2>&1 || { echo "Erreur : python3 est introuvable."; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "Erreur : curl est introuvable."; exit 1; }

WORK_BASE="/userdata/system"
[[ -d "$WORK_BASE" ]] || WORK_BASE="/tmp"
WORK="$(mktemp -d "$WORK_BASE/dcgtoolbox-install.XXXXXX")"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd || true)"
SOURCE_DIR="$SCRIPT_DIR/toolbox"
if [[ ! -f "$SOURCE_DIR/toolbox_ui.py" || ! -f "$SOURCE_DIR/version" ]]; then
    echo "Téléchargement des fichiers de l’application depuis GitHub…"
    SOURCE_DIR="$WORK/toolbox"
    mkdir -p "$SOURCE_DIR"
    for file in toolbox_ui.py Logo.jpg avatar.png version repository; do
        URL="https://raw.githubusercontent.com/${REPOSITORY}/${BRANCH}/toolbox/${file}"
        curl --fail --location --silent --show-error --retry 3 "$URL" -o "$SOURCE_DIR/$file"
    done
fi

for file in toolbox_ui.py Logo.jpg avatar.png version repository; do
    [[ -f "$SOURCE_DIR/$file" ]] || { echo "Erreur : fichier manquant : $file"; exit 1; }
done

mkdir -p "$APP_DIR"
echo "Installation de la toolbox dans $APP_DIR…"
for file in toolbox_ui.py Logo.jpg avatar.png repository; do
    install -m 0644 "$SOURCE_DIR/$file" "$APP_DIR/$file.new"
    mv -f "$APP_DIR/$file.new" "$APP_DIR/$file"
done
install -m 0644 "$SOURCE_DIR/version" "$APP_DIR/version.new"
mv -f "$APP_DIR/version.new" "$APP_DIR/version"

PORT_TMP="$PORT_SCRIPT.new"
cat > "$PORT_TMP" <<'PORT_EOF'
#!/usr/bin/env bash
set -e
PORTS_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$PORTS_DIR/dcgtoolbox"
exec python3 "$APP_DIR/toolbox_ui.py"
PORT_EOF
chmod 0755 "$PORT_TMP"
mv -f "$PORT_TMP" "$PORT_SCRIPT"
if [[ -f "$OLD_PORT_SCRIPT" ]]; then
    rm -f -- "$OLD_PORT_SCRIPT"
fi

curl --fail --silent "http://127.0.0.1:1234/reloadgames" >/dev/null 2>&1 || true
echo "Batocera Ultimate Toolbox $(cat "$APP_DIR/version") installée dans Ports."
echo "Lancez Batocera Ultimate Toolbox depuis EmulationStation > Ports."
