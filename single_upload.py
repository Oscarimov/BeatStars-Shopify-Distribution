# single_upload_debug.py
# Version ULTRA-VERBOSE avec logs pour debug
# Place ce fichier à côté de uploader.py et config.json

import shutil
import tempfile
from pathlib import Path
import csv
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import os
import sys
import traceback

# Import du uploader fourni
from uploader import ShopifyGraphQLUploader


def debug_print(title, data=None):
    """Affiche des messages bien visibles pour le debug."""
    print("\n" + "="*80)
    print("🟦 DEBUG:", title)
    if data is not None:
        print(data)
    print("="*80 + "\n")


def ask_files():
    root = tk.Tk()
    root.withdraw()

    try:
        messagebox.showinfo("Sélection des fichiers", 
            "Sélectionne la cover, puis le MP3, puis le WAV (optionnel), puis les STEMS (optionnel).")

        cover = filedialog.askopenfilename(
            title="Cover image (JPG, PNG, GIF, WEBP uniquement)", 
            filetypes=[
                ("Images", "*.jpg *.jpeg *.png *.gif *.webp *.bmp *.tiff"),
                ("JPG", "*.jpg *.jpeg"),
                ("PNG", "*.png"),
                ("Toutes images", "*.jpg *.jpeg *.png *.gif *.webp *.bmp *.tiff"),
                ("Tous fichiers", "*.*")
            ]
        )
        
        debug_print("Cover sélectionnée", cover)

        if not cover:
            return None

        mp3 = filedialog.askopenfilename(title="MP3")
        debug_print("MP3 sélectionné", mp3)

        if not mp3:
            return None

        wav = filedialog.askopenfilename(title="WAV (optionnel) — Annuler si aucun")
        debug_print("WAV sélectionné", wav)

        if wav == "":
            wav = None

        stems = filedialog.askopenfilename(title="STEMS (zip/rar) — Annuler si aucun")
        debug_print("STEMS sélectionné", stems)

        if stems == "":
            stems = None

        return {
            "cover": cover,
            "mp3": mp3,
            "wav": wav,
            "stems": stems
        }

    except Exception as e:
        debug_print("Erreur dans ask_files()", traceback.format_exc())
        return None
    finally:
        root.destroy()


def ask_metadata(default_title=None):
    root = tk.Tk()
    root.withdraw()

    try:
        title = simpledialog.askstring("Titre", "Nom de la prod :", initialvalue=default_title or "")
        debug_print("Titre entré", title)

        if not title:
            return None

        bpm = simpledialog.askstring("BPM", "BPM :", initialvalue="")
        debug_print("BPM entré", bpm)

        if bpm is None:
            bpm = ""

        tags = simpledialog.askstring("Tags", "Tags (séparés par des virgules) :", initialvalue="")
        debug_print("Tags entrés", tags)

        if tags is None:
            tags = ""

        return {
            "title": title.strip(),
            "bpm": bpm.strip() or "0",
            "tags": tags.strip()
        }

    except Exception as e:
        debug_print("Erreur dans ask_metadata()", traceback.format_exc())
        return None
    finally:
        root.destroy()


def prepare_temp_folder(files: dict, metadata: dict):
    debug_print("Préparation du dossier temporaire", {"files": files, "metadata": metadata})

    safe_title = "".join(c for c in metadata["title"] if c.isalnum() or c in " _-").strip()
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    folder_name = f"{safe_title}_{timestamp}"

    base_dir = Path(tempfile.gettempdir()) / "shopify_single_uploads" / folder_name
    base_dir.mkdir(parents=True, exist_ok=True)

    debug_print("Dossier créé", str(base_dir))

    # Copie des fichiers
    def copy_with_pattern(src_path, suffix):
        if not src_path:
            return None
        try:
            src = Path(src_path)
            dest = base_dir / src.name  # ← CHANGEMENT ICI : utiliser src.name au lieu de f"{safe_title}{suffix}{ext}"
            shutil.copy2(src, dest)
            debug_print(f"Copie {suffix}", f"{src} -> {dest}")
            return dest
        except Exception:
            debug_print(f"Erreur copie {suffix}", traceback.format_exc())
            return None

    artwork = copy_with_pattern(files.get("cover"), "_artwork")
    mp3 = copy_with_pattern(files.get("mp3"), "_MP3")
    wav = copy_with_pattern(files.get("wav"), "_WAV") if files.get("wav") else None
    stems = copy_with_pattern(files.get("stems"), "_STEMS") if files.get("stems") else None

    # Génération du CSV
    csv_path = base_dir / f"{safe_title}_metadata.csv"
    try:
        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["title", "bpm", "tags", "creation_date"])
            writer.writerow([
                metadata["title"], 
                metadata["bpm"], 
                metadata["tags"],
                datetime.now().strftime("%b %d, %Y")
            ])
        debug_print("CSV généré", str(csv_path))
    except Exception:
        debug_print("Erreur CSV", traceback.format_exc())

    return base_dir


def main():
    debug_print("Démarrage du script")

    files = ask_files()
    if not files:
        debug_print("Aucun fichier sélectionné")
        sys.exit(1)

    metadata = ask_metadata()
    if not metadata:
        debug_print("Aucun metadata -> stop")
        sys.exit(1)

    beat_folder = prepare_temp_folder(files, metadata)
    debug_print("Dossier final prêt", str(beat_folder))

    # Chargement du uploader
    try:
        # Pass the temporary beat_folder to avoid folder selection dialog
        # since single_upload creates its own temp folder
        uploader = ShopifyGraphQLUploader("config.json", beats_folder=beat_folder)
        debug_print("Uploader chargé OK")
    except Exception:
        debug_print("Erreur création ShopifyGraphQLUploader", traceback.format_exc())
        sys.exit(1)

    # Login Playwright
    try:
        if uploader.config.get('auto_upload_digital_downloads', True):
            debug_print("Tentative login Shopify via Playwright…")
            uploader.login_to_shopify()
            debug_print("Login Playwright -> OK")
    except Exception:
        debug_print("Erreur login Playwright", traceback.format_exc())

    debug_print("Début upload Shopify")

    try:
        result = uploader.upload_beat_to_shopify(beat_folder, index=1)
        debug_print("Résultat upload", result)
    except Exception:
        debug_print("ERREUR upload_beat_to_shopify()", traceback.format_exc())
        messagebox.showerror("Erreur critique", "ERREUR upload_beat_to_shopify — voir console")
        sys.exit(1)

    # Analyse résultat
    if result.get("status") == "created":
        message = f"UPLOAD OK — Produit Shopify créé : {result.get('title')}"
        messagebox.showinfo("Succès", message)
    elif result.get("status") == "skipped":
        message = "Produit déjà existant — ignoré."
        messagebox.showwarning("Skip", message)
    else:
        message = "Erreur pendant l’upload — voir console DEBUG."
        messagebox.showerror("Erreur", message)

    debug_print("Script terminé — FIN")


if __name__ == "__main__":
    main()