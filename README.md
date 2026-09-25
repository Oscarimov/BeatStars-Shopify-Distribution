# BeatStars to Shopify Tool v3.1

## 🎯 Vue d'ensemble

Outil complet pour automatiser le transfert de vos productions musicales depuis BeatStars vers votre boutique Shopify. Gère le téléchargement automatique des fichiers depuis BeatStars (MP3, WAV, STEMS, artwork) et leur mise en ligne sur Shopify avec différentes options de tarification.

**✨ v3.1** : Exécutables autonomes qui pilotent votre vrai Chrome (connexion Shopify unique via `login_shopify_chrome.bat`, plus de navigateur embarqué).

---

## 📦 Contenu du Package

Vous avez **deux outils** au choix :

### 1. **BeatStars-Shopify-Tool.exe** (Outil Complet)
**Workflow complet avec menu interactif** :
```
1. Scraper BeatStars → Télécharge vos beats automatiquement
2. Upload Shopify → Met en ligne sur votre boutique
3. Workflow complet → Fait tout en une fois
```

**Idéal pour** : Gérer votre catalogue complet de beats

### 2. **Single-Upload-Tool.exe** (Upload Manuel)
**Upload rapide d'un seul beat** :
- Sélection manuelle des fichiers (cover, MP3, WAV, STEMS)
- Formulaire pour titre, BPM, tags
- Upload direct vers Shopify

**Idéal pour** : Uploads ponctuels, tests, beats hors BeatStars

---

## 🚀 Installation Rapide (5 minutes)

### Étape 1 : Extraction

**Téléchargez tous les fichiers** et gardez tous les fichiers ensemble :
```
BeatStars-Shopify-Tool/
├── BeatStars-Shopify-Tool.exe    ← Outil complet (scraper + upload)
├── Single-Upload-Tool.exe         ← Upload manuel
├── login_shopify_chrome.bat       ← Connexion Shopify unique (à lancer avant la 1ère utilisation)
├── config.json                    ← À éditer
├── README.md
└── README_EN.md
```

**⚠️ IMPORTANT** : Ne déplacez pas les fichiers individuellement, gardez tout ensemble!

---

### Étape 2 : Prérequis par Fonctionnalité

#### Pour **Scraper BeatStars** (Option 1 du menu) :
- ✅ **Google Chrome installé** (dernière version)
  - Téléchargement : https://www.google.com/chrome/
  - ⚠️ **OBLIGATOIRE** pour télécharger depuis BeatStars
  - Le scraper utilise Selenium qui nécessite Chrome

#### Pour **Upload Shopify** (Option 2 du menu) :
- ✅ **Google Chrome installé** (dernière version)
  - Téléchargement : https://www.google.com/chrome/
  - ⚠️ **OBLIGATOIRE** : l'outil pilote votre vrai Chrome (pas un navigateur générique) pour éviter que Shopify bloque la connexion
  - Une connexion manuelle unique est requise via `login_shopify_chrome.bat` (voir section "Option 2 - Upload Shopify" plus bas)

#### Pour **Single Upload** :
- ✅ **Google Chrome installé** (même prérequis que l'upload Shopify ci-dessus)

---

### Étape 3 : Configuration du config.json

#### A. Obtenir votre Collection ID

**Méthode simple via Shopify :**
1. Allez sur **Shopify Admin** → **Products** → **Collections**
2. Cliquez sur votre collection (ex: "Mes instrus")
3. Dans l'URL du navigateur :
   ```
   https://admin.shopify.com/store/votre-store/collections/629200158987
                                                            ^^^^^^^^^^^^
   ```
4. **Copiez ce numéro** (ex: `629200158987`)

#### B. Configurer l'Authentification Shopify

**Option 1 : Token Legacy (si vous l'avez déjà)** ✅ Recommandé
```json
{
    "store_url": "votre-store.myshopify.com",
    "access_token": "shpat_votre_token_existant"
}
```

**Option 2 : Client Credentials (2026+)** 🆕
1. Shopify Admin → **Settings** → **Apps** → **Develop apps**
2. **Create app** → Donnez un nom
3. Sélectionnez ces **4 permissions** :
   - ✅ `read_products`
   - ✅ `write_products`
   - ✅ `read_files`
   - ✅ `write_files`
4. **Release** → Copiez **Client ID** et **Client Secret**

```json
{
    "store_url": "votre-store.myshopify.com",
    "client_id": "123456789",
    "client_secret": "shpcs_abc123..."
}
```

#### C. Éditer config.json

Ouvrez `config.json` et remplissez :

```json
{
    "store_url": "votre-store.myshopify.com",
    "access_token": "shpat_votre_token",
    "collection_id": "gid://shopify/Collection/629200158987",
    
    "beats_folder": "C:/Users/VotreNom/Downloads/Beats",
    "vendor": "VOTRE NOM D'ARTISTE",
    
    "shopify_login": {
        "email": "votre@email.com",
        "password": "votre_mot_de_passe_shopify",
        "auto_login": true
    },
    
    "beatstars_login": {
        "email": "votre@email.com",
        "password": "votre_mot_de_passe_beatstars",
        "auto_login": true
    },
    
    "variants": [
        {
            "name": "MP3",
            "price": "29.99",
            "digital_files": ["mp3"]
        },
        {
            "name": "PREMIUM (WAV)",
            "price": "44.99",
            "digital_files": ["wav"]
        },
        {
            "name": "PREMIUM + STEMS",
            "price": "79.99",
            "digital_files": ["stems"]
        }
    ]
}
```

**Points importants :**
- ⚠️ Remplacez `"gid://shopify/Collection/xxxxxxxxxxxx"` par votre **vrai** numéro
- ⚠️ Format du collection_id : `"gid://shopify/Collection/629200158987"`
- ⚠️ Utilisez `/` dans les chemins Windows : `C:/Users/...` (pas `\`)

---

## 📘 Utilisation

### Tool #1 : BeatStars-Shopify-Tool.exe (Outil Complet)

**Double-cliquez sur `BeatStars-Shopify-Tool.exe`**

**Menu principal :**
```
========================================
   BEATSTARS TO SHOPIFY TOOL v3.0
========================================

1. Scraper BeatStars (télécharger vos beats)
2. Upload Shopify (mettre en ligne)
3. Workflow complet (scraper + upload)
4. Afficher la configuration
5. Quitter

Votre choix : _
```

---

#### Option 1 - Scraper BeatStars (Téléchargement)

**🌐 Nécessite : Google Chrome installé**

**Workflow :**
1. **Chrome s'ouvre automatiquement** (Selenium)
2. **Connexion à BeatStars** :
   - Première fois : Entrez vos credentials manuellement
   - Session sauvegardée pour les fois suivantes
3. **Préparation** :
   - Basculez en **vue liste** (icône liste en haut)
   - Scrollez jusqu'en bas pour charger tous vos beats
4. **Appuyez sur Entrée** dans le terminal

   ⚠️**Très Important**⚠️ : Pour garantir le meilleur fonctionnement possible des téléchargements, le mieux est de ne plus toucher à votre pc ou à votre souris, certains téléchargements simulent un clic de votre souris, une utilisation parallele peut interférer avec le bot. Il est également conseiller de vérifier l'intégrité des fichiers téléchargés dans vos dossiers, pour s'assurer qu'ils sont tous présents, et retélécharger ceux qui manquent ou relancer le process pour les beats en questions.

5. **Choix du mode** :
   ```
   1. Télécharger tout (nouveau + manquants)
   2. Télécharger seulement les nouveaux
   3. Télécharger tout (forcer re-download)
   ```
6. **Téléchargement automatique** commence

**Fichiers téléchargés par beat :**
```
Beats/
└── Titre du Beat/
    ├── Titre du Beat.mp3           ← MP3 haute qualité
    ├── Titre du Beat.wav           ← WAV (si disponible)
    ├── Titre du Beat_stems.zip     ← STEMS extraits (si disponible)
    ├── Titre du Beat_artwork.jpg   ← Cover image
    └── Titre du Beat_metadata.csv  ← BPM, tags, date

```

**Formats d'archives supportés** (STEMS) :
- ✅ **ZIP** (intégré)
- ✅ **7Z** (intégré)
- ⚠️ **RAR** (nécessite UnRAR - voir section ci-dessous)
- ✅ **TAR.GZ** (intégré)

---

#### Option 2 - Upload Shopify

**🌐 Nécessite Google Chrome installé** (l'outil pilote votre vrai Chrome, pas juste les browsers inclus)

**⚠️ Étape unique à faire avant la première utilisation (ou si la session expire) :**
1. Double-cliquez sur `login_shopify_chrome.bat`
2. Une fenêtre Chrome normale s'ouvre (profil dédié à l'outil, aucune automatisation)
3. Connectez-vous à Shopify comme d'habitude (captcha/2FA si demandé — normal, résolvez-le comme toujours)
4. **Fermez complètement cette fenêtre Chrome** une fois sur le tableau de bord

Cette étape existe car Shopify peut bloquer la page de connexion pour tout navigateur piloté par un script. En vous connectant vous-même dans une fenêtre Chrome non automatisée, la session est ensuite réutilisée normalement par l'outil, sans jamais repasser par l'écran de login.

**Workflow :**
1. Le browser s'ouvre en utilisant la session déjà connectée
2. Pour chaque beat dans le dossier :
   - ✅ Création du produit
   - ✅ Création des variantes (MP3, WAV, STEMS)
   - ✅ Upload des fichiers téléchargeables
   - ✅ Attachment de la cover image
   - ✅ Ajout à la collection
3. Affichage du résumé

**Note** : Détecte automatiquement les produits déjà uploadés et les ignore

---

#### Option 3 - Workflow Complet

**Fait tout automatiquement** :
```
1. Scrape BeatStars → Télécharge vos beats
2. Upload Shopify → Met en ligne automatiquement
```

**Idéal pour** : Synchronisation complète de votre catalogue

---

### Tool #2 : Single-Upload-Tool.exe (Upload Manuel)

**Double-cliquez sur `Single-Upload-Tool.exe`**

**Dialogues interactifs :**
1. 🖼️ **Sélectionner cover image** (JPG, PNG, etc.)
2. 🎵 **Sélectionner MP3** (obligatoire)
3. 🎶 **Sélectionner WAV** (optionnel - Annuler pour passer)
4. 📦 **Sélectionner STEMS** (optionnel - Annuler pour passer)
5. ✏️ **Entrer titre** du beat
6. 🎼 **Entrer BPM** (optionnel)
7. 🏷️ **Entrer tags** (optionnel, séparés par virgules)
8. 🚀 **Upload automatique vers Shopify**

**Utilisez-le pour :**
- Tests rapides
- Beats qui ne sont pas sur BeatStars
- Uploads ponctuels d'un seul beat
- Vérifier que tout fonctionne

---

## 🔧 Configuration UnRAR (Optionnel)

**⚠️ Nécessaire UNIQUEMENT si vos STEMS sur BeatStars sont en format RAR**

Si vos archives STEMS sont en **ZIP ou 7Z**, vous n'avez rien à faire.

### Windows :
1. Téléchargez UnRAR : https://www.rarlab.com/rar_add.htm
2. Extrayez `UnRAR.exe`
3. Créez un dossier `tools\` à côté des .exe
4. Placez `UnRAR.exe` dans `tools\unrar.exe`

**Structure finale :**
```
BeatStars-Shopify-Tool/
├── BeatStars-Shopify-Tool.exe
├── Single-Upload-Tool.exe
├── login_shopify_chrome.bat
├── config.json
├── scripts (ignorez sauf si vous voulez modifier le code source)
└── tools/                          ← Créé par vous
    └── unrar.exe                   ← Téléchargé (si vous ne l'avez pas déjà et que vos             archives   sont en .rar)

```

---

## 🍎 Utilisation sur Mac (guide communautaire)

Deux guides pas-à-pas ont été rédigés par un utilisateur pour faire tourner le bot sur Mac depuis les sources :

- 📘 [1. Installer le bot sur Mac](https://oscarimov.github.io/BeatStars-Shopify-Distribution/mac/1-installation.html)
- 🚀 [2. Lancer le bot](https://oscarimov.github.io/BeatStars-Shopify-Distribution/mac/2-lancer-le-bot.html)

> ⚠️ **Non maintenu officiellement.** Les `.exe` restent Windows uniquement. Ces guides s'appuient sur des fichiers complémentaires Mac (`setup.sh`, `login_shopify_chrome.sh`, `run_single_upload.sh`, `macos.patch`) qui **ne sont pas inclus dans ce dépôt**, et n'ont pas été testés par le mainteneur. Relisez tout script avant de l'exécuter.

## 🐛 Résolution des Problèmes

### ❌ "Chrome driver error" ou "Chrome not found"

**Cause :** Chrome n'est pas installé

**Solution :**
```
1. Installez Google Chrome : https://www.google.com/chrome/
2. Relancez BeatStars-Shopify-Tool.exe
3. Utilisez l'Option 1 (Scraper BeatStars)
```

**Note :** Chrome est nécessaire pour **toutes** les fonctionnalités (scraper BeatStars, upload Shopify, Single Upload) — l'upload Shopify pilote directement votre Chrome installé, ce n'est plus juste le scraper qui en a besoin.

---

### ❌ "Erreur : collection_id invalide"

**Cause :** Vous avez laissé les placeholders `xxxxxxxxxxxx`

**Solution :**
1. Allez sur Shopify Admin → Products → Collections
2. Cliquez sur votre collection
3. Copiez le numéro dans l'URL : `collections/629200158987`
4. Dans config.json, utilisez :
   ```json
   "collection_id": "gid://shopify/Collection/629200158987"
   ```

**Formats INVALIDES :**
```json
"collection_id": "gid://shopify/Collection/xxxxxxxxxxxx"  ❌ Placeholders!
"collection_id": "629200158987"                           ❌ Manque le préfixe
"collection_id": "Mes instrus"                            ❌ C'est le nom!
```

---

### ❌ "Could not open Google Chrome" / Playwright n'arrive pas à lancer Chrome

**Cause la plus fréquente :** Le **Microsoft Visual C++ Redistributable (x64)** est manquant, périmé ou vient d'être réparé sans redémarrage. C'est une dépendance Windows dont Chrome a besoin pour démarrer, indépendante de Python/Playwright.

**Solution :**
1. Vérifiez que Google Chrome est bien installé : https://www.google.com/chrome/
2. Téléchargez et installez le VC++ Redistributable : https://aka.ms/vs/17/release/vc_redist.x64.exe
3. **Redémarrez votre PC** (souvent nécessaire pour que l'installation prenne effet)
4. Relancez l'outil

**Autre cause possible :** Une autre fenêtre utilise déjà le dossier `chrome_profile/` (celui créé par `login_shopify_chrome.bat`). Fermez toute fenêtre Chrome ouverte par l'outil avant de relancer.

**Note :** Cette erreur peut apparaître pour n'importe quelle fonctionnalité — l'outil pilote votre vrai Chrome pour tout (scraper, upload Shopify, Single Upload).

---

### ❌ "Config file not found"

**Cause :** config.json pas dans le même dossier que les .exe

**Solution :**
Copiez `config.json` **à côté** des exécutables

---

### ❌ "Token d'accès invalide"

**Si vous utilisez un token legacy (shpat_) :**
- Vérifiez qu'il commence bien par `shpat_`
- Vérifiez les permissions API dans Shopify Admin

**Si vous utilisez client credentials (2026+) :**
- Vérifiez que l'app est **installée** sur votre store
- Vérifiez les **4 permissions** sont cochées
- Vérifiez `client_id` et `client_secret`

---

### ❌ "Session expirée"

**Pour BeatStars :** Supprimez `beatstars_session.json` puis relancez l'outil → reconnexion automatique.

**Pour Shopify :** Relancez `login_shopify_chrome.bat` et reconnectez-vous. Si ça ne suffit pas, supprimez aussi le dossier `chrome_profile/` et recommencez la connexion depuis zéro.

---

### ❌ "Beats folder not found"

**Cause :** Le chemin dans `beats_folder` est incorrect

**Solution :**
- Windows : `"C:/Users/VotreNom/Documents/Beats"` (utilisez `/` pas `\`)
- OU laissez vide : `"beats_folder": ""` → dialogue de sélection au lancement

---

## ❓ Questions Fréquentes

### Prérequis et Installation

**Dois-je installer Python ?**
❌ Non! Python est inclus dans les exécutables

**Dois-je installer Playwright ?**
❌ Non! Playwright est inclus dans les exécutables — il pilote simplement votre Chrome déjà installé.

**Dois-je installer Chrome ?**
✅ **OUI** - pour toutes les fonctionnalités (scraper BeatStars, upload Shopify, Single Upload).

---

### Taille et Structure

**Quelle différence entre les deux .exe ?**
- **BeatStars-Shopify-Tool.exe** : 
  - Menu complet (scraper BeatStars + upload Shopify)
  - Workflow complet automatisé
- **Single-Upload-Tool.exe** : 
  - Upload manuel d'un seul beat
  - Sélection manuelle des fichiers

Les deux nécessitent Chrome et le même `login_shopify_chrome.bat`.

---

### Utilisation

**Les deux outils peuvent-ils coexister ?**
✅ OUI! Ils partagent le même profil Chrome (`chrome_profile/`) et le même `config.json`

**Comment mettre à jour l'outil ?**
Téléchargez la nouvelle version, gardez votre `config.json`

**L'outil fonctionne-t-il hors ligne ?**
❌ Non, connexion internet requise

**Puis-je interrompre le processus ?**
✅ Oui, avec `Ctrl+C`. Les beats déjà téléchargés sont conservés

**Puis-je partager avec mon équipe ?**
✅ Oui, mais chacun doit avoir son propre `config.json` avec ses credentials

**Le scraper BeatStars fonctionne-t-il sur tous les comptes ?**
✅ Oui, même comptes gratuits. Connectez-vous manuellement la première fois.

---

## 🔐 Sécurité

- ✅ Toutes les données restent locales sur votre ordinateur
- ✅ Identifiants stockés dans `config.json` (à protéger!)
- ✅ Ne partagez **jamais** vos tokens ou votre config
- ✅ Browsers proviennent de sources officielles (Playwright/Microsoft, Google Chrome)

**Sessions sauvegardées :**
- `beatstars_session.json` - Session BeatStars (scraper)
- `shopify_session.json` - Session Shopify (upload)
- `.shopify_token_cache` - Token API (si client credentials)
- `chrome_profile/` - Profil Chrome dédié à l'outil (contient vos cookies de connexion Shopify — ne partagez jamais ce dossier)

---

## 📊 Structure des Fichiers Téléchargés

Après téléchargement depuis BeatStars (Option 1) :

```
Beats/
├── Titre Beat 1/
│   ├── Titre Beat 1.mp3
│   ├── Titre Beat 1.wav
│   ├── Titre Beat 1_stems.zip      ← Extrait automatiquement
│   ├── Titre Beat 1_artwork.jpg
│   └── Titre Beat 1_metadata.csv   ← BPM, tags, date
│
└── Titre Beat 2/
    └── ...
```

---

## 🎯 Configuration des Variantes

Dans `config.json`, personnalisez vos offres :

```json
"variants": [
    {
        "name": "MP3 Lease",
        "price": "29.99",
        "digital_files": ["mp3"]
    },
    {
        "name": "WAV Lease",
        "price": "49.99",
        "digital_files": ["mp3", "wav"]
    },
    {
        "name": "Premium Lease (Stems)",
        "price": "99.99",
        "digital_files": ["mp3", "wav", "stems"]
    },
    {
        "name": "Unlimited Rights",
        "price": "299.99",
        "digital_files": ["mp3", "wav", "stems"]
    }
]
```

---

## ✅ Checklist de Démarrage

**Pour Scraper BeatStars (Option 1) :**
- [ ] Google Chrome installé
- [ ] Tous les fichiers téléchargés
- [ ] Collection ID récupéré depuis Shopify
- [ ] `config.json` édité avec vos infos
- [ ] Credentials BeatStars configurés
- [ ] Credentials Shopify configurés
- [ ] Double-clic sur BeatStars-Shopify-Tool.exe
- [ ] Option 1 → **Ça marche!** 🎉

**Pour Upload Shopify uniquement (Option 2) :**
- [ ] Tous les fichiers téléchargés
- [ ] Google Chrome installé
- [ ] `login_shopify_chrome.bat` lancé et connexion Shopify effectuée
- [ ] Collection ID récupéré depuis Shopify
- [ ] `config.json` édité avec vos infos
- [ ] Beats déjà téléchargés dans le dossier
- [ ] Double-clic sur BeatStars-Shopify-Tool.exe
- [ ] Option 2 → **Ça marche!** 🎉

**Pour Single Upload :**
- [ ] Tous les fichiers téléchargés
- [ ] Google Chrome installé
- [ ] `login_shopify_chrome.bat` lancé et connexion Shopify effectuée
- [ ] Collection ID récupéré depuis Shopify
- [ ] `config.json` édité avec vos infos
- [ ] Double-clic sur Single-Upload-Tool.exe → **Ça marche!** 🎉

---

## 📝 Historique des Versions

**v3.1** - Réparation de l'upload Digital Downloads (Septembre 2026)
- 🐛 Fix : Shopify a renommé "Digital Downloads" en "Digital Products" et changé toute l'interface (UI par variante au lieu d'un panneau unique) — le code d'upload a été entièrement réécrit pour suivre
- 🔐 Fix : Shopify bloque désormais la page de connexion pour tout navigateur piloté par un script. L'outil pilote maintenant votre **vrai Chrome installé** (profil dédié via `login_shopify_chrome.bat`, connexion manuelle unique) au lieu d'un Chromium embarqué automatisé
- ❌ Retiré : les navigateurs Playwright embarqués (`ms-playwright/`, ~150 MB) ne sont plus nécessaires ni distribués
- ✅ Fix : confirmation réelle de l'upload de chaque fichier (au lieu de supposer un succès dès la fermeture de la fenêtre), + validation de la barre "Unsaved changes"

**v3.0** - Exécutables autonomes (Janvier 2026)
- ✅ Browsers Playwright bundlés (~150 MB)
- ✅ Python inclus dans les .exe
- ✅ Deux outils : Complet et Single upload
- ✅ Meilleure gestion du collection_id
- ✅ Messages d'erreur plus clairs
- ⚠️ Chrome toujours nécessaire pour scraper BeatStars (Selenium)

**v2.3** - Nouvelle authentification Shopify (2026)
- Support client credentials (OAuth 2.0)
- Token auto-refresh (24h)
- Compatible legacy tokens (shpat_)

**v2.2** - Support RAR amélioré
- UnRAR pour archives RAR
- Support ZIP, 7Z, TAR.GZ
- Nettoyage auto des dossiers temporaires

**v2.1** - Compression et vérification
- Compression optimisée stems
- Vérification d'intégrité

**v2.0** - Gestion des sessions
- Persistance sessions BeatStars/Shopify
- Auto-login avec support 2FA
- Détection produits existants

---

## 🆘 Support

Pour toute assistance :
1. ✅ Consultez ce README
2. ✅ Vérifiez la section **Résolution des Problèmes**
3. ✅ Vérifiez que `config.json` est correct
4. ✅ Vérifiez que Chrome est installé (nécessaire pour tout : scraper, upload, single upload)
5. ✅ Pour upload Shopify : avez-vous lancé `login_shopify_chrome.bat` et confirmé la connexion ?

**Problème avec collection_id ?**
→ Section "Résolution des Problèmes" ci-dessus

**Problème avec Chrome ?**
→ Installer Chrome : https://www.google.com/chrome/

---

Développé pour simplifier la gestion de vos productions musicales. 🎵

**Bonne production!** 🚀