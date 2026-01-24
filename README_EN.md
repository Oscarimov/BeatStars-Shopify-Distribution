# BeatStars to Shopify Tool v3.0

## 🎯 Overview

Complete tool to automate the transfer of your music productions from BeatStars to your Shopify store. Handles file downloads (MP3, WAV, STEMS, artwork) and uploads them with different pricing options.

**✨ NEW v3.0**: Standalone executables - no need to install Python or Playwright!

---

## 📦 Package Contents

You have **two tools** to choose from:

### 1. **BeatStars-Shopify-Tool.exe** 
- **Usage**: Download from BeatStars + Upload to Shopify
- **Ideal for**: Batch uploads of multiple beats

### 2. **Single-Upload-Tool.exe**
- **Usage**: Manual upload of a single beat
- **Ideal for**: Quick uploads, tests, beats outside BeatStars

**Both share**:
- ✅ Same `ms-playwright/` folder (browsers included)
- ✅ Same `config.json` file
- ✅ No installation required

---

## 🚀 Quick Setup (2 minutes)

### Step 1: Extraction

**Download all files from this github repository** and keep all files together in the same folder:
```
BeatStars-Shopify-Tool/
├── BeatStars-Shopify-Tool.exe    ← Batch uploads
├── Single-Upload-Tool.exe         ← Manual uploads
├── ms-playwright/                 ← Browsers (DO NOT DELETE!)
├── scripts (you can ignore that unless you are a developper or want to dig into the actual code)
├── config.json                    ← To edit
├── README.md
└── README_EN.md
```

**⚠️ IMPORTANT**: Do not move files individually, keep everything together!

---

### Step 2: Configure config.json

#### A. Get Your Collection ID

**Simple method via Shopify:**
1. Go to **Shopify Admin** → **Products** → **Collections**
2. Click on your collection (e.g., "All Beats")
3. In the browser URL:
   ```
   https://admin.shopify.com/store/your-store/collections/629200158987
                                                           ^^^^^^^^^^^^
   ```
4. **Copy this number** (e.g., `629200158987`)

#### B. Configure Shopify Authentication

**Option 1: Legacy Token (if you already have one)** ✅ Recommended
```json
{
    "store_url": "your-store.myshopify.com",
    "access_token": "shpat_your_existing_token"
}
```

**Option 2: Client Credentials (2026+)** 🆕
1. Shopify Admin → **Settings** → **Apps** → **Develop apps**
2. **Create app** → Give it a name
3. Select these **4 permissions**:
   - ✅ `read_products`
   - ✅ `write_products`
   - ✅ `read_files`
   - ✅ `write_files`
4. **Release** → Copy **Client ID** and **Client Secret**

```json
{
    "store_url": "your-store.myshopify.com",
    "client_id": "123456789",
    "client_secret": "shpcs_abc123..."
}
```

#### C. Edit config.json

Open `config.json` and fill in:

```json
{
    "store_url": "your-store.myshopify.com",
    "access_token": "shpat_your_token",
    "collection_id": "gid://shopify/Collection/629200158987",
    
    "beats_folder": "C:/Users/YourName/Downloads/Beats",
    
    "shopify_login": {
        "email": "your@email.com",
        "password": "your_shopify_password",
        "auto_login": true
    },
    
    "beatstars_login": {
        "email": "your@email.com",
        "password": "your_beatstars_password",
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

**Important points:**
- ⚠️ Replace `"gid://shopify/Collection/xxxxxxxxxxxx"` with your **real** number
- ⚠️ Collection ID format: `"gid://shopify/Collection/629200158987"`
- ⚠️ Use `/` in Windows paths: `C:/Users/...` (not `\`)

---

## 📘 Usage

### Tool #1: BeatStars-Shopify-Tool.exe (Batch uploads)

**Double-click on `BeatStars-Shopify-Tool.exe`**

**Main menu:**
```
1. Download from BeatStars
2. Upload to Shopify
3. Complete workflow (Download + Upload)
4. Display configuration
5. Exit
```

#### Option 1 - BeatStars Download
1. Chrome opens automatically
2. Log in to BeatStars (first time only)
3. Switch to **list view**
4. Scroll to the bottom to load all your beats
5. Press **Enter** in the terminal
6. Files are downloaded automatically

⚠️**Attention point**⚠️ : In ordrer for the download to be as efficient and accurate as possible , you might want to leave your pc and come back when it's done, especially for 20+ beats. In fact, the bot simulates clicks, so using your pc during the download can interefere with the process. You might also want to check your folders to see if some files are missing.

**Downloaded files:**
- MP3 (high quality)
- WAV (if available)
- STEMS (archives extracted automatically)
- Artwork (cover image)
- Metadata (BPM, tags, date)

#### Option 2 - Shopify Upload
1. Playwright browser opens (included in ms-playwright/)
2. Automatic login to Shopify
3. Product creation with variants
4. Upload of downloadable files
5. Attachment of covers

#### Option 3 - Complete Workflow
Does everything at once: BeatStars download → Shopify upload

---

### Tool #2: Single-Upload-Tool.exe (Manual upload)

**Double-click on `Single-Upload-Tool.exe`**

**Interactive dialogs:**
1. 🖼️ Select **cover image** (JPG, PNG, etc.)
2. 🎵 Select **MP3**
3. 🎶 Select **WAV** (optional - Cancel to skip)
4. 📦 Select **STEMS** (optional - Cancel to skip)
5. ✏️ Enter beat **title**
6. 🎼 Enter **BPM** (optional)
7. 🏷️ Enter **tags** (optional, comma-separated)
8. 🚀 Automatic upload to Shopify

**Use it for:**
- Quick tests
- Beats not on BeatStars
- One-off uploads
- Verifying everything works

---

## 🎯 Supported Formats

**Archives:**
- ✅ **ZIP** (built-in)
- ✅ **7Z** (built-in)
- ✅ **RAR** (requires UnRAR - see section below)
- ✅ **TAR.GZ** (built-in)

**Images:**
- ✅ JPG, JPEG, PNG, GIF, WEBP, BMP

**Audio:**
- ✅ MP3, WAV

---

## 🔧 UnRAR Configuration (Optional)

If your STEMS archives are in **RAR** format, you need to install UnRAR:

**Windows:**
1. Download UnRAR: https://www.rarlab.com/rar_add.htm
2. Extract `UnRAR.exe`
3. Create a `tools\` folder next to the .exe files
4. Place `UnRAR.exe` in `tools\unrar.exe`

**Note:** ZIP and 7Z work without UnRAR

---

## 🐛 Troubleshooting

### ❌ "Error: collection_id invalid"

**Cause:** You left the placeholders `xxxxxxxxxxxx`

**Solution:**
1. Go to Shopify Admin → Products → Collections
2. Click on your collection
3. Copy the number in the URL: `collections/629200158987`
4. In config.json, use:
   ```json
   "collection_id": "gid://shopify/Collection/629200158987"
   ```

**INVALID formats:**
```json
"collection_id": "gid://shopify/Collection/xxxxxxxxxxxx"  ❌ Placeholders!
"collection_id": "629200158987"                           ❌ Missing prefix
"collection_id": "All Beats"                              ❌ That's the name!
```

---

### ❌ "Executable doesn't exist" or "Playwright not installed"

**Cause:** `ms-playwright/` folder missing or misplaced

**Solution:**
1. Verify that `ms-playwright/` is **next to** the .exe files
2. If missing, re-download all files from the github in the same folder
3. **NEVER move** files individually

**Correct structure:**
```
📁 Main folder
├── BeatStars-Shopify-Tool.exe     ✅
├── Single-Upload-Tool.exe          ✅
├── 📁 ms-playwright/               ✅ Must be here!
│   └── chromium_headless_shell-*/
└── config.json                     ✅
```

---

### ❌ "Config file not found"

**Cause:** config.json not in the same folder as the .exe files

**Solution:**
Copy `config.json` **next to** the executables

---

### ❌ "Invalid access token"

**If using legacy token (shpat_):**
- Verify it starts with `shpat_`
- Check API permissions in Shopify Admin

**If using client credentials (2026+):**
- Verify the app is **installed** on your store
- Verify all **4 permissions** are checked
- Verify `client_id` and `client_secret`

---

### ❌ "Session expired"

**Solution:** 
Delete these files:
- `beatstars_session.json`
- `shopify_session.json`
- `.shopify_token_cache` (if client credentials)

Then restart the tool → automatic reconnection

---

### ❌ "Beats folder not found"

**Cause:** Path in `beats_folder` is incorrect

**Solution:**
- Windows: `"C:/Users/YourName/Documents/Beats"` (use `/` not `\`)
- OR leave empty: `"beats_folder": ""` → selection dialog at launch

---

## ❓ Frequently Asked Questions

**Do I need to install Python or Playwright?**
❌ No! Everything is included in the executables

**Why is the package 180 MB?**
Chromium browsers are ~150 MB. This is normal (Chrome, VS Code, Discord = 150-300 MB)

**Can I delete the ms-playwright/ folder to save space?**
❌ NO! Both .exe files need it to function

**Can both tools coexist?**
✅ YES! They share the same `ms-playwright/` and `config.json`

**What's the difference between the two .exe files?**
- **BeatStars-Shopify-Tool.exe**: Batch uploads from BeatStars
- **Single-Upload-Tool.exe**: Manual upload of a single beat

**How do I update the tool?**
Download the new version, keep your `config.json`

**Does the tool work offline?**
❌ No, internet connection required

**Can I interrupt the process?**
✅ Yes, with `Ctrl+C`. Already downloaded beats are kept

**Can I share with my team?**
✅ Yes, but everyone needs their own `config.json` with their credentials

---

## 🔐 Security

- ✅ All data stays local on your computer
- ✅ Credentials stored in `config.json` (protect it!)
- ✅ **Never share** your tokens or config
- ✅ Browsers from official sources (Playwright/Microsoft)

**Saved sessions:**
- `beatstars_session.json` - BeatStars session
- `shopify_session.json` - Shopify session
- `.shopify_token_cache` - API token (if client credentials)

---

## 📊 Downloaded Files Structure

After downloading from BeatStars:

```
Beats/
├── Beat Title 1/
│   ├── Beat Title 1.mp3
│   ├── Beat Title 1.wav
│   ├── Beat Title 1_stems.zip      ← Extracted automatically
│   ├── Beat Title 1_artwork.jpg
│   └── Beat Title 1_metadata.csv   ← BPM, tags, date
│
└── Beat Title 2/
    └── ...
```

---

## 🎯 Variant Configuration

In `config.json`, customize your offers:

```json
"variants": [
    {
        "name": "MP3",
        "price": "29.99",
        "digital_files": ["mp3"]
    },
    {
        "name": "WAV + MP3",
        "price": "49.99",
        "digital_files": ["mp3", "wav"]
    },
    {
        "name": "FULL PACKAGE",
        "price": "99.99",
        "digital_files": ["mp3", "wav", "stems"]
    }
]
```

---

## ✅ Getting Started Checklist

- [ ] Download all files from github
- [ ] `ms-playwright/` present next to .exe files
- [ ] Collection ID retrieved from Shopify
- [ ] `config.json` edited with your info
- [ ] Collection ID in correct format: `"gid://shopify/Collection/629200158987"`
- [ ] Shopify credentials configured (token OR client_id/secret)
- [ ] BeatStars credentials configured
- [ ] Double-click on .exe → **It works!** 🎉

---

## 📝 Version History

**v3.0** - Standalone executables (January 2026)
- ✅ No need to install Python or Playwright
- ✅ Chromium browsers included (~150 MB)
- ✅ Two tools: Batch and Single upload
- ✅ Better collection_id handling
- ✅ Clearer error messages

**v2.3** - New Shopify authentication (2026)
- Client credentials support (OAuth 2.0)
- Auto-refresh token (24h)
- Compatible with legacy tokens (shpat_)

**v2.2** - Improved RAR support
- UnRAR for RAR archives
- Support for ZIP, 7Z, TAR.GZ
- Auto cleanup of temporary folders

**v2.1** - Compression and verification
- Optimized stems compression
- Integrity verification

**v2.0** - Session management
- Persistent BeatStars/Shopify sessions
- Auto-login with 2FA support
- Existing product detection

---

## 🆘 Support

For any assistance:
1. ✅ Check this README
2. ✅ Check the **Troubleshooting** section
3. ✅ Verify `config.json` is correct
4. ✅ Verify `ms-playwright/` is present

**Issue with collection_id?**
→ "Troubleshooting" section above

**Issue with Playwright?**
→ Verify `ms-playwright/` is next to the .exe files

---

Developed to simplify your music production management. 🎵

**Happy producing!** 🚀