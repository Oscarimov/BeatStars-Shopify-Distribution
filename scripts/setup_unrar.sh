#!/usr/bin/env bash
# Facultatif (macOS / Linux) : installe un outil d'extraction RAR pour verifier les stems .rar.
# Sans lui, tout fonctionne sauf la verification d'integrite des archives .rar.
set -euo pipefail

if command -v unrar >/dev/null 2>&1; then
    echo "[OK] unrar est deja installe : $(command -v unrar)"
    exit 0
fi

case "$(uname -s)" in
    Darwin)
        if ! command -v brew >/dev/null 2>&1; then
            echo "Homebrew est requis : https://brew.sh (puis relance ce script)"
            exit 1
        fi
        # Le paquet 'unrar' de Homebrew a change de statut (licence non libre) ; 'unar' est une alternative libre
        # reconnue par la librairie rarfile. macOS fournit aussi 'bsdtar' d'origine.
        brew install unrar || brew install unar
        ;;
    Linux)
        if   command -v apt-get >/dev/null 2>&1; then sudo apt-get update && sudo apt-get install -y unrar || sudo apt-get install -y unar
        elif command -v dnf     >/dev/null 2>&1; then sudo dnf install -y unrar
        elif command -v pacman  >/dev/null 2>&1; then sudo pacman -S --noconfirm unrar
        elif command -v zypper  >/dev/null 2>&1; then sudo zypper install -y unrar
        else echo "Aucun gestionnaire de paquets reconnu : installe 'unrar' ou 'unar' a la main."; exit 1
        fi
        ;;
    *) echo "Systeme non supporte : $(uname -s)"; exit 1 ;;
esac

if command -v unrar >/dev/null 2>&1 || command -v unar >/dev/null 2>&1; then
    echo "[OK] Outil d'extraction RAR installe."
else
    echo "[ERREUR] Installation terminee mais aucun outil detecte."; exit 1
fi
