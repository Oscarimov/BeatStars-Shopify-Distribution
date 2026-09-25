#!/usr/bin/env bash
# Connexion a Shopify (macOS / Linux) - equivalent de login_shopify_chrome.bat.
# Ouvre un Chrome NORMAL (aucune automatisation) sur le profil dedie chrome_profile/.
# Shopify bloque le captcha sur un navigateur pilote par un script : on se connecte
# donc a la main ici, une seule fois, puis le bot reutilise ce profil deja connecte.
set -euo pipefail
cd "$(dirname "$0")"

case "$(uname -s)" in
    Darwin) CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" ;;
    *)      CHROME="$(command -v google-chrome-stable || true)"
            [ -z "$CHROME" ] && [ -x /opt/google/chrome/chrome ] && CHROME=/opt/google/chrome/chrome ;;
esac
if [ -z "${CHROME:-}" ] || [ ! -x "$CHROME" ]; then
    echo "[ERREUR] Google Chrome est introuvable. Installe-le depuis https://www.google.com/chrome"
    exit 1
fi

echo ""
echo "Ferme d'abord toutes les fenetres Chrome (Cmd+Q sur Mac), puis :"
echo "  1. Connecte-toi a Shopify dans la fenetre qui s'ouvre"
echo "  2. Une fois sur ton tableau de bord, ferme Chrome"
echo ""
"$CHROME" --user-data-dir="$PWD/chrome_profile" "https://admin.shopify.com"
