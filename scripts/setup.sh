#!/usr/bin/env bash
# Installation (macOS / Linux) - a lancer une seule fois depuis le dossier scripts/ :
#     bash setup.sh
# Cree un environnement Python isole (.venv), installe les dependances et verifie
# que Playwright sait piloter le vrai Google Chrome (voir README).
set -euo pipefail
cd "$(dirname "$0")"

OS="$(uname -s)"
echo ""
echo "=== BeatStars -> Shopify : installation ($OS) ==="
echo ""

# 1. Python 3.9+ avec tkinter (fenetres de selection de fichiers)
echo "[1/4] Verification de Python..."
if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERREUR] python3 est introuvable."
    [ "$OS" = "Darwin" ] && echo "         Installe-le avec : brew install python python-tk"
    [ "$OS" = "Linux" ]  && echo "         Ubuntu/Debian : sudo apt install python3 python3-venv python3-tk"
    exit 1
fi
if ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
    echo "[ERREUR] Python 3.9 ou plus recent est requis (trouve : $(python3 --version))."
    exit 1
fi
if ! python3 -c 'import tkinter' >/dev/null 2>&1; then
    echo "[ERREUR] tkinter est manquant (necessaire pour choisir les fichiers)."
    [ "$OS" = "Darwin" ] && echo "         Installe-le avec : brew install python-tk"
    [ "$OS" = "Linux" ]  && echo "         Ubuntu/Debian : sudo apt install python3-tk"
    exit 1
fi
echo "[OK] $(python3 --version)"

# 2. Google Chrome (le vrai, pas Chromium : Shopify bloque les navigateurs automatises)
echo "[2/4] Verification de Google Chrome..."
if [ "$OS" = "Darwin" ]; then
    CHROME_OK=0; [ -x "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ] && CHROME_OK=1
else
    CHROME_OK=0
    { [ -x /opt/google/chrome/chrome ] || command -v google-chrome-stable >/dev/null 2>&1; } && CHROME_OK=1
fi
if [ "$CHROME_OK" -ne 1 ]; then
    echo "[ERREUR] Google Chrome est introuvable. Installe-le depuis https://www.google.com/chrome"
    [ "$OS" = "Linux" ] && echo "         (Linux : utilise le paquet .deb/.rpm officiel, pas Chromium en snap.)"
    exit 1
fi
echo "[OK] Google Chrome trouve"

# 3. Environnement virtuel + dependances
echo "[3/4] Installation des dependances Python (quelques minutes)..."
python3 -m venv .venv
.venv/bin/python -m pip install --quiet --upgrade pip
.venv/bin/python -m pip install --quiet -r requirements.txt
echo "[OK] Dependances installees"

# 4. Test reel : Playwright pilote-t-il bien Chrome ?
echo "[4/4] Test de lancement de Chrome via Playwright..."
if ! .venv/bin/python _verify_playwright.py; then
    echo "[ERREUR] Chrome n'a pas pu etre lance par Playwright (voir le message ci-dessus)."
    exit 1
fi

# Info facultative : extraction des archives .rar (stems)
if ! command -v unrar >/dev/null 2>&1 && ! command -v unar >/dev/null 2>&1 && ! command -v bsdtar >/dev/null 2>&1; then
    echo ""
    echo "[INFO] Aucun outil d'extraction RAR detecte. Les stems .rar ne seront pas verifies."
    echo "       Facultatif : bash setup_unrar.sh"
fi

echo ""
echo "=== Installation terminée ==="
echo ""
echo "Etapes suivantes :"
echo "  1. cp config.example.json config.json   (puis remplis-le)"
echo "  2. bash login_shopify_chrome.sh          (connexion a Shopify, une seule fois)"
echo "  3. bash run_single_upload.sh             (envoyer une prod)"
