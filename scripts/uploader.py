"""
Shopify GraphQL Uploader - Version améliorée avec corrections de robustesse
===========================================================================
Compatible avec: single_upload.py, main.py, build_all.py, config.json
Supporte: ms-playwright bundled pour distribution .exe
"""

import time
import os
import sys
import json
import glob  # Import unique
from pathlib import Path
import tempfile
import pandas as pd
import requests
from typing import Dict, List, Optional, Any, Tuple
import mimetypes
from mutagen.mp3 import MP3
import asyncio
import nest_asyncio
import tkinter as tk
from tkinter import filedialog
from functools import wraps
from dataclasses import dataclass

# ============================================================================
# CONFIGURATION BROWSER (Viewport configurable)
# ============================================================================

@dataclass
class BrowserConfig:
    """Configuration centralisée du navigateur - RÉSOUT le problème de fenêtre géante"""
    # Viewport pour mode manuel (fenêtre RAISONNABLE)
    manual_viewport_width: int = 1280
    manual_viewport_height: int = 800
    
    # Viewport pour mode headless (peut être plus grand)
    headless_viewport_width: int = 1920
    headless_viewport_height: int = 1080
    
    # Timeouts (en ms)
    default_timeout: int = 30000
    navigation_timeout: int = 30000
    element_timeout: int = 10000
    short_wait: int = 1000
    medium_wait: int = 2000
    long_wait: int = 5000
    
    # Retry config
    max_retries: int = 3
    retry_base_delay: float = 1.0

# Config globale par défaut
DEFAULT_BROWSER_CONFIG = BrowserConfig()

# ============================================================================
# GESTION PLAYWRIGHT BUNDLED (pour .exe)
# ============================================================================

if getattr(sys, 'frozen', False):
    exe_dir = os.path.dirname(sys.executable)
    browserpath = os.path.join(exe_dir, "ms-playwright")
    
    if os.path.exists(browserpath):
        chromium_found = glob.glob(os.path.join(browserpath, "chromium*"))
        
        if not chromium_found:
            nested_path = os.path.join(browserpath, "ms-playwright")
            if os.path.exists(nested_path):
                chromium_nested = glob.glob(os.path.join(nested_path, "chromium*"))
                if chromium_nested:
                    print(f"⚠️  Detected nested ms-playwright folder (from unzip)")
                    browserpath = nested_path
                    chromium_found = chromium_nested
        
        if chromium_found:
            print(f"✅ Using bundled Playwright browsers: {browserpath}")
            print(f"   Found: {', '.join([os.path.basename(p) for p in chromium_found])}")
        else:
            print(f"⚠️  No Chromium browsers found in {browserpath}")
            browserpath = os.path.join(os.path.expanduser("~"), "AppData", "Local", "ms-playwright")
            print(f"   Trying AppData: {browserpath}")
    else:
        browserpath = os.path.join(os.path.expanduser("~"), "AppData", "Local", "ms-playwright")
        print(f"⚠️  Bundled browsers folder not found, using AppData: {browserpath}")
    
    os.environ['PLAYWRIGHT_BROWSERS_PATH'] = browserpath
    os.environ['PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD'] = '1'

from playwright.async_api import async_playwright, Browser, BrowserContext, Page, Error as PlaywrightError

nest_asyncio.apply()

# ============================================================================
# UTILITAIRES
# ============================================================================

def get_or_create_event_loop() -> asyncio.AbstractEventLoop:
    """Obtient ou crée un event loop de manière sûre et robuste"""
    try:
        loop = asyncio.get_running_loop()
        return loop
    except RuntimeError:
        pass
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Loop is closed")
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def with_retry(max_retries: int = 3, base_delay: float = 1.0, exceptions: tuple = (Exception,)):
    """Décorateur pour retry avec exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        time.sleep(delay)
            raise last_exception
        return wrapper
    return decorator


# ============================================================================
# CLASSE PRINCIPALE
# ============================================================================

class ShopifyGraphQLUploader:
    def __init__(self, config_path: str = "config.json", beats_folder: Optional[Path] = None):
        """
        Initialize the Shopify uploader.
        
        Args:
            config_path: Path to the config JSON file
            beats_folder: Optional override for the beats folder. If provided, skips folder selection.
                         Used by single_upload.py which doesn't need a beats folder.
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        
        # Browser config pour viewport adaptable
        self.browser_config = DEFAULT_BROWSER_CONFIG
        self._is_headless = True  # Track browser mode
        
        debug_mode = self.config.get('debug_mode', False)
        uploader_verbose = self.config.get('uploader_verbose', False)
        digital_verbose = self.config.get('digital_downloads_verbose', False)
        legacy_verbose = self.config.get('verbose', False)
        
        if debug_mode:
            self.verbose = True
            self.digital_downloads_verbose = True
        elif uploader_verbose:
            self.verbose = True
            self.digital_downloads_verbose = digital_verbose
        elif legacy_verbose:
            self.verbose = True
            self.digital_downloads_verbose = digital_verbose
        else:
            self.verbose = False
            self.digital_downloads_verbose = digital_verbose
        
        self.store_url = self.config['store_url'].replace('https://', '').replace('http://', '').rstrip('/')
        self.access_token = self.config.get('access_token', '')
        
        if beats_folder is not None:
            self.download_folder = beats_folder
        else:
            self.download_folder = self._get_beats_folder()
        
        self.apiurl = f"https://{self.store_url}/admin/api/2024-10/graphql.json"
        self.headers = {
            "Content-Type": "application/json",
            "X-Shopify-Access-Token": self.access_token
        }
        
        self.music_category_id = None
        self.publication_ids = {}
        
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        print(f"📁 Source folder: {self.download_folder}")
        print(f"🪐 Store: {self.store_url}")
        print(f"📂 Collection: {self.config['collection_id']}")
    
    def _get_beats_folder(self) -> Path:
        """
        Intelligently determine the beats folder:
        1. Check if 'beats_folder' is declared in config
        2. If yes and exists, use it
        3. If no or doesn't exist, ask user via file dialog
        """
        config_beats_folder = self.config.get('beats_folder')
        
        if config_beats_folder:
            beats_path = Path(config_beats_folder)
            if beats_path.exists() and beats_path.is_dir():
                print(f"✅ Using beats folder from config: {beats_path}")
                return beats_path
            else:
                print(f"⚠️ Beats folder from config doesn't exist: {config_beats_folder}")
        else:
            print("ℹ️ No 'beats_folder' declared in config.json")
        
        print("\n📂 Please select your beats folder...")
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        try:
            selected_folder = filedialog.askdirectory(
                title="Select Beats Folder",
                mustexist=True
            )
            
            if not selected_folder:
                print("❌ No folder selected. Using temp directory as fallback.")
                return Path(tempfile.gettempdir())
            
            beats_path = Path(selected_folder)
            print(f"✅ Selected beats folder: {beats_path}")
            
            save_to_config = input("\n💾 Save this folder to config.json for next time? (y/n): ").strip().lower()
            if save_to_config == 'y':
                self.config['beats_folder'] = str(beats_path)
                with open('config.json', 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
                print("✅ Config updated!")
            
            return beats_path
            
        except (tk.TclError, Exception) as e:
            print(f"⚠️ Error selecting folder: {e}")
            print("Using temp directory as fallback.")
            return Path(tempfile.gettempdir())
        finally:
            try:
                root.destroy()
            except tk.TclError:
                pass
    
    # =========================================================================
    # GESTION BROWSER - VIEWPORT CONFIGURABLE
    # =========================================================================
    
    def _get_viewport(self, headless: bool) -> Dict[str, int]:
        """
        Retourne le viewport approprié selon le mode.
        
        CORRECTION PRINCIPALE: En mode visible (manuel/CAPTCHA), utilise une 
        fenêtre de taille raisonnable au lieu de 1920x1080.
        """
        if headless:
            return {
                'width': self.browser_config.headless_viewport_width,
                'height': self.browser_config.headless_viewport_height
            }
        else:
            # Mode visible = fenêtre RAISONNABLE (1280x800 par défaut)
            return {
                'width': self.browser_config.manual_viewport_width,
                'height': self.browser_config.manual_viewport_height
            }
    
    def _get_browser_args(self) -> List[str]:
        """Arguments anti-détection pour le navigateur"""
        return [
            '--disable-blink-features=AutomationControlled',
            '--disable-dev-shm-usage',
            '--no-sandbox',
            '--disable-setuid-sandbox'
        ]
    
    async def _create_context(self, headless: bool, storage_state: Optional[str] = None) -> BrowserContext:
        """
        Crée un context browser avec les bons paramètres.
        Centralise la création pour éviter la duplication de code.
        """
        viewport = self._get_viewport(headless)
        
        context_kwargs = {
            'viewport': viewport,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'locale': 'fr-FR',
            'timezone_id': 'Europe/Paris'
        }
        
        if storage_state and Path(storage_state).exists():
            context_kwargs['storage_state'] = storage_state
        
        context = await self.browser.new_context(**context_kwargs)
        
        # Script anti-webdriver
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)
        
        return context
    
    async def init_playwright(self, headless: bool = True):
        """Initialize Playwright browser with session restoration
        
        Args:
            headless: If True, browser runs in background. If False, visible window.
        """
        if not self.playwright:
            self._is_headless = headless
            self.playwright = await async_playwright().start()
            
            try:
                self.browser = await self.playwright.chromium.launch(
                    headless=headless,
                    args=self._get_browser_args()
                )
                
                if not headless:
                    print("🖥️  Browser window opened (manual login mode)")
                    
            except PlaywrightError as e:
                print("\n" + "=" * 70)
                print("  ❌ PLAYWRIGHT BROWSER NOT INSTALLED")
                print("=" * 70)
                print("\nPlaywright needs browser files (one-time setup).")
                print("\nDiagnostic:")
                if getattr(sys, 'frozen', False):
                    browser_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', 'NOT SET')
                    print(f"  Browser path: {browser_path}")
                    
                    chromium_dirs = glob.glob(os.path.join(browser_path, "chromium-*"))
                    chromium_dirs += glob.glob(os.path.join(browser_path, "chromium_headless_shell-*"))
                    
                    if chromium_dirs:
                        print(f"  ✅ Found bundled Chromium: {[os.path.basename(d) for d in chromium_dirs]}")
                        print(f"  ⚠️  Chromium found but browser launch failed")
                        print(f"  Error: {str(e)}")
                        print(f"\n  This is likely a compatibility issue, not a missing browser issue.")
                    else:
                        print(f"  ❌ No Chromium installation found in: {browser_path}")
                        print(f"  ⚠️  Expected folder structure:")
                        print(f"     {browser_path}/")
                        print(f"     └── chromium_headless_shell-XXXX/")
                else:
                    print(f"  Error: {str(e)}")
                    
                if getattr(sys, 'frozen', False):
                    chromium_dirs = glob.glob(os.path.join(browser_path, "chromium-*"))
                    chromium_dirs += glob.glob(os.path.join(browser_path, "chromium_headless_shell-*"))
                    
                    if chromium_dirs:
                        print("\n⚠️  BROWSER COMPATIBILITY ISSUE")
                        print("Chromium browsers are present but failed to launch.")
                        print("\nPossible causes:")
                        print("  1. Antivirus blocking browser execution")
                        print("  2. Missing system dependencies")
                        print("  3. Corrupted browser files")
                        print("\nSolutions:")
                        print("  1. Re-extract the complete ZIP file")
                        print("  2. Add exception in your antivirus for this folder")
                        print("  3. Run as administrator (if on work/restricted PC)")
                    else:
                        print("\n⚠️  MISSING BUNDLED BROWSERS")
                        print("\nThe ms-playwright/ folder is missing or incomplete.")
                        print("\nSolutions:")
                        print("  1. Re-extract the COMPLETE ZIP file")
                        print("  2. Ensure ms-playwright/ folder is next to the .exe")
                        print("  3. Do NOT move files individually")
                else:
                    print("\nOption 1 - Run the setup script:")
                    print("  Double-click: setup_playwright.bat")
                    print("\nOption 2 - Run this command:")
                    print("  python -m playwright install chromium")
                    print("\nThen run this program again.")
                print("=" * 70)
                
                if getattr(sys, 'frozen', False):
                    chromium_dirs = glob.glob(os.path.join(browser_path, "chromium-*"))
                    chromium_dirs += glob.glob(os.path.join(browser_path, "chromium_headless_shell-*"))
                    
                    if chromium_dirs:
                        raise Exception(f"Browser launch failed. Check antivirus or re-extract ZIP. Error: {str(e)}")
                    else:
                        raise Exception("Missing bundled browsers. Re-extract the complete ZIP file.")
                else:
                    raise Exception("Playwright browser not installed. Run setup_playwright.bat or: python -m playwright install chromium")
            
            print("🌐 Playwright browser initialized")
            
            # Try to load existing session
            session_file = Path("shopify_session.json")
            if session_file.exists() and not self.config.get('force_fresh_login', False):
                print("🔄 Attempting to restore previous session...")
                if await self.load_browser_session():
                    return
            
            # No saved session or expired - create new context
            self.context = await self._create_context(headless)
            self.page = await self.context.new_page()
    
    async def close_playwright(self):
        """Close Playwright browser proprement"""
        errors = []
        
        if self.context:
            try:
                await self.context.close()
            except PlaywrightError as e:
                errors.append(f"context: {e}")
            finally:
                self.context = None
                self.page = None
        
        if self.browser:
            try:
                await self.browser.close()
            except PlaywrightError as e:
                errors.append(f"browser: {e}")
            finally:
                self.browser = None
        
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                errors.append(f"playwright: {e}")
            finally:
                self.playwright = None
        
        if errors:
            print(f"⚠️  Errors closing Playwright: {', '.join(errors)}")
        else:
            print("🌐 Playwright browser closed")
    
    async def switch_to_visible_browser(self, navigate_to: Optional[str] = None) -> bool:
        """
        Bascule vers un navigateur visible (pour CAPTCHA ou login manuel).
        
        AMÉLIORATION: Utilise le viewport configuré (pas 1920x1080).
        """
        if not self._is_headless:
            return True
        
        print("🔄 Switching to visible browser mode...")
        
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            
            self.context = None
            self.page = None
            self.browser = None
            
            self.browser = await self.playwright.chromium.launch(
                headless=False,
                args=self._get_browser_args()
            )
            
            # Créer le context avec le BON viewport (pas 1920x1080!)
            self.context = await self._create_context(headless=False)
            self.page = await self.context.new_page()
            self._is_headless = False
            
            if navigate_to:
                await self.page.goto(navigate_to, wait_until='domcontentloaded')
                await self.page.wait_for_timeout(self.browser_config.medium_wait)
            
            print("🖥️  Browser window is now visible!")
            return True
            
        except PlaywrightError as e:
            print(f"❌ Error switching browser mode: {e}")
            return False
    
    async def save_browser_session(self):
        """Save browser cookies and storage state (safe JSON)"""
        try:
            path = "shopify_session.json"
            await self.context.storage_state(path=path)

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print("💾 Session saved successfully (sanitized)")
            return True

        except (OSError, json.JSONDecodeError, PlaywrightError) as e:
            print(f"⚠️ Could not save session: {e}")
            return False

    async def load_browser_session(self) -> bool:
        """Load saved session if exists"""
        session_file = Path("shopify_session.json")
        if not session_file.exists():
            return False
        
        try:
            if self.context:
                await self.context.close()
            
            self.context = await self._create_context(
                headless=self._is_headless,
                storage_state="shopify_session.json"
            )
            
            self.page = await self.context.new_page()
            
            test_url = f"https://admin.shopify.com/store/{self.store_url.replace('.myshopify.com', '')}"
            await self.page.goto(test_url, timeout=15000, wait_until='domcontentloaded')
            await self.page.wait_for_timeout(2000)
            
            if await self.is_logged_in():
                print("✅ Session restored from file!")
                return True
            
            print("⚠️ Saved session expired")
            return False
        except (PlaywrightError, OSError) as e:
            print(f"⚠️ Could not load session: {e}")
            return False

    async def is_logged_in(self) -> bool:
        """Verify if the user is properly logged in to Shopify admin"""
        try:
            current_url = self.page.url
            
            if "admin.shopify.com" in current_url and "/store/" in current_url:
                if any(x in current_url.lower() for x in ["/login", "two_factor", "2fa", "authentication"]):
                    return False
                return True
            
            return False
        except (PlaywrightError, AttributeError):
            return False

    async def verify_and_refresh_session(self) -> bool:
        """Verify session is still active, refresh if needed"""
        try:
            if await self.is_logged_in():
                return True
            
            print("\n⚠️ Session expired, trying to restore...")
            if await self.load_browser_session():
                return True
            
            print("\n" + "="*60)
            print("   ⚠️ SESSION EXPIRED - LOGIN REQUIRED")
            print("="*60)
            print("\n   Your Shopify session has expired.")
            
            if self._is_headless:
                print("\n   ⚠️ NOTE: Browser is running in background mode.")
                print("   If you can't see the browser window:")
                print("   1. Check your taskbar for Chromium")
                print("   2. Or restart the tool with auto_login disabled")
            
            print("\n   Please log in again in the browser window.")
            print("\n   ⚠️ Do NOT press Enter until you're on the dashboard!")
            print("="*60 + "\n")
            
            input("👉 Press Enter ONLY when you're on the admin dashboard...")
            
            await self.page.wait_for_timeout(2000)
            
            if await self.is_logged_in():
                await self.save_browser_session()
                return True
            else:
                print("❌ Login verification failed")
                return False
                
        except PlaywrightError as e:
            print(f"❌ Error verifying session: {e}")
            return False
    
    async def login_to_shopify_async(self):
        """
        Semi-automatic login with Playwright
        - Avoids passkey button
        - Handles CAPTCHA
        - Fills email and password automatically
        - Pauses for 2FA
        """
        login_config = self.config.get('shopify_login', {})
        email = login_config.get('email', '')
        password = login_config.get('password', '')
        auto_login = login_config.get('auto_login', False)
        show_browser = login_config.get('show_browser', False)
        
        needs_manual_login = not auto_login or not email or not password
        use_visible_browser = needs_manual_login or show_browser
        
        # Initialize browser in appropriate mode
        # Si visible, utilise le viewport RAISONNABLE (pas 1920x1080)
        await self.init_playwright(headless=not use_visible_browser)
        
        if self.config.get('force_fresh_login', False):
            session_file = Path("shopify_session.json")
            if session_file.exists():
                session_file.unlink()
                print("🗑️ Cleared saved session (force_fresh_login=true)")
        
        login_url = f"https://admin.shopify.com/store/{self.store_url.replace('.myshopify.com', '')}"
        
        try:
            await self.page.goto(login_url, timeout=30000)
            print(f"🌐 Navigating to: {login_url}")
            await self.page.wait_for_timeout(3000)
            
            if await self.is_logged_in():
                print("✅ Already logged in!")
                await self.save_browser_session()
                return
            
            if not auto_login or not email or not password:
                print("\n⚠️ Auto-login disabled or credentials missing in config")
                print("💡 Add this to your config.json to enable auto-login:")
                print("""
    "shopify_login": {
        "email": "your-email@example.com",
        "password": "your-password",
        "auto_login": true
    }
                """)
                print("\n⚠️ IMPORTANT: Complete the ENTIRE login process including 2FA")
                print("   Do NOT press Enter until you see the Shopify admin dashboard!")
                print("   URL should be like: https://admin.shopify.com/store/YOUR-STORE/...\n")
                input("👉 Press Enter ONLY when you're on the admin dashboard...")
                
                await self.page.wait_for_timeout(2000)
                if not await self.is_logged_in():
                    print("❌ Login verification failed. Please try again.")
                    print(f"   Current URL: {self.page.url}")
                    input("👉 Complete the login and press Enter when ready...")
                
                await self.save_browser_session()
                return
            
            print("🤖 Starting semi-automatic login...\n")
            
            # === STEP 1: Enter email ===
            print("📧 Step 1/3: Entering email")
            try:
                email_input = await self.page.wait_for_selector(
                    "input[type='email'], input[name='account[email]']",
                    timeout=10000
                )
                await email_input.fill(email)
                print(f"   ✓ Email entered: {email}")
                await self.page.wait_for_timeout(1500)
                
                try:
                    clicked = await self.page.evaluate("""
                        () => {
                            const buttons = Array.from(document.querySelectorAll('button'));
                            const validButton = buttons.find(btn => {
                                const text = btn.textContent.toLowerCase();
                                return (
                                    !text.includes('clé') &&
                                    !text.includes('passkey') &&
                                    !text.includes('access key') &&
                                    (text.includes('continue') || text.includes('continuer') || 
                                     text.includes('utiliser') && text.includes('e-mail') ||
                                     btn.type === 'submit')
                                );
                            });
                            if (validButton) {
                                validButton.click();
                                return true;
                            }
                            return false;
                        }
                    """)
                    
                    if clicked:
                        print("   ✓ Clicked Continue button")
                    else:
                        await email_input.press('Enter')
                        print("   ✓ Pressed Enter")
                except PlaywrightError:
                    await email_input.press('Enter')
                    print("   ✓ Pressed Enter")
                
                await self.page.wait_for_timeout(3000)
                
                if await self.check_for_captcha():
                    if not await self.is_logged_in():
                        print("⚠️ Please complete the rest of the login process")
                        input("👉 Press Enter when on the admin dashboard...")
                    await self.save_browser_session()
                    return
                
            except PlaywrightError as e:
                print(f"❌ Could not find email field: {e}")
                input("Please complete login manually and press Enter when on the admin dashboard...")
                await self.save_browser_session()
                return
            
            # === STEP 2: Enter password ===
            print("\n🔑 Step 2/3: Entering password")
            try:
                password_input = await self.page.wait_for_selector(
                    "input[type='password'], input[name='account[password]']",
                    timeout=10000
                )
                await password_input.fill(password)
                print("   ✓ Password entered")
                await self.page.wait_for_timeout(1500)
                
                try:
                    login_button = await self.page.wait_for_selector(
                        "button[type='submit'], button:has-text('Se connecter'), button:has-text('Log in')",
                        timeout=3000
                    )
                    await login_button.click()
                    print("   ✓ Clicked Login button")
                except PlaywrightError:
                    await password_input.press('Enter')
                    print("   ✓ Pressed Enter")
                
                await self.page.wait_for_timeout(4000)
                
                if await self.check_for_captcha():
                    if not await self.is_logged_in():
                        print("⚠️ Please complete the rest of the login process")
                        input("👉 Press Enter when on the admin dashboard...")
                    await self.save_browser_session()
                    return
                
            except PlaywrightError as e:
                print(f"❌ Could not find password field: {e}")
                input("Please complete login manually and press Enter when on the admin dashboard...")
                await self.save_browser_session()
                return
            
            # === STEP 3: Check for 2FA ===
            print("\n🔐 Step 3/3: Checking for 2FA...")
            await self.page.wait_for_timeout(2000)
            
            if await self.is_logged_in():
                print("   ✓ Login successful - no 2FA required!")
            else:
                current_url = self.page.url.lower()
                
                requires_2fa = any([
                    "two_factor" in current_url,
                    "2fa" in current_url,
                    "authentication" in current_url,
                    "verify" in current_url
                ])
                
                if requires_2fa or not await self.is_logged_in():
                    print("\n" + "="*60)
                    print("   🔐 TWO-FACTOR AUTHENTICATION REQUIRED")
                    print("="*60)
                    print("\n   Please COMPLETE the 2FA process in the browser:")
                    print("   1. Enter your 2FA code")
                    print("   2. Wait until you see the Shopify admin dashboard")
                    print("   3. URL should look like:")
                    print("      https://admin.shopify.com/store/YOUR-STORE/...")
                    print("\n   ⚠️ Do NOT press Enter until you see the dashboard!")
                    print("="*60 + "\n")
                    
                    input("👉 Press Enter ONLY when you're on the admin dashboard...")
                    
                    await self.page.wait_for_timeout(2000)
                    if not await self.is_logged_in():
                        print("\n❌ Warning: Login verification failed")
                        print(f"   Current URL: {self.page.url}")
                        input("👉 Please ensure you're logged in and press Enter...")
            
            print("💾 Saving session...")
            await self.save_browser_session()
            
            print("\n✅ Login completed!\n")
            
        except PlaywrightError as e:
            print(f"\n❌ Login error: {e}")
            print("\n⚠️ Please complete login manually")
            input("👉 Press Enter when you're on the admin dashboard...")
            await self.save_browser_session()
    
    async def check_for_captcha(self) -> bool:
        """Check if CAPTCHA appeared and switch to visible browser if needed"""
        try:
            await self.page.wait_for_timeout(2000)
            
            page_content = await self.page.content()
            page_content_lower = page_content.lower()
            
            captcha_indicators = [
                'captcha',
                'recaptcha',
                'hcaptcha',
                'challenge',
                'verify you are human',
                'unusual activity'
            ]
            
            if any(indicator in page_content_lower for indicator in captcha_indicators):
                print("\n" + "="*60)
                print("   🤖 CAPTCHA DETECTED")
                print("="*60)
                print("\n   Shopify has detected automation and requires verification.")
                
                current_url = self.page.url
                
                # Si en mode headless, basculer vers visible avec fenêtre raisonnable
                if self._is_headless:
                    print("   🔄 Switching to visible browser mode...")
                    print("="*60 + "\n")
                    
                    store_handle = self.store_url.replace('.myshopify.com', '')
                    login_url = f"https://admin.shopify.com/store/{store_handle}"
                    
                    if await self.switch_to_visible_browser(navigate_to=login_url):
                        print(f"🌐 Navigated to: {login_url}")
                
                print("="*60 + "\n")
                print("   Please solve the CAPTCHA in the browser window.")
                print("="*60 + "\n")
                
                input("👉 Press Enter once you've solved the CAPTCHA...")
                
                await self.page.wait_for_timeout(2000)
                return True
            
            return False
            
        except PlaywrightError as e:
            print(f"⚠️ Error checking CAPTCHA: {e}")
            return False
    
    def login_to_shopify(self):
        """Synchronous wrapper for login"""
        loop = get_or_create_event_loop()
        return loop.run_until_complete(self.login_to_shopify_async())

    async def verify_digital_downloads_async(self, product_id: str, product_title: str, expected_variants: dict, beat_folder: Path) -> dict:
        """Verify that all files are properly attached to Digital Downloads variants"""
        try:
            if not await self.verify_and_refresh_session():
                return {"status": "error", "message": "Could not establish session"}
            
            page = self.page
            product_url = f"https://admin.shopify.com/store/{self.store_url.replace('.myshopify.com', '')}/products/{product_id.split('/')[-1]}"
            
            try:
                await page.goto(product_url, timeout=30000, wait_until='domcontentloaded')
            except PlaywrightError as nav_error:
                if any(x in page.url.lower() for x in ["login", "two_factor", "authentication"]):
                    if not await self.verify_and_refresh_session():
                        return {"status": "error", "message": "Session expired"}
                    await page.goto(product_url, timeout=30000, wait_until='domcontentloaded')
                else:
                    raise nav_error
            
            await page.wait_for_timeout(2000)
            
            try:
                more_actions = page.locator("button:has-text('More actions')").first
                await more_actions.wait_for(state="visible", timeout=10000)
                await more_actions.click()
                await page.wait_for_timeout(1000)
                
                digital_file_link = page.locator("a:has-text('Add digital file')").first
                await digital_file_link.wait_for(state="visible", timeout=10000)
                await digital_file_link.click()
            except PlaywrightError as e:
                return {"status": "error", "message": f"Could not open Digital Downloads: {e}"}
            
            await page.wait_for_timeout(5000)
            
            app_frame = None
            try:
                app_frame = page.frame(name="app-iframe")
            except PlaywrightError:
                pass
            
            if not app_frame:
                frames = page.frames
                for frame in frames:
                    try:
                        if "delivery.shopifyapps.com" in frame.url or "Digital Downloads" in await frame.title():
                            app_frame = frame
                            break
                    except PlaywrightError:
                        continue
            
            if not app_frame:
                app_frame = page
            
            await page.wait_for_timeout(3000)
            
            results = {}
            has_any_issue = False
            
            for variant in expected_variants:
                variant_name = variant["type"]
                expected_files = variant["files"]
                
                file_extensions = [Path(f).suffix.lower() for f in expected_files]
                unique_extensions = list(set(file_extensions))
                
                if len(unique_extensions) == 1:
                    expected_display = f"{len(expected_files)} {unique_extensions[0]} file(s)"
                else:
                    expected_display = f"{len(expected_files)} file(s) ({', '.join(unique_extensions)})"
                
                missing_local = []
                for file_path in expected_files:
                    if not Path(file_path).exists():
                        missing_local.append(Path(file_path).name)
                
                if missing_local:
                    results[variant_name] = {
                        "expected": expected_display,
                        "status": "error",
                        "message": f"Local files missing: {', '.join(missing_local)}"
                    }
                    has_any_issue = True
                else:
                    results[variant_name] = {
                        "expected": expected_display,
                        "status": "ok",
                        "message": f"{len(expected_files)} file(s) configured"
                    }
            
            try:
                file_inputs = await app_frame.locator('input[type="file"]').all()
                
                uploaded_count = 0
                for file_input in file_inputs:
                    try:
                        parent = await file_input.locator('xpath=ancestor::div[contains(@class, "Polaris") or contains(@class, "field")]').first.inner_text()
                        
                        if any(ext in parent.lower() for ext in ['.mp3', '.wav', '.zip', '.rar', 'mb', 'gb', 'ko']):
                            uploaded_count += 1
                    except PlaywrightError:
                        pass
                
                total_expected = len(expected_variants)
                if uploaded_count == 0 and total_expected > 0:
                    for variant_key in results.keys():
                        if results[variant_key]["status"] == "ok":
                            results[variant_key]["status"] = "warning"
                            results[variant_key]["message"] = "Could not verify upload - may need re-upload"
                            has_any_issue = True
                
            except PlaywrightError:
                pass
            
            try:
                products_url = f"https://admin.shopify.com/store/{self.store_url.replace('.myshopify.com', '')}/products"
                await page.goto(products_url, timeout=15000, wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)
            except PlaywrightError:
                pass
            
            return {"status": "success", "results": results, "has_issues": has_any_issue}
            
        except PlaywrightError as e:
            return {"status": "error", "message": str(e)}
    
    async def verify_all_digital_downloads_async(self) -> dict:
        """Verify all products have correct Digital Downloads files attached"""
        json_file = Path("digital_downloads_mapping.json")
        if not json_file.exists():
            return {"status": "error", "message": "No mapping file found"}
        
        with open(json_file, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        
        print("\n" + "="*60)
        print("🔍 VERIFICATION: Checking Digital Downloads Configuration")
        print("="*60 + "\n")
        
        verification_results = []
        
        for idx, product in enumerate(mappings, 1):
            product_id = product["product_id"]
            product_title = product["product_title"]
            beat_folder = Path(product["folder"])
            variants = product.get("variants", [])
            
            print(f"📋 {idx}/{len(mappings)}: {product_title}")
            
            result = await self.verify_digital_downloads_async(product_id, product_title, variants, beat_folder)
            
            if result["status"] == "success":
                results = result.get("results", {})
                has_issues = result.get("has_issues", False)
                has_errors = any(r["status"] == "error" for r in results.values())
                has_warnings = any(r["status"] == "warning" for r in results.values())
                
                if has_errors:
                    print(f"   ❌ Issues found:")
                    for variant_key, data in results.items():
                        if data["status"] == "error":
                            print(f"      - {variant_key}: {data['message']}")
                    verification_results.append({
                        "product": product_title,
                        "product_id": product_id,
                        "beat_folder": beat_folder,
                        "status": "error",
                        "details": results
                    })
                elif has_warnings:
                    print(f"   ⚠️ Warnings:")
                    for variant_key, data in results.items():
                        if data["status"] == "warning":
                            print(f"      - {variant_key}: {data['message']}")
                    verification_results.append({
                        "product": product_title,
                        "product_id": product_id,
                        "beat_folder": beat_folder,
                        "status": "warning",
                        "details": results
                    })
                else:
                    print(f"   ✅ Configuration verified:")
                    for variant_key, data in results.items():
                        print(f"      - {variant_key}: {data['expected']}")
                    verification_results.append({
                        "product": product_title,
                        "product_id": product_id,
                        "beat_folder": beat_folder,
                        "status": "ok",
                        "details": results
                    })
            else:
                print(f"   ❌ Verification failed: {result.get('message', 'Unknown error')}")
                verification_results.append({
                    "product": product_title,
                    "product_id": product_id,
                    "beat_folder": beat_folder,
                    "status": "error",
                    "message": result.get("message")
                })
            
            await self.page.wait_for_timeout(1000)
        
        print("\n" + "="*60)
        print("📊 VERIFICATION SUMMARY")
        print("="*60)
        
        ok_count = sum(1 for r in verification_results if r["status"] == "ok")
        warning_count = sum(1 for r in verification_results if r["status"] == "warning")
        error_count = sum(1 for r in verification_results if r["status"] == "error")
        
        if ok_count == len(verification_results):
            print(f"   ✅ All {ok_count} product(s) configured correctly!")
        else:
            print(f"   ✅ OK: {ok_count}")
            if warning_count > 0:
                print(f"   ⚠️ Warnings: {warning_count}")
            if error_count > 0:
                print(f"   ❌ Errors: {error_count}")
        
        print("\n   ℹ️  Note: This checks file configuration.")
        print("   ℹ️  Large files may still be processing on Shopify servers.")
        if warning_count > 0 or error_count > 0:
            print("   ℹ️  Products with issues will be automatically re-uploaded.")
        print("="*60 + "\n")
        
        return {
            "total": len(verification_results),
            "ok": ok_count,
            "warnings": warning_count,
            "errors": error_count,
            "results": verification_results
        }
    
    def verify_all_digital_downloads(self):
        """Synchronous wrapper for verification"""
        loop = get_or_create_event_loop()
        return loop.run_until_complete(self.verify_all_digital_downloads_async())

    async def upload_files_to_digital_downloads_async(self, product_id: str, product_title: str, beat_folder: Path, only_large_files: bool = False):
        """Upload files to Digital Downloads using existing Playwright session"""
        verbose = self.config.get('digital_downloads_verbose', False)
        
        try:
            if not await self.verify_and_refresh_session():
                print("❌ Could not establish valid session")
                return False
            
            page = self.page
            product_url = f"https://admin.shopify.com/store/{self.store_url.replace('.myshopify.com', '')}/products/{product_id.split('/')[-1]}"
            
            if verbose:
                print(f"🌐 Navigating to product page...")
            
            try:
                await page.goto(product_url, timeout=30000, wait_until='domcontentloaded')
            except PlaywrightError as nav_error:
                if any(x in page.url.lower() for x in ["login", "two_factor", "authentication"]):
                    if not await self.verify_and_refresh_session():
                        return False
                    await page.goto(product_url, timeout=30000, wait_until='domcontentloaded')
                else:
                    raise nav_error
            
            await page.wait_for_timeout(3000)
            
            if "products/" not in page.url:
                print(f"❌ Not on product page")
                return False
            
            try:
                more_actions = page.locator("button:has-text('More actions')").first
                await more_actions.wait_for(state="visible", timeout=10000)
                await more_actions.click()
                await page.wait_for_timeout(1000)
                
                digital_file_link = page.locator("a:has-text('Add digital file')").first
                await digital_file_link.wait_for(state="visible", timeout=10000)
                await digital_file_link.click()
            except PlaywrightError as e:
                print(f"❌ Could not open Digital Downloads: {e}")
                return False
            
            await page.wait_for_timeout(5000)
            
            app_frame = None
            try:
                app_frame = page.frame(name="app-iframe")
            except PlaywrightError:
                pass
            
            if not app_frame:
                frames = page.frames
                for frame in frames:
                    try:
                        if "delivery.shopifyapps.com" in frame.url or "Digital Downloads" in await frame.title():
                            app_frame = frame
                            break
                    except PlaywrightError:
                        continue
            
            if not app_frame:
                app_frame = page
            
            await page.wait_for_timeout(4000)
            
            file_inputs = await app_frame.locator('input[type="file"]').all()
            
            if len(file_inputs) == 0:
                print("❌ No file inputs found")
                return False
            
            if verbose:
                print(f"   Found {len(file_inputs)} file input(s)")
            
            variant_inputs = {}
            config_variant_names = [v["name"] for v in self.config["variants"]]
            
            for idx, file_input in enumerate(file_inputs):
                try:
                    input_id = await file_input.get_attribute("id")
                    label_text = None
                    
                    if input_id:
                        try:
                            label = app_frame.locator(f'label[for="{input_id}"]').first
                            if await label.count() > 0:
                                label_text = await label.inner_text()
                        except PlaywrightError:
                            pass
                    
                    if not label_text:
                        try:
                            parent = await file_input.evaluate('el => el.parentElement.textContent')
                            if parent:
                                label_text = parent[:100]
                        except PlaywrightError:
                            pass
                    
                    if label_text:
                        label_lower = label_text.lower()
                        
                        for variant_name in config_variant_names:
                            variant_lower = variant_name.lower()
                            key_words = [w.strip() for w in variant_lower.replace('+', ' ').split() if len(w.strip()) > 2]
                            
                            if all(word in label_lower for word in key_words):
                                variant_inputs[variant_name] = file_input
                                break
                    
                except PlaywrightError as e:
                    if verbose:
                        print(f"   ⚠️ Error processing input: {e}")
                    continue
            
            if not variant_inputs:
                print("❌ Could not map file inputs")
                return False
            
            uploaded_count = 0
            
            for variant_config in self.config["variants"]:
                variant_name = variant_config["name"]
                
                target_input = variant_inputs.get(variant_name)
                
                if not target_input:
                    if verbose:
                        print(f"   ⚠️ No input found for variant '{variant_name}'")
                    continue
                
                files_to_upload = []
                
                for file_type in variant_config.get("digital_files", []):
                    pattern = self.config["file_patterns"].get(file_type)
                    if pattern:
                        matches = glob.glob(str(beat_folder / pattern))
                        if not matches:
                            pattern_lower = pattern.replace('_MP3', '_mp3').replace('_WAV', '_wav').replace('_STEMS', '_stems').replace('_Stems', '_stems')
                            matches = glob.glob(str(beat_folder / pattern_lower))
                        for file_path in matches:
                            files_to_upload.append(file_path)
                
                if not files_to_upload:
                    for file_type in variant_config.get("digital_files", []):
                        base_pattern = self.config["file_patterns"].get(file_type, f"*{file_type}*")
                        
                        patterns_to_try = [
                            base_pattern,
                            base_pattern.lower(),
                            f"*.{file_type}",
                            f"*_{file_type}.*",
                            f"*_{file_type.upper()}.*",
                            f"*_{file_type.lower()}.*"
                        ]
                        
                        if file_type.lower() in ['stems', 'stem']:
                            patterns_to_try.extend(["*.rar", "*.zip", "*stems*.rar", "*stems*.zip"])
                        
                        for pattern in patterns_to_try:
                            matches = glob.glob(str(beat_folder / pattern))
                            if matches:
                                files_to_upload.extend(matches)
                                if verbose:
                                    print(f"     🔍 Fallback: found {len(matches)} {file_type} file(s) with pattern {pattern}")
                                break
                        
                        if files_to_upload:
                            break
                
                if not files_to_upload:
                    continue
                
                if verbose:
                    print(f"\n📂 Uploading to '{variant_config['name']}':")
                    for f in files_to_upload:
                        file_size_mb = os.path.getsize(f) / (1024 * 1024)
                        print(f"   - {Path(f).name} ({file_size_mb:.1f} MB)")
                
                try:
                    await target_input.set_input_files(files_to_upload)
                    uploaded_count += 1
                except PlaywrightError as e:
                    print(f"   ❌ Upload failed: {e}")
                    continue
            
            if uploaded_count == 0:
                if verbose:
                    print("   ℹ️  No files to upload")
                return True
            
            if verbose:
                print(f"   ⏳ Waiting for uploads to complete...")
            
            async def wait_for_uploads_complete():
                await page.wait_for_timeout(20000)
                
                max_attempts = 30
                attempt = 0
                
                while attempt < max_attempts:
                    attempt += 1
                    
                    save_clicked = False
                    save_selectors = [
                        'button:has-text("Save")',
                        'button:has-text("Enregistrer")',
                        'button:has-text("Done")',
                        'button[type="submit"]'
                    ]
                    
                    for selector in save_selectors:
                        try:
                            if app_frame != page:
                                btn = app_frame.locator(selector).first
                                if await btn.count() > 0 and await btn.is_visible():
                                    await btn.click(timeout=3000)
                                    save_clicked = True
                                    break
                            
                            btn = page.locator(selector).first
                            if await btn.count() > 0 and await btn.is_visible():
                                await btn.click(timeout=3000)
                                save_clicked = True
                                break
                        except PlaywrightError:
                            continue
                    
                    if not save_clicked:
                        if verbose:
                            print(f"   ⚠️ Could not find Save button")
                        return False
                    
                    await page.wait_for_timeout(2000)
                    
                    popup_found = False
                    
                    popup_selectors = [
                        '[role="dialog"]',
                        '.Polaris-Modal-Dialog',
                        'div[class*="Modal"]'
                    ]
                    
                    for popup_selector in popup_selectors:
                        try:
                            popups = await page.locator(popup_selector).all()
                            
                            for popup in popups:
                                try:
                                    if await popup.is_visible():
                                        popup_text = await popup.inner_text()
                                        popup_text_lower = popup_text.lower()
                                        
                                        if any(word in popup_text_lower for word in ['uploading', 'upload', 'téléchargement', 'en cours']):
                                            popup_found = True
                                            
                                            if verbose:
                                                print(f"   ⏳ Still uploading... (attempt {attempt})")
                                            
                                            ok_btn = popup.locator('button:has-text("OK"), button:has-text("Ok")').first
                                            if await ok_btn.count() > 0:
                                                await ok_btn.click()
                                            else:
                                                await page.keyboard.press('Escape')
                                            
                                            await page.wait_for_timeout(500)
                                            break
                                except PlaywrightError:
                                    continue
                            
                            if popup_found:
                                break
                        except PlaywrightError:
                            continue
                    
                    if not popup_found:
                        if verbose:
                            print(f"   ✅ Uploads complete!")
                        return True
                    
                    await page.wait_for_timeout(10000)
                
                print(f"   ⚠️ Timeout after {attempt} attempts")
                return False
            
            upload_success = await wait_for_uploads_complete()
            
            if not upload_success:
                print("⚠️ Upload may not be complete")
                return False
            
            if verbose:
                print(f"   💾 Waiting for save to complete...")
            else:
                print(f"   💾 Saving files...")
            
            try:
                back_button_selector = 'button#dynamic-back-button[role="link"]'
                max_save_wait = 600
                elapsed = 0
                save_verified = False
                
                while elapsed < max_save_wait:
                    try:
                        back_button = page.locator(back_button_selector).first
                        if await back_button.count() > 0:
                            is_visible = await back_button.is_visible()
                            is_enabled = await back_button.is_enabled()
                            
                            if is_visible and is_enabled:
                                save_verified = True
                                if verbose:
                                    print(f"   ✅ Save complete! Back button available after {elapsed}s")
                                else:
                                    print(f"   ✅ Save complete!")
                                break
                    except PlaywrightError:
                        pass
                    
                    if elapsed % 30 == 0 and elapsed > 0:
                        if verbose:
                            print(f"   ⏳ Still saving... ({elapsed}s / {max_save_wait}s)")
                        else:
                            print(f"   ⏳ Still saving... ({elapsed}s)")
                    
                    await page.wait_for_timeout(1000)
                    elapsed += 1
                
                if not save_verified:
                    print(f"   ⚠️ Warning: Save verification timeout after {elapsed}s")
                    print(f"   ⚠️ Files may still be processing")
                
            except PlaywrightError as e:
                if verbose:
                    print(f"   ⚠️ Error during save verification: {e}")
            
            await page.wait_for_timeout(3000)
            
            if verbose:
                print(f"   🔙 Returning to products page...")
            
            try:
                products_url = f"https://admin.shopify.com/store/{self.store_url.replace('.myshopify.com', '')}/products"
                await page.goto(products_url, timeout=15000, wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)
            except PlaywrightError as e:
                if verbose:
                    print(f"   ⚠️ Could not navigate back to products: {e}")
            
            print(f"   ✅ Digital downloads configured")
            return True
            
        except PlaywrightError as e:
            print(f"❌ Error: {e}")
            if verbose:
                import traceback
                traceback.print_exc()
            return False

    def upload_files_to_digital_downloads(self, product_id: str, product_title: str, beat_folder: Path, only_large_files: bool = False):
        """Synchronous wrapper for upload"""
        loop = get_or_create_event_loop()
        return loop.run_until_complete(
            self.upload_files_to_digital_downloads_async(product_id, product_title, beat_folder, only_large_files)
        )

    def get_file_path_by_type(self, beat_folder: Path, file_type: str) -> Optional[Path]:
        """Get file path based on configured pattern"""
        pattern = self.config.get('file_patterns', {}).get(file_type)
        if not pattern:
            return None
        
        files = list(beat_folder.glob(pattern))
        
        if not files:
            patterns_to_try = [
                f"*_{file_type.upper()}.*",
                f"*_{file_type.lower()}.*",
                f"*.{file_type}",
                f"*{file_type}*"
            ]
            
            if file_type.lower() in ['stems', 'stem']:
                patterns_to_try.extend(["*.rar", "*.zip", "*stems*.rar", "*stems*.zip"])
            
            for fallback_pattern in patterns_to_try:
                files = list(beat_folder.glob(fallback_pattern))
                if files:
                    break
        
        return files[0] if files else None

    def find_variant_config_by_title(self, variant_title: str) -> Optional[dict]:
        """Find variant configuration by matching title"""
        variant_title_lower = variant_title.lower().strip()
        
        for variant in self.config['variants']:
            variant_name_lower = variant['name'].lower().strip()
            
            if variant_title_lower == variant_name_lower:
                return variant
            
            if variant_name_lower in variant_title_lower:
                return variant
        
        return None
    
    def graphql_request(self, query: str, variables: dict = None) -> dict:
        """Make a GraphQL request with automatic retry and token refresh"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        try:
            response = requests.post(self.apiurl, json=payload, headers=self.headers, timeout=30)
        except requests.RequestException as e:
            print(f"❌ Network error: {e}")
            return None
        
        if response.status_code == 429:
            wait_time = int(response.headers.get('Retry-After', 2))
            print(f"⏳ Rate limited, waiting {wait_time} seconds...")
            time.sleep(wait_time)
            return self.graphql_request(query, variables)
        
        if response.status_code != 200:
            print(f"❌ API Error {response.status_code}: {response.text}")
            
            if response.status_code == 401 and self.config.get('client_id'):
                print("🔄 Token expiré. Auto-refresh...")
                client_id = self.config['client_id']
                client_secret = self.config['client_secret']
                oauth_url = f"https://{self.store_url}/admin/oauth/access_token"
                body = {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials"
                }
                try:
                    resp_oauth = requests.post(oauth_url, json=body, timeout=10)
                    if resp_oauth.status_code == 200:
                        new_token = resp_oauth.json().get('access_token')
                        if new_token:
                            self.access_token = new_token
                            self.headers['X-Shopify-Access-Token'] = new_token
                            print(f"✅ Nouveau token obtenu: {new_token[:20]}...")
                            
                            self.config['access_token'] = new_token
                            config_file = "config.json"
                            with open(config_file, 'w', encoding='utf-8') as f:
                                json.dump(self.config, f, indent=2, ensure_ascii=False)
                            print("💾 Token mis à jour dans config.json")
                            
                            return self.graphql_request(query, variables)
                        else:
                            print("❌ Aucun nouveau token dans la réponse OAuth")
                    else:
                        print(f"❌ Échec refresh token: {resp_oauth.status_code} - {resp_oauth.text}")
                except requests.RequestException as e:
                    print(f"❌ OAuth request failed: {e}")
            
            return None
        
        data = response.json()
        if "errors" in data and data["errors"]:
            print(f"⚠️ GraphQL Errors: {json.dumps(data['errors'], indent=2)}")
        
        return data

    
    def get_music_category_id(self) -> Optional[str]:
        if self.music_category_id:
            return self.music_category_id
        
        query = """
        query {
            taxonomy {
                categories(first: 250, search: "Music") {
                    edges {
                        node {
                            id
                            name
                            fullName
                            isLeaf
                        }
                    }
                }
            }
        }
        """
        
        result = self.graphql_request(query)
        
        if result and result.get("data", {}).get("taxonomy", {}).get("categories", {}).get("edges"):
            for edge in result["data"]["taxonomy"]["categories"]["edges"]:
                node = edge["node"]
                if "Digital Music Downloads" in node.get("fullName", "") and node.get("isLeaf", False):
                    self.music_category_id = node["id"]
                    return self.music_category_id
        
        default_category_id = self.config.get('default_category_id')
        if default_category_id:
            self.music_category_id = default_category_id
            return self.music_category_id
        
        return None
    
    def ensure_metafield_definitions(self):
        definitions = [
            {
                "name": "Audio Preview",
                "namespace": "custom",
                "key": "audio_preview",
                "type": "file_reference",
                "description": "MP3 preview file for the beat"
            },
            {
                "name": "BPM",
                "namespace": "custom",
                "key": "bpm",
                "type": "number_integer",
                "description": "Beats per minute"
            },
            {
                "name": "Duration",
                "namespace": "custom",
                "key": "duration",
                "type": "single_line_text_field",
                "description": "Track duration (e.g., 3:45)"
            },
            {
                "name": "Tags",
                "namespace": "custom",
                "key": "tags",
                "type": "list.single_line_text_field",
                "description": "Genre and style tags"
            }
        ]
        
        for definition in definitions:
            query = """
            mutation CreateMetafieldDefinition($definition: MetafieldDefinitionInput!) {
                metafieldDefinitionCreate(definition: $definition) {
                    createdDefinition {
                        id
                        name
                    }
                    userErrors {
                        field
                        message
                    }
                }
            }
            """
            
            self.graphql_request(query, {
                "definition": {
                    "name": definition["name"],
                    "namespace": definition["namespace"],
                    "key": definition["key"],
                    "type": definition["type"],
                    "description": definition["description"],
                    "ownerType": "PRODUCT"
                }
            })
    
    def check_product_exists(self, title: str) -> Optional[str]:
        query = """
        query checkProduct($first: Int!, $query: String!) {
            products(first: $first, query: $query) {
                edges {
                    node {
                        id
                        title
                        handle
                        status
                    }
                }
            }
        }
        """
        
        search_query = f'title:"{title}"'
        result = self.graphql_request(query, {
            "first": 5,
            "query": search_query
        })
        
        if result and result.get("data", {}).get("products", {}).get("edges"):
            for edge in result["data"]["products"]["edges"]:
                product = edge["node"]
                if product["title"].lower() == title.lower():
                    return product["id"]
        
        return None
    
    def get_sales_channel_publications(self) -> Dict[str, str]:
        if self.publication_ids:
            return self.publication_ids
        
        query = """
        query {
            publications(first: 20) {
                edges {
                    node {
                        id
                        name
                        catalog {
                            id
                            title
                        }
                    }
                }
            }
        }
        """
        
        result = self.graphql_request(query)
        
        if result and result.get("data", {}).get("publications", {}).get("edges"):
            for edge in result["data"]["publications"]["edges"]:
                node = edge["node"]
                name = node.get("name", "")
                
                if "Online Store" in name or "online" in name.lower():
                    self.publication_ids["Online Store"] = node["id"]
                
                if "Shop" in name and "Online" not in name:
                    self.publication_ids["Shop"] = node["id"]
        
        return self.publication_ids
    
    def publish_product_to_sales_channels(self, product_id: str) -> bool:
        publications = self.get_sales_channel_publications()
        
        if not publications:
            return False
        
        query = """
        mutation publishProduct($id: ID!, $input: [PublicationInput!]!) {
            publishablePublish(id: $id, input: $input) {
                publishable {
                    ... on Product {
                        id
                        title
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        publication_inputs = []
        for channel_name, publication_id in publications.items():
            publication_inputs.append({
                "publicationId": publication_id
            })
        
        result = self.graphql_request(query, {
            "id": product_id,
            "input": publication_inputs
        })
        
        if result and result.get("data", {}).get("publishablePublish", {}).get("publishable"):
            return True
        
        return False
    
    def get_collection_id(self) -> Optional[str]:
        """Récupère l'ID de collection depuis config avec validation robuste"""
        
        collection_id = self.config.get('collection_id')
        
        if not collection_id:
            print("❌ ERREUR: Aucun 'collection_id' trouvé dans config.json")
            print("\n📋 Comment obtenir votre collection_id:")
            print("   1. Allez sur Shopify Admin > Products > Collections")
            print("   2. Cliquez sur votre collection")
            print("   3. Dans l'URL, copiez le numéro après /collections/")
            print("   4. Format: 'gid://shopify/Collection/VOTRE_NUMERO'")
            print("\n   Exemple: 'gid://shopify/Collection/629200158987'")
            print("\n   OU lancez: python get_collection_id.py")
            return None
        
        collection_id = str(collection_id).strip().strip('"').strip("'")
        
        if not collection_id.startswith('gid://shopify/Collection/'):
            print(f"❌ ERREUR: Format de collection_id invalide: '{collection_id}'")
            print(f"\n📋 Format attendu: 'gid://shopify/Collection/NUMERO'")
            print(f"   Vous avez: '{collection_id}'")
            
            if collection_id.replace('x', '').replace('X', '').isdigit() or collection_id.replace('x', '').replace('X', '').replace('_', '').isdigit():
                print(f"\n💡 Si votre ID de collection est {collection_id}, utilisez:")
                print(f"   'gid://shopify/Collection/{collection_id}'")
            
            return None
        
        collection_number = collection_id.split('/')[-1]
        if 'x' in collection_number.lower() or '_' in collection_number:
            print(f"❌ ERREUR: Le collection_id contient des placeholders: '{collection_id}'")
            print(f"\n📋 Remplacez les 'x' par votre vrai numéro de collection")
            print(f"   Format actuel: {collection_id}")
            print(f"   Format attendu: gid://shopify/Collection/629200158987 (exemple)")
            print("\n   💡 Lancez: python get_collection_id.py")
            print("      pour récupérer automatiquement votre collection_id")
            return None
        
        if self.verbose:
            print(f"✅ Collection ID valide: {collection_id}")
        
        return collection_id
    
    def save_digital_downloads_mapping(self, product_id: str, title: str, variant_mapping: dict, beat_folder: Path):
        file_patterns = self.config.get('file_patterns', {})
        
        mapping_data = {
            "product_id": product_id,
            "product_title": title,
            "folder": str(beat_folder),
            "variants": []
        }
        
        def get_files_by_type(file_type: str) -> list:
            pattern = file_patterns.get(file_type, f'*{file_type}*')
            files = list(beat_folder.glob(pattern))
            return [str(f) for f in files] if files else []
        
        for variant_name, variant_data in variant_mapping.items():
            variant_id = variant_data['id']
            digital_files_types = variant_data['digital_files']
            
            files_to_attach = []
            for file_type in digital_files_types:
                files = get_files_by_type(file_type)
                files_to_attach.extend(files)
            
            if files_to_attach:
                mapping_data["variants"].append({
                    "variant_id": variant_id,
                    "type": variant_name,
                    "files": files_to_attach
                })
        
        output_file = Path("digital_downloads_mapping.json")
        existing_data = []
        
        if output_file.exists():
            with open(output_file, 'r', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = []
        
        existing_data.append(mapping_data)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        
        return mapping_data
    
    def create_product(self, title: str, bpm: str, duration: str, tags: str, audio_file_id: Optional[str] = None, creation_date: Optional[str] = None) -> Optional[str]:
        category_id = self.get_music_category_id()
        
        query = """
        mutation createProduct($input: ProductInput!) {
            productCreate(input: $input) {
                product {
                    id
                    title
                    handle
                    category {
                        id
                        name
                    }
                    metafields(first: 10) {
                        edges {
                            node {
                                namespace
                                key
                                value
                            }
                        }
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        tags_list = []
        if tags and isinstance(tags, str) and tags.strip():
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
        
        metafields = [
            {
                "namespace": "custom",
                "key": "bpm",
                "type": "number_integer",
                "value": str(bpm)
            },
            {
                "namespace": "custom",
                "key": "duration",
                "type": "single_line_text_field",
                "value": duration
            },
            {
                "namespace": "custom",
                "key": "tags",
                "type": "list.single_line_text_field",
                "value": json.dumps(tags_list)
            }
        ]
        
        if creation_date:
            try:
                from datetime import datetime
                parsed_date = datetime.strptime(creation_date, "%b %d, %Y")
                iso_date = parsed_date.strftime("%Y-%m-%d")
                
                metafields.append({
                    "namespace": "custom",
                    "key": "creation_date",
                    "type": "date",
                    "value": iso_date
                })
            except ValueError as e:
                if self.verbose:
                    print(f"   ⚠️ Could not parse creation date '{creation_date}': {e}")
        
        product_tags = []
        if tags:
            product_tags.extend(tags_list)
        
        default_tags = self.config.get('default_product_tags', [])
        if default_tags:
            product_tags.extend(default_tags)
        
        seen = set()
        unique_tags = []
        for tag in product_tags:
            if tag.lower() not in seen:
                seen.add(tag.lower())
                unique_tags.append(tag)
        
        product_input = {
            "title": title,
            "productType": self.config.get('product_type', 'Beat'),
            "status": "ACTIVE",
            "tags": unique_tags,
            "metafields": metafields,
            "requiresSellingPlan": False,
            "productOptions": [
                {
                    "name": "Licence",
                    "values": [
                        {"name": variant["name"]} 
                        for variant in self.config['variants']
                    ]
                }
            ]
        }
        
        if category_id:
            product_input["category"] = category_id
        
        result = self.graphql_request(query, {"input": product_input})
        
        if result and result.get("data", {}).get("productCreate", {}).get("product"):
            product = result["data"]["productCreate"]["product"]
            return product["id"]
        else:
            if result and result.get("data", {}).get("productCreate", {}).get("userErrors"):
                errors = result["data"]["productCreate"]["userErrors"]
                if self.config.get('verbose', False):
                    print(f"❌ Product creation errors: {errors}")
        
        return None
    
    def check_file_status(self, file_id: str, max_attempts: int = 10) -> bool:
        """Check if a file has finished processing"""
        query = """
        query getFileStatus($id: ID!) {
            node(id: $id) {
                ... on GenericFile {
                    id
                    fileStatus
                }
                ... on MediaImage {
                    id
                    fileStatus
                }
            }
        }
        """
        
        for attempt in range(max_attempts):
            result = self.graphql_request(query, {"id": file_id})
            
            if result and result.get("data", {}).get("node"):
                node = result["data"]["node"]
                status = node.get("fileStatus", "")
                
                if status == "READY":
                    return True
                elif status in ["FAILED", "PROCESSING_FAILED"]:
                    print(f"⚠️ File processing failed: {file_id}")
                    return False
                
                time.sleep(1)
            else:
                time.sleep(1)
        
        print(f"⚠️ File status check timed out: {file_id}")
        return False
    
    def update_audio_preview_metafield(self, product_id: str, audio_file_id: str) -> bool:
        """Update the audio_preview metafield after the product is created"""
        query = """
        mutation updateProductMetafields($input: ProductInput!) {
            productUpdate(input: $input) {
                product {
                    id
                    metafields(first: 10) {
                        edges {
                            node {
                                namespace
                                key
                                value
                            }
                        }
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        product_input = {
            "id": product_id,
            "metafields": [
                {
                    "namespace": "custom",
                    "key": "audio_preview",
                    "type": "file_reference",
                    "value": audio_file_id
                }
            ]
        }
        
        result = self.graphql_request(query, {"input": product_input})
        
        if result and result.get("data", {}).get("productUpdate", {}).get("product"):
            return True
        else:
            if self.config.get('verbose', False):
                if result and result.get("data", {}).get("productUpdate", {}).get("userErrors"):
                    errors = result["data"]["productUpdate"]["userErrors"]
                    print(f"   ⚠️ Audio preview errors: {errors}")
        
        return False
    
    def create_variants(self, product_id: str, beat_folder: Path) -> dict:
        query = """
        mutation createVariants($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
            productVariantsBulkCreate(
                productId: $productId, 
                variants: $variants, 
                strategy: REMOVE_STANDALONE_VARIANT
            ) {
                productVariants {
                    id
                    title
                    price
                    inventoryItem {
                        tracked
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        variants_input = []
        variant_mapping = {}
        
        for variant in self.config['variants']:
            variants_input.append({
                "optionValues": [{"optionName": "Licence", "name": variant["name"]}],
                "price": variant["price"],
                "inventoryPolicy": "CONTINUE",
                "inventoryItem": {
                    "tracked": False,
                    "requiresShipping": False
                }
            })
        
        result = self.graphql_request(query, {
            "productId": product_id,
            "variants": variants_input
        })
        
        if result and result.get("data", {}).get("productVariantsBulkCreate", {}).get("productVariants"):
            created_variants = result['data']['productVariantsBulkCreate']['productVariants']
            
            for config_variant in self.config['variants']:
                variant_name = config_variant['name']
                for created_variant in created_variants:
                    if variant_name in created_variant['title']:
                        variant_mapping[variant_name] = {
                            'id': created_variant['id'],
                            'digital_files': config_variant.get('digital_files', [])
                        }
                        break
            
            return variant_mapping
        
        return {}
    
    def create_file(self, file_url: str, filename: str) -> Optional[str]:
        query = """
        mutation createFile($files: [FileCreateInput!]!) {
            fileCreate(files: $files) {
                files {
                    id
                    fileStatus
                    alt
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        result = self.graphql_request(query, {
            "files": [{
                "originalSource": file_url,
                "filename": filename,
                "contentType": "FILE"
            }]
        })
        
        if result and result.get("data", {}).get("fileCreate", {}).get("files"):
            file_data = result["data"]["fileCreate"]["files"][0]
            time.sleep(1)
            return file_data["id"]
        
        return None
    
    def upload_file_to_shopify(self, file_path: str, resource_type: str = "IMAGE") -> Optional[str]:
        if not os.path.exists(file_path):
            return None
        
        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        
        if resource_type == "FILE" or mime_type and mime_type.startswith("audio"):
            resource_type = "FILE"
        
        stage_query = """
        mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
            stagedUploadsCreate(input: $input) {
                stagedTargets {
                    url
                    resourceUrl
                    parameters {
                        name
                        value
                    }
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        stage_result = self.graphql_request(stage_query, {
            "input": [{
                "resource": resource_type,
                "filename": filename,
                "mimeType": mime_type or "application/octet-stream",
                "fileSize": str(file_size),
                "httpMethod": "POST"
            }]
        })
        
        if not stage_result or not stage_result.get("data", {}).get("stagedUploadsCreate", {}).get("stagedTargets"):
            return None
        
        target = stage_result["data"]["stagedUploadsCreate"]["stagedTargets"][0]
        
        try:
            with open(file_path, 'rb') as f:
                form_data = {param["name"]: param["value"] for param in target["parameters"]}
                files = {'file': (filename, f, mime_type)}
                
                upload_response = requests.post(target["url"], data=form_data, files=files)
                
                if upload_response.status_code not in [200, 201, 204]:
                    return None
        except (OSError, requests.RequestException) as e:
            print(f"⚠️ File upload error: {e}")
            return None
        
        if resource_type == "FILE":
            file_id = self.create_file(target["resourceUrl"], filename)
            return file_id
        
        return target["resourceUrl"]
    
    def add_product_media(self, product_id: str, media_urls: List[Dict[str, str]]) -> bool:
        query = """
        mutation createProductMedia($media: [CreateMediaInput!]!, $productId: ID!) {
            productCreateMedia(media: $media, productId: $productId) {
                media {
                    id
                    mediaContentType
                }
                mediaUserErrors {
                    field
                    message
                }
            }
        }
        """
        
        result = self.graphql_request(query, {
            "productId": product_id,
            "media": media_urls
        })
        
        if result and result.get("data", {}).get("productCreateMedia", {}).get("media"):
            return True
        
        return False
    
    def add_product_to_collection(self, product_id: str, collection_id: str) -> bool:
        query = """
        mutation addProductsToCollection($id: ID!, $productIds: [ID!]!) {
            collectionAddProducts(id: $id, productIds: $productIds) {
                collection {
                    id
                }
                userErrors {
                    field
                    message
                }
            }
        }
        """
        
        result = self.graphql_request(query, {
            "id": collection_id,
            "productIds": [product_id]
        })
        
        if result and result.get("data", {}).get("collectionAddProducts"):
            return True
        
        return False
    
    def get_audio_duration(self, mp3_path: str) -> str:
        try:
            audio = MP3(mp3_path)
            duration_seconds = int(audio.info.length)
            minutes = duration_seconds // 60
            seconds = duration_seconds % 60
            return f"{minutes}:{seconds:02d}"
        except Exception:
            return "3:00"
    
    def upload_beat_to_shopify(self, beat_folder: Path, index: int) -> dict:
        """Upload beat to Shopify with all files at once"""
        try:
            csv_files = list(beat_folder.glob("*_metadata.csv"))
            if not csv_files:
                print(f"❌ Beat {index}: FAILED - No metadata in {beat_folder}")
                return {"status": "failed"}
            
            df = pd.read_csv(csv_files[0])
            
            # Validation des champs requis (title et bpm)
            missing_fields = []
            
            # Vérifier title (REQUIS)
            raw_title = df['title'].iloc[0] if 'title' in df.columns else None
            if pd.isna(raw_title) or not isinstance(raw_title, str) or not str(raw_title).strip():
                missing_fields.append("title")
                title = ""
            else:
                title = str(raw_title).strip()
            
            # Vérifier bpm (REQUIS)
            raw_bpm = df['bpm'].iloc[0] if 'bpm' in df.columns else None
            if pd.isna(raw_bpm):
                missing_fields.append("bpm")
                bpm = "0"
            else:
                bpm = str(raw_bpm)
            
            # Si des champs requis manquent → SKIP
            if missing_fields:
                print(f"⚠️  Beat {index}: SKIPPED - Missing required metadata: {', '.join(missing_fields)}")
                print(f"   📁 Folder: {beat_folder.name}")
                return {"status": "skipped", "reason": f"missing_metadata: {', '.join(missing_fields)}"}
            
            # Tags (OPTIONNEL - peut être vide)
            raw_tags = df['tags'].iloc[0] if 'tags' in df.columns else None
            if pd.isna(raw_tags) or not isinstance(raw_tags, str):
                tags = ""
            else:
                tags = str(raw_tags).strip()
            
            # creation_date (OPTIONNEL)
            creation_date = None
            if 'creation_date' in df.columns:
                raw_date = df['creation_date'].iloc[0]
                if pd.notna(raw_date) and isinstance(raw_date, str):
                    creation_date = raw_date
            
            existing_product_id = self.check_product_exists(title)
            if existing_product_id:
                print(f"⭐️ Beat {index}: SKIPPED - {title} (already exists)")
                return {"status": "skipped"}
            
            print(f"⚙️  Beat {index}: PROCESSING - {title}")
            
            artwork_patterns = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']
            artwork_files = []
            for pattern in artwork_patterns:
                artwork_files.extend(list(beat_folder.glob(pattern)))
            artwork_files = artwork_files[:1]
            
            file_patterns = self.config.get('file_patterns', {})
            mp3_pattern = file_patterns.get('mp3', '*_MP3.*')
            wav_pattern = file_patterns.get('wav', '*_WAV.*')
            stems_pattern = file_patterns.get('stems', '*_STEMS.*')
            
            mp3_files = list(beat_folder.glob(mp3_pattern))
            
            if not artwork_files:
                print(f"❌ Beat {index}: FAILED - {title} (no artwork found)")
                return {"status": "failed"}
            
            if not mp3_files:
                print(f"⚠️ No MP3 files found matching pattern '{mp3_pattern}'")
            
            duration = "3:00"
            audio_file_id = None
            
            if mp3_files:
                duration = self.get_audio_duration(str(mp3_files[0]))
                audio_file_id = self.upload_file_to_shopify(str(mp3_files[0]), "FILE")
                if not audio_file_id:
                    print(f"   ⚠️ MP3 upload failed")
            
            product_id = self.create_product(title, bpm, duration, tags, audio_file_id, creation_date)
            if not product_id:
                print(f"❌ Beat {index}: FAILED - {title} (product creation failed)")
                return {"status": "failed"}
            
            if audio_file_id:
                if not self.check_file_status(audio_file_id):
                    print(f"   ⚠️ Could not set audio preview (file processing timeout)")
                elif not self.update_audio_preview_metafield(product_id, audio_file_id):
                    print(f"   ⚠️ Could not set audio preview (metafield update failed)")
            else:
                if mp3_files:
                    print(f"   ⚠️ No audio preview set (upload failed)")
            
            variant_mapping = self.create_variants(product_id, beat_folder)
            
            artwork_url = self.upload_file_to_shopify(str(artwork_files[0]), "IMAGE")
            if artwork_url:
                self.add_product_media(product_id, [
                    {"originalSource": artwork_url, "mediaContentType": "IMAGE"}
                ])
            
            self.publish_product_to_sales_channels(product_id)
            
            collection_id = self.get_collection_id()
            if collection_id:
                self.add_product_to_collection(product_id, collection_id)
            
            self.save_digital_downloads_mapping(product_id, title, variant_mapping, beat_folder)
            
            if self.config.get('auto_upload_digital_downloads', True):
                if not self.upload_files_to_digital_downloads(product_id, title, beat_folder, only_large_files=False):
                    print(f"⚠️ Beat {index}: Product created but Digital Downloads upload failed - {title}")
                    return {
                        "status": "created",
                        "product_id": product_id,
                        "title": title,
                        "beat_folder": beat_folder
                    }
            
            print(f"✅ Beat {index}: SUCCESS - {title}")
            return {
                "status": "created",
                "product_id": product_id,
                "title": title,
                "beat_folder": beat_folder
            }
            
        except Exception as e:
            print(f"❌ Beat {index}: FAILED - Error: {e}")
            return {"status": "failed"}
    
    def generate_digital_downloads_csv(self):
        json_file = Path("digital_downloads_mapping.json")
        if not json_file.exists():
            return
        
        with open(json_file, 'r', encoding='utf-8') as f:
            mappings = json.load(f)
        
        csv_data = []
        csv_data.append(["Product Title", "Product ID", "Variant Title", "Variant ID", "SKU", "Files"])
        
        for product in mappings:
            for variant in product.get("variants", []):
                files_str = ";".join(variant["files"])
                csv_data.append([
                    product["product_title"],
                    product["product_id"],
                    variant["type"],
                    variant["variant_id"],
                    f"{product['product_title'].replace(' ', '_')}_{variant['type'].replace(' ', '_')}",
                    files_str
                ])
        
        csv_file = Path("digital_downloads_import.csv")
        df = pd.DataFrame(csv_data[1:], columns=csv_data[0])
        df.to_csv(csv_file, index=False, encoding='utf-8')
        
        print(f"📄 Digital Downloads CSV generated: {csv_file}")
        return csv_file
    
    def process_beats(self):
        print("\n🔧 Initializing...")
        self.ensure_metafield_definitions()
        
        if self.config.get('auto_upload_digital_downloads', True):
            print("\n🔐 Logging into Shopify admin for Digital Downloads...")
            self.login_to_shopify()
        
        category_id = self.get_music_category_id()
        publications = self.get_sales_channel_publications()
        
        beat_folders = [
            folder for folder in self.download_folder.iterdir()
            if folder.is_dir() and list(folder.glob("*_metadata.csv"))
        ]
        
        beat_folders = sorted(beat_folders, key=lambda x: x.name.lower(), reverse=True)
        
        print(f"📊 Found {len(beat_folders)} beats to process\n")
        print("=" * 60)
        print("Creating products and uploading ALL files")
        print("=" * 60 + "\n")
        
        created = 0
        skipped = 0
        failed = 0
        
        for i, folder in enumerate(beat_folders, 1):
            result = self.upload_beat_to_shopify(folder, i)
            
            if result.get("status") == "created":
                created += 1
            elif result.get("status") == "skipped":
                skipped += 1
            else:
                failed += 1
            
            time.sleep(2)
        
        print(f"\n{'=' * 60}")
        print(f"📊 FINAL RESULTS:")
        if created > 0:
            print(f"   ✅ Created: {created}")
        if skipped > 0:
            print(f"   ⭐️ Skipped (already exist): {skipped}")
        if failed > 0:
            print(f"   ❌ Failed: {failed}")
        
        total_success = created + skipped
        if beat_folders:
            print(f"\n📈 Success rate: {(total_success/len(beat_folders)*100):.1f}%")
        
        if created > 0 and not self.config.get('auto_upload_digital_downloads', True):
            print(f"\n📁 DIGITAL DOWNLOADS APP SETUP:")
            print(f"   JSON mapping: digital_downloads_mapping.json")
            self.generate_digital_downloads_csv()
            print(f"\n   ℹ️ Next steps:")
            print(f"   1. Open Digital Downloads app in Shopify admin")
            print(f"   2. Use the CSV file to bulk attach files to variants")
            print(f"   3. Configure download limits per license type")
        
        print("=" * 60)
        
        # Close Playwright at the end
        if self.browser:
            loop = get_or_create_event_loop()
            loop.run_until_complete(self.close_playwright())


def main():
    uploader = ShopifyGraphQLUploader("config.json")
    uploader.process_beats()


if __name__ == "__main__":
    main()