#!/usr/bin/env bash
# Lance l'upload manuel d'une prod (macOS / Linux) : bash run_single_upload.sh
# Prerequis : setup.sh execute, config.json rempli, connexion Shopify faite
# (login_shopify_chrome.sh). Ferme Chrome avant de lancer.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
    echo "[ERREUR] Installation manquante. Lance d'abord : bash setup.sh"
    exit 1
fi
if [ ! -f config.json ]; then
    echo "[ERREUR] config.json est introuvable. Fais : cp config.example.json config.json (puis remplis-le)"
    exit 1
fi
exec .venv/bin/python single_upload.py
