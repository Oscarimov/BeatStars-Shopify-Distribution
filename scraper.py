import time
import re
import json
import os
import shutil
import tempfile
from pathlib import Path
import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import zipfile
import tarfile
import platform
import subprocess
from datetime import datetime

# Archive extraction libraries
try:
    import rarfile
    RARFILE_AVAILABLE = True
    
    # Check if rarfile can find the extraction tool
    try:
        # First, check if unrar.exe is in tools/ folder (for packaged builds)
        tools_dir = Path(__file__).parent / 'tools'
        local_unrar = None
        
        if platform.system() == 'Windows':
            local_unrar = tools_dir / 'unrar.exe'
            if local_unrar.exists():
                rarfile.UNRAR_TOOL = str(local_unrar)
                print(f"✅ Using bundled UnRAR: {local_unrar}")
                RARFILE_TOOL_AVAILABLE = True
            else:
                # Try system unrar
                rarfile.UNRAR_TOOL
                RARFILE_TOOL_AVAILABLE = True
        else:
            # Linux/macOS: check system unrar
            rarfile.UNRAR_TOOL
            RARFILE_TOOL_AVAILABLE = True
            
    except:
        RARFILE_TOOL_AVAILABLE = False
        if platform.system() == 'Windows':
            print("⚠️  UnRAR.exe not found")
            print("   RAR extraction will work but integrity checks will be skipped")
        else:
            print("⚠️  rarfile installed but unrar tool not found")
            print("   RAR extraction will work but integrity checks will be skipped")
            print("   To enable RAR integrity checks, install unrar:")
            print("   - Ubuntu/Debian: sudo apt-get install unrar")
            print("   - macOS: brew install unrar")
            
except ImportError:
    RARFILE_AVAILABLE = False
    RARFILE_TOOL_AVAILABLE = False
    print("⚠️  rarfile not installed - RAR file extraction may not work")
    print("   Install with: pip install rarfile --break-system-packages")

try:
    import py7zr
    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False
    print("⚠️  py7zr not installed - 7Z file extraction may not work")
    print("   Install with: pip install py7zr --break-system-packages")

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    print("⚠️  pyautogui not installed - MP3 re-downloads may not work")
    print("   Install with: pip install pyautogui --break-system-packages")

class SecureBeatstarsScraper:
    def __init__(self, download_folder=None, config_path='config.json', verbose=False):
        """
        Initialize scraper with backward compatibility.
        Can accept either download_folder directly OR load from config.
        """
        self.driver = None
        self.temp_profile_dir = None
        self.session_file = Path("beatstars_session.json")
        self.progress_file = Path("beatstars_progress.json")  # Still keep for crash recovery metadata
        
        # Load config
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except:
            self.config = {}
        
        # Configure verbose/debug modes
        debug_mode = self.config.get('debug_mode', False)
        scraper_verbose = self.config.get('scraper_verbose', False)
        
        if debug_mode:
            self.verbose = True
            self.debug_mode = True
        elif scraper_verbose or verbose:
            self.verbose = True
            self.debug_mode = False
        else:
            self.verbose = self.config.get('verbose', False)
            self.debug_mode = False
        
        # Support both methods: direct folder path OR config file
        if download_folder:
            self.download_folder = Path(download_folder)
        else:
            self.download_folder = Path(self.config.get('beats_folder', './beats'))
        
        self.download_folder.mkdir(exist_ok=True)
        print(f"📁 Download folder: {self.download_folder}")
        
        # Selector learning system
        self.learned_selectors_file = Path("beatstars_learned_selectors.json")
        self.learned_selectors = self.load_learned_selectors()
        
        # Load progress tracking (for metadata only, not for skip logic)
        self.progress = self.load_progress()
    
    def load_progress(self):
        """Load download progress metadata (not used for skip detection)"""
        try:
            if self.progress_file.exists():
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                    if self.verbose:
                        print(f"📊 Progress file loaded (metadata only)")
                    return progress
        except:
            pass
        
        return {
            'completed_beats': [],  # For metadata tracking only
            'last_index': 0,
            'session_start': datetime.now().isoformat(),
            'download_order': []
        }
    
    def save_progress(self):
        """Save current progress metadata"""
        try:
            self.progress['last_updated'] = datetime.now().isoformat()
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.progress, f, indent=2, ensure_ascii=False)
            if self.verbose:
                print(f"  💾 Progress metadata saved")
        except Exception as e:
            if self.verbose:
                print(f"  ⚠️ Could not save progress: {e}")
    
    def mark_beat_completed(self, beat_name):
        """Mark a beat as completed (metadata only)"""
        if beat_name not in self.progress['completed_beats']:
            self.progress['completed_beats'].append(beat_name)
            if beat_name not in self.progress['download_order']:
                self.progress['download_order'].append(beat_name)
            self.save_progress()
    
    def load_learned_selectors(self):
        """Load previously successful selectors"""
        try:
            if self.learned_selectors_file.exists():
                with open(self.learned_selectors_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if self.verbose:
                        print(f"✅ Loaded {len(data.get('menu_button', []))} learned menu selectors")
                    return data
        except:
            pass
        
        return {
            'menu_button': [],
            'download_option': [],
            'last_updated': None
        }
    
    def normalize_for_comparison(self, text):
        """Normalize text for comparison - MORE aggressive normalization"""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove extra whitespace
        text = ' '.join(text.split())
        
        # Remove common unicode variations and accents
        import unicodedata
        text = unicodedata.normalize('NFKD', text)
        text = ''.join([c for c in text if not unicodedata.combining(c)])
        
        # Remove punctuation that might cause issues
        text = text.replace('é', 'e').replace('è', 'e').replace('ê', 'e')
        text = text.replace('à', 'a').replace('â', 'a')
        text = text.replace('ù', 'u').replace('û', 'u')
        text = text.replace('ô', 'o').replace('ö', 'o')
        text = text.replace('î', 'i').replace('ï', 'i')
        text = text.replace('ç', 'c')
        
        return text.strip()

    def debug_beat_bpm_structure(self, beat_element, index):
        """Debug BPM extraction when it fails"""
        print(f"\n{'='*60}")
        print(f"DEBUG: Beat #{index} BPM Structure")
        print(f"{'='*60}")
        print("\n1. FULL TEXT:")
        print(beat_element.text[:500])
        print("\n2. BPM ICONS:")
        try:
            icons = beat_element.find_elements(By.CSS_SELECTOR, "i.icon-bpm, i[class*='bpm']")
            for i, icon in enumerate(icons):
                parent = icon.find_element(By.XPATH, "..")
                print(f"   Icon {i}: {parent.text.strip()}")
        except: pass
        print("\n3. COLUMNS:")
        try:
            cols = beat_element.find_elements(By.CSS_SELECTOR, ".table-column")
            for i, col in enumerate(cols):
                if col.text.strip():
                    print(f"   Col {i}: {col.text.strip()}")
        except: pass
        print(f"{'='*60}\n")
    
    def extract_creation_date_robust(self, beat_element, index):
        """Enhanced creation date extraction with JavaScript and textContent for dynamic content"""
        date_value = None
        
        # Method 1: JavaScript icon-based extraction
        if not date_value:
            try:
                date_value = self.driver.execute_script("""
                    var element = arguments[0];
                    var dateIcon = element.querySelector('i.icon-clock');
                    if (dateIcon) {
                        var parent = dateIcon.parentElement;
                        var valueSpan = parent.querySelector('span.value, span');
                        if (valueSpan) {
                            return (valueSpan.textContent || valueSpan.innerText || '').trim();
                        }
                    }
                    return null;
                """, beat_element)
                if date_value and len(date_value) > 0:
                    if self.verbose:
                        print(f"  [DEBUG] Date via JavaScript icon: {date_value}")
            except: 
                pass
        
        # Method 2: textContent attribute on icon-based selector
        if not date_value:
            try:
                date_icon = beat_element.find_element(By.CSS_SELECTOR, "i.icon-clock")
                parent = date_icon.find_element(By.XPATH, "..")
                date_span = parent.find_element(By.CSS_SELECTOR, "span.value, span")
                date_value = date_span.get_attribute('textContent').strip()
                if date_value and len(date_value) > 0:
                    if self.verbose:
                        print(f"  [DEBUG] Date via textContent: {date_value}")
            except:
                pass
        
        # Method 3: Standard text extraction
        if not date_value:
            try:
                date_icon = beat_element.find_element(By.CSS_SELECTOR, "i.icon-clock")
                parent = date_icon.find_element(By.XPATH, "..")
                date_span = parent.find_element(By.CSS_SELECTOR, "span.value, span")
                date_value = date_span.text.strip()
                if date_value and len(date_value) > 0:
                    if self.verbose:
                        print(f"  [DEBUG] Date via text: {date_value}")
            except:
                pass
        
        # Method 4: Search in all table columns for date pattern
        if not date_value:
            try:
                columns = beat_element.find_elements(By.CSS_SELECTOR, ".table-column")
                for col in columns:
                    text = col.text.strip()
                    if re.search(r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b', text, re.IGNORECASE):
                        date_value = text
                        if self.verbose:
                            print(f"  [DEBUG] Date via column text pattern: {date_value}")
                        break
            except:
                pass
        
        return date_value
    
    def extract_bpm_robust(self, beat_element, index):
        """Enhanced BPM extraction with JavaScript and textContent for dynamic content"""
        bpm_value = None
        
        # Method 1: JavaScript icon-based extraction
        if not bpm_value:
            try:
                bpm_value = self.driver.execute_script("""
                    var element = arguments[0];
                    var bpmIcon = element.querySelector('i.icon-bpm');
                    if (bpmIcon) {
                        var parent = bpmIcon.parentElement;
                        var valueSpan = parent.querySelector('span.value, span');
                        if (valueSpan) {
                            return (valueSpan.textContent || valueSpan.innerText || '').trim();
                        }
                    }
                    return null;
                """, beat_element)
                if bpm_value and len(bpm_value) > 0:
                    if self.verbose:
                        print(f"  [DEBUG] BPM via JavaScript icon: {bpm_value}")
            except: 
                pass
        
        # Method 2: textContent attribute
        if not bpm_value:
            try:
                bpm_icon = beat_element.find_element(By.CSS_SELECTOR, "i.icon-bpm")
                parent = bpm_icon.find_element(By.XPATH, "..")
                value_span = parent.find_element(By.CSS_SELECTOR, "span.value, span")
                bpm_value = value_span.get_attribute('textContent')
                if bpm_value:
                    bpm_value = bpm_value.strip()
                    if self.verbose:
                        print(f"  [DEBUG] BPM via textContent: {bpm_value}")
            except: 
                pass
        
        # Method 3: innerText attribute
        if not bpm_value:
            try:
                bpm_icon = beat_element.find_element(By.CSS_SELECTOR, "i.icon-bpm")
                parent = bpm_icon.find_element(By.XPATH, "..")
                value_span = parent.find_element(By.CSS_SELECTOR, "span.value, span")
                bpm_value = value_span.get_attribute('innerText')
                if bpm_value:
                    bpm_value = bpm_value.strip()
            except: 
                pass
        
        # Method 4: JavaScript search for "BPM" text
        if not bpm_value:
            try:
                bpm_value = self.driver.execute_script("""
                    var element = arguments[0];
                    var spans = element.querySelectorAll('span');
                    for (var i = 0; i < spans.length; i++) {
                        var text = (spans[i].textContent || spans[i].innerText || '').trim();
                        if (text && text.toUpperCase().indexOf('BPM') > -1) {
                            return text;
                        }
                    }
                    return null;
                """, beat_element)
                if bpm_value:
                    bpm_value = bpm_value.strip()
            except: 
                pass
        
        # Method 5: Column search with textContent
        if not bpm_value:
            try:
                cols = beat_element.find_elements(By.CSS_SELECTOR, ".table-column, .secondary-column")
                for col in cols:
                    col_text = col.get_attribute('textContent') or col.get_attribute('innerText') or ''
                    if 'BPM' in col_text.upper():
                        bpm_value = col_text.strip()
                        break
            except: 
                pass
        
        # Method 6: Regex on full element text
        if not bpm_value:
            try:
                full_text = self.driver.execute_script("""
                    return (arguments[0].textContent || arguments[0].innerText || '').trim();
                """, beat_element)
                
                if full_text:
                    match = re.search(r'(\d+)\s*BPM', full_text, re.IGNORECASE)
                    if match:
                        bpm_value = f"{match.group(1)} BPM"
            except: 
                pass
        
        if not bpm_value and self.debug_mode:
            self.debug_beat_bpm_structure(beat_element, index)
        
        return bpm_value if bpm_value else "N/A"
    
    def save_learned_selector(self, selector_type, selector, description=""):
        """Save a working selector for future use"""
        if selector_type not in self.learned_selectors:
            self.learned_selectors[selector_type] = []
        
        selector_entry = {'selector': selector, 'description': description}
        if selector_entry not in self.learned_selectors[selector_type]:
            self.learned_selectors[selector_type].insert(0, selector_entry)
            self.learned_selectors[selector_type] = self.learned_selectors[selector_type][:10]
            
            import datetime
            self.learned_selectors['last_updated'] = datetime.datetime.now().isoformat()
            
            try:
                with open(self.learned_selectors_file, 'w', encoding='utf-8') as f:
                    json.dump(self.learned_selectors, f, indent=2, ensure_ascii=False)
                if self.verbose:
                    print(f"  💾 Learned new selector for {selector_type}")
            except:
                pass

    def sanitize_filename(self, filename, max_length=200):
        """Sanitize filename for filesystem compatibility"""
        invalid_chars = r'[<>:"/\\|?*]'
        filename = re.sub(invalid_chars, '_', filename)
        filename = filename.strip('. ')
        return filename[:max_length]

    def cleanup(self):
        """Clean up temporary profile"""
        if self.temp_profile_dir and os.path.exists(self.temp_profile_dir):
            try:
                shutil.rmtree(self.temp_profile_dir)
                if self.verbose:
                    print("🧹 Cleaned temp profile")
            except:
                pass

    def setup_secure_driver(self):
        """Setup Chrome with temporary profile"""
        self.temp_profile_dir = tempfile.mkdtemp(prefix="chrome_profile_")
        print(f"🔒 Temp profile: {self.temp_profile_dir}")
        
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={self.temp_profile_dir}")
        chrome_options.add_experimental_option("prefs", {
            "download.default_directory": str(self.download_folder.resolve()),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "plugins.always_open_pdf_externally": True,
            "safebrowsing.enabled": True
        })
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            print("✅ Browser launched")
        except Exception as e:
            print(f"❌ Browser launch error: {e}")
            self.cleanup()
            raise

    def save_session(self):
        """Save browser cookies and session info"""
        try:
            cookies = self.driver.get_cookies()
            session_data = {
                'cookies': cookies,
                'url': self.driver.current_url,
                'timestamp': time.time()
            }
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, indent=2)
            
            print("💾 BeatStars session saved")
            return True
        except Exception as e:
            if self.verbose:
                print(f"⚠️ Could not save session: {e}")
            return False

    def load_session(self):
        """Load saved session if exists and valid"""
        if not self.session_file.exists():
            return False
        
        if self.config.get('beatstars_login', {}).get('force_fresh_login', False):
            print("🔄 Force fresh login enabled - skipping session restore")
            return False
        
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            age_days = (time.time() - session_data['timestamp']) / 86400
            if age_days > 7:
                print("⚠️ Saved session is too old (>7 days)")
                return False
            
            print("🔄 Attempting to restore previous session...")
            
            self.driver.get("https://www.beatstars.com/")
            time.sleep(1)
            
            # Clean and add cookies with domain normalization
            cookies_added = 0
            for cookie in session_data['cookies']:
                try:
                    cookie_copy = cookie.copy()
                    
                    # Normalize domain to base domain
                    if 'domain' in cookie_copy:
                        domain = cookie_copy['domain'].lstrip('.')
                        if 'beatstars.com' in domain:
                            cookie_copy['domain'] = '.beatstars.com'
                    
                    # Remove problematic fields
                    cookie_copy.pop('sameSite', None)
                    cookie_copy.pop('expiry', None)
                    
                    self.driver.add_cookie(cookie_copy)
                    cookies_added += 1
                except Exception as e:
                    if self.verbose:
                        print(f"   ⚠️ Could not add cookie {cookie.get('name', 'unknown')}: {e}")
            
            if self.verbose:
                print(f"   ✓ Added {cookies_added}/{len(session_data['cookies'])} cookies")
            
            # Now navigate to studio page
            self.driver.get("https://studio.beatstars.com/content/tracks/uploaded")
            time.sleep(3)  # INCREASED: wait for page to load
            
            # Try to trigger initial beat loading with a small scroll
            try:
                self.driver.execute_script("window.scrollTo(0, 500);")
                time.sleep(1)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            except:
                pass
            
            if self.check_login_status():
                print("✅ Session restored successfully!")
                return True
            else:
                print("❌ Session restore failed - login required")
                return False
                
        except Exception as e:
            if self.verbose:
                print(f"❌ Session restore error: {e}")
            return False

    def check_login_status(self):
        """Check if user is logged in"""
        try:
            # Wait longer and check multiple indicators
            # First, check if we're on the studio page (not login page)
            if "account/login" in self.driver.current_url.lower():
                return False
            
            # Check for studio-specific elements that appear when logged in
            indicators = [
                "studio-list-item",  # Beat items
                "[class*='studio-header']",  # Studio header
                "studio-button-item-menu",  # Beat menu buttons
                "[data-cy*='studio']"  # Any studio data-cy element
            ]
            
            for selector in indicators:
                try:
                    WebDriverWait(self.driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    if self.verbose:
                        print(f"   ✓ Login verified via: {selector}")
                    return True
                except:
                    continue
            
            # Last check: look for user profile/menu
            try:
                self.driver.find_element(By.CSS_SELECTOR, "[class*='user-menu'], [class*='profile']")
                return True
            except:
                pass
            
            return False
        except:
            return False

    def dismiss_save_password_popup(self):
        """Dismiss browser's save password popup"""
        try:
            never_selectors = [
                "button:contains('Jamais')", "button:contains('Never')",
                "button[aria-label*='Jamais']", "button[aria-label*='Never']"
            ]
            for selector in never_selectors:
                try:
                    if ':contains' in selector:
                        text = selector.split("'")[1]
                        btn = self.driver.find_element(By.XPATH, f"//button[contains(text(), '{text}')]")
                    else:
                        btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if btn and btn.is_displayed():
                        try:
                            btn.click()
                        except:
                            self.driver.execute_script("arguments[0].click();", btn)
                        time.sleep(0.5)
                        return True
                except:
                    continue
        except:
            pass
        return False

    def dismiss_cookie_popups(self):
        """Dismiss cookie consent popups"""
        try:
            popup_selectors = [
                "#onetrust-accept-btn-handler", ".onetrust-close-btn-handler",
                "button[id*='accept']", "button[id*='cookie']"
            ]
            for selector in popup_selectors:
                try:
                    btn = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if btn.is_displayed():
                        btn.click()
                        time.sleep(0.5)
                        return True
                except:
                    continue
        except:
            pass
        return False

    def attempt_auto_login(self):
        """Try auto-login with credentials from config - AUTO scroll + MANUAL verification"""
        beatstars_login = self.config.get('beatstars_login', {})
        email = beatstars_login.get('email', '')
        password = beatstars_login.get('password', '')
        
        if not email or not password:
            return False
        
        print("🔐 Attempting auto-login...")
        try:
            self.driver.get("https://www.beatstars.com/account/login")
            time.sleep(2)
            self.dismiss_cookie_popups()
            
            email_field = self.driver.find_element(By.CSS_SELECTOR, "input[type='email'], input[name='email']")
            email_field.clear()
            email_field.send_keys(email)
            time.sleep(0.5)
            
            self.dismiss_cookie_popups()
            continue_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            try:
                continue_btn.click()
            except:
                self.driver.execute_script("arguments[0].click();", continue_btn)
            time.sleep(2)
            
            password_field = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='password']"))
            )
            password_field.clear()
            password_field.send_keys(password)
            time.sleep(0.5)
            
            self.dismiss_cookie_popups()
            login_btn = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            try:
                login_btn.click()
            except:
                self.driver.execute_script("arguments[0].click();", login_btn)
            time.sleep(4)
            
            self.dismiss_save_password_popup()
            
            self.driver.get("https://studio.beatstars.com/content/tracks/uploaded")
            time.sleep(3)
            self.dismiss_save_password_popup()
            self.dismiss_cookie_popups()
            
            if "studio.beatstars.com" in self.driver.current_url.lower():
                print("✅ Auto-login successful!")
                
                # AUTO: Click list view and scroll
                print("🔄 Switching to list view and loading all beats...")
                self.click_list_view_button()
                self.auto_scroll_to_bottom()
                
                # MANUAL VERIFICATION
                print("\n⏸️  PAUSED: Please verify all beats are loaded")
                print("   Scroll manually if needed, then press ENTER...")
                input()
                print("✅ Continuing with scraping...\n")
                
                self.save_session()
                return True
            return False
        except:
            return False

    def click_list_view_button(self):
        """Click the list view button"""
        try:
            list_button = self.driver.find_element(By.CSS_SELECTOR, "button.btn-switcher.switcher-list")
            if list_button and list_button.is_displayed():
                try:
                    icon = list_button.find_element(By.CSS_SELECTOR, "i.vb-icon-bars-m-regular")
                    if "selected" in icon.get_attribute("class"):
                        return True
                except:
                    pass
                try:
                    list_button.click()
                except:
                    self.driver.execute_script("arguments[0].click();", list_button)
                time.sleep(1.5) 
                return True
        except:
            pass
        return False

    def auto_scroll_to_bottom(self):
        """Auto-scroll to load all beats - works even in background"""
        print("⏬ Loading all beats (auto-scroll)...")
        
        last_count = 0
        no_change = 0
        scroll_step = 0
        
        while no_change < 3:
            # JavaScript scroll works even if window is in background
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2) 
            
            current_count = len(self.driver.find_elements(By.CSS_SELECTOR, "studio-list-item"))
            print(f"\r   📊 Beats loaded: {current_count} (scroll #{scroll_step+1})", end='', flush=True)
            
            if current_count > last_count:
                no_change = 0
            else:
                no_change += 1
            
            last_count = current_count
            scroll_step += 1
        
        print(f"\n✅ All beats loaded: {current_count} total")
        
        # Scroll back to top
        self.driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1.5)

    def navigate_to_beatstars(self):
        """Navigate to BeatStars with login handling - AUTO list view + scroll + MANUAL verification"""
        print("\n🌐 Connecting to BeatStars...")
        
        if self.load_session():
            print("🔄 Switching to list view and loading all beats...")
            self.click_list_view_button()
            self.auto_scroll_to_bottom()
            
            print("\n⏸️  PAUSED: Please verify all beats are loaded")
            print("   Scroll manually if needed, then press ENTER...")
            input()
            print("✅ Continuing with scraping...\n")
            
            return True
        
        if self.config.get('beatstars_login', {}).get('auto_login', False):
            if self.attempt_auto_login():
                # Auto-login already does list view + scroll + manual pause
                return True
        
        url = "https://studio.beatstars.com/content/tracks/uploaded"
        self.driver.get(url)
        
        print("\n" + "="*60)
        print("  LOGIN REQUIRED")
        print("="*60)
        print("\n  Please log in to BeatStars in the browser")
        print("  Press ENTER when logged in...")
        print("="*60)
        input("\n  → Press ENTER when ready...")
        
        self.save_session()
        
        # AUTO: Click list view and scroll
        print("🔄 Switching to list view and loading all beats...")
        self.dismiss_popups()
        self.click_list_view_button()
        self.auto_scroll_to_bottom()
        
        # MANUAL VERIFICATION
        print("\n⏸️  PAUSED: Please verify all beats are loaded")
        print("   Scroll manually if needed, then press ENTER...")
        input()
        print("✅ Continuing with scraping...\n")
        
        return True

    def wait_for_download(self, timeout=30, reject_extensions=None):
        """Wait for file to appear in download folder"""
        if reject_extensions is None:
            reject_extensions = []
        
        reject_extensions = [ext.lower() for ext in reject_extensions]
        
        start_time = time.time()
        downloaded_file = None
        
        while (time.time() - start_time) < timeout:
            for file in self.download_folder.glob("*"):
                if file.is_file() and not file.name.endswith('.crdownload') and not file.name.endswith('.tmp'):
                    file_age = time.time() - file.stat().st_mtime
                    if file_age < timeout:
                        if file.suffix.lower() in reject_extensions:
                            if self.verbose:
                                print(f"  ⚠️ Rejecting unwanted file type: {file.name}")
                            file.unlink()  # Delete the unwanted file
                            return False
                        downloaded_file = file
                        time.sleep(1)  # Small wait to ensure file is complete
                        return True
            
            time.sleep(0.5)
        
        return False

    def dismiss_popups(self):
        """Remove annoying popups"""
        try:
            self.driver.execute_script("""
                var hj_elements = document.querySelectorAll('[class*="hj-"], [id*="hj-"]');
                for (var el of hj_elements) {
                    el.remove();
                }
            """)
        except:
            pass

    def handle_mp3_player_download(self, original_tab):
        """Handle MP3 download when it opens in new tab/window - SIMPLE JAVASCRIPT METHOD"""
        try:
            self.dismiss_popups()
            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "audio, video")))
            
            self.driver.execute_script("""
                const media = document.querySelector('audio') || document.querySelector('video');
                if (media) {
                    const a = document.createElement('a');
                    a.href = media.src;
                    a.download = media.src.split('/').pop() || 'download.mp3';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                }
            """)
            return True
        except:
            return False
        finally:
            if len(self.driver.window_handles) > 1:
                self.driver.close()
            self.driver.switch_to.window(original_tab)
    
    def handle_wav_player_download(self, original_tab):
        """Handle WAV download when it opens in new tab/window - SAME AS MP3"""
        try:
            self.dismiss_popups()
            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.CSS_SELECTOR, "audio, video")))
            
            self.driver.execute_script("""
                const media = document.querySelector('audio') || document.querySelector('video');
                if (media) {
                    const a = document.createElement('a');
                    a.href = media.src;
                    a.download = media.src.split('/').pop() || 'download.wav';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                }
            """)
            return True
        except:
            return False
        finally:
            if len(self.driver.window_handles) > 1:
                self.driver.close()
            self.driver.switch_to.window(original_tab)

    def safe_click(self, element):
        """Safely click an element"""
        self.dismiss_popups()
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.3)  
        try:
            element.click()
        except:
            self.driver.execute_script("arguments[0].click();", element)

    def retry_missing_files(self, beat_element, beat_folder, safe_beat_name, missing_formats):
        """Retry downloading missing files - SAME logic as download_beat_files"""
        main_window = self.driver.current_window_handle
        main_url = self.driver.current_url
        
        formats_map = {"mp3": 3, "wav": 1, "stems": 2}
        successful = []
        
        for format_name in missing_formats:
            if format_name not in formats_map:
                continue
            
            position = formats_map[format_name]
            xpath = f"//mat-dialog-container//bs-dialog//div[2]/div/div[{position}]/bs-square-button/button"
            
            try:
                # Clean windows
                if len(self.driver.window_handles) > 1:
                    for handle in list(self.driver.window_handles):
                        if handle != main_window:
                            try:
                                self.driver.switch_to.window(handle)
                                self.driver.close()
                            except:
                                pass
                
                # Return to main
                try:
                    self.driver.switch_to.window(main_window)
                except:
                    self.driver.get(main_url)
                    time.sleep(1.5)
                    main_window = self.driver.current_window_handle
                
                time.sleep(0.8)
                
                # Open menu
                menu_button = WebDriverWait(beat_element, 10).until(
                    EC.element_to_be_clickable((By.XPATH, ".//studio-button-item-menu//button"))
                )
                self.safe_click(menu_button)
                
                # Click Download
                download_option = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Download')]]"))
                )
                self.safe_click(download_option)
                
                # Click format
                format_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                existing_files = set(self.download_folder.glob("*"))
                self.safe_click(format_button)
                time.sleep(1.5)

                if (format_name == "mp3" or format_name == "wav") and len(self.driver.window_handles) > 1:
                    new_tab = self.driver.window_handles[-1]
                    self.driver.switch_to.window(new_tab)
                    if format_name == "mp3":
                        self.handle_mp3_player_download(main_window)
                    else:  # wav
                        self.handle_wav_player_download(main_window)
                
                # Validate download
                if self.wait_for_download(reject_extensions=['.svg', '.html', '.htm']):
                    new_files = set(self.download_folder.glob("*")) - existing_files
                    if new_files:
                        downloaded_file = list(new_files)[0]
                        extension = downloaded_file.suffix
                        
                        # Validate extension
                        valid_extensions = {
                            'wav': ['.wav'],
                            'stems': ['.zip', '.rar', '.7z', '.tar', '.gz'],
                            'mp3': ['.mp3']
                        }
                        
                        if extension.lower() not in valid_extensions.get(format_name, []):
                            downloaded_file.unlink()
                            continue
                        
                        if format_name == "stems":
                            new_name = f"{safe_beat_name}_stems{extension}"
                        else:
                            new_name = f"{safe_beat_name}.{format_name.lower()}"
                        
                        destination = beat_folder / new_name
                        
                        if destination.exists():
                            destination.unlink()
                        
                        shutil.move(str(downloaded_file), str(destination))
                        successful.append(format_name)
                
                # Close dialog
                try:
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                    time.sleep(0.3)
                except:
                    pass

            except (TimeoutException, NoSuchElementException):
                try:
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                except:
                    pass
                try:
                    self.driver.switch_to.window(main_window)
                except:
                    pass
            except Exception as e:
                try:
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                except:
                    pass
                try:
                    self.driver.switch_to.window(main_window)
                except:
                    pass
        
        # Final cleanup
        try:
            if len(self.driver.window_handles) > 1:
                for handle in self.driver.window_handles:
                    if handle != main_window:
                        try:
                            self.driver.switch_to.window(handle)
                            self.driver.close()
                        except:
                            pass
            self.driver.switch_to.window(main_window)
        except:
            try:
                self.driver.get(main_url)
                time.sleep(1.5)
            except:
                pass
        
        return successful

    def download_beat_files(self, beat_element, beat_name, beat_folder):
        """Download MP3, WAV, and STEMS for a beat"""
        main_window = self.driver.current_window_handle
        main_url = self.driver.current_url
        
        safe_beat_name = self.sanitize_filename(beat_name)
        download_info = {"beat_name": beat_name, "downloads": []}
        
        formats_map = {
            "mp3": 3,
            "wav": 1,
            "stems": 2
        }
        
        successful_downloads = []
        
        for format_name, position in formats_map.items():
            xpath = f"//mat-dialog-container//bs-dialog//div[2]/div/div[{position}]/bs-square-button/button"
            
            try:
                # CRITICAL: Before each format, ensure we're clean
                if len(self.driver.window_handles) > 1:
                    if self.verbose:
                        print(f"  🧹 Cleaning up {len(self.driver.window_handles)-1} stray window(s)")
                    for handle in list(self.driver.window_handles):
                        if handle != main_window:
                            try:
                                self.driver.switch_to.window(handle)
                                self.driver.close()
                            except:
                                pass
                
                # Return to main window
                try:
                    self.driver.switch_to.window(main_window)
                except:
                    self.driver.get(main_url)
                    time.sleep(1.5)
                    main_window = self.driver.current_window_handle
                
                time.sleep(0.8) 
                
                # Open menu
                menu_button = WebDriverWait(beat_element, 10).until(
                    EC.element_to_be_clickable((By.XPATH, ".//studio-button-item-menu//button"))
                )
                self.safe_click(menu_button)
                
                # Click Download option
                download_option = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//button[.//span[contains(text(), 'Download')]]"))
                )
                self.safe_click(download_option)
                
                # Click format button
                format_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, xpath))
                )
                existing_files = set(self.download_folder.glob("*"))
                self.safe_click(format_button)
                time.sleep(1.5)  

                if (format_name == "mp3" or format_name == "wav") and len(self.driver.window_handles) > 1:
                    new_tab = self.driver.window_handles[-1]
                    self.driver.switch_to.window(new_tab)
                    if format_name == "mp3":
                        self.handle_mp3_player_download(main_window)
                    else:  # wav
                        self.handle_wav_player_download(main_window)
                
                if self.wait_for_download(reject_extensions=['.svg', '.html', '.htm']):
                    new_files = set(self.download_folder.glob("*")) - existing_files
                    if new_files:
                        downloaded_file = list(new_files)[0]
                        extension = downloaded_file.suffix
                        
                        # Double-check extension is valid
                        valid_extensions = {
                            'wav': ['.wav'],
                            'stems': ['.zip', '.rar', '.7z', '.tar', '.gz'],
                            'mp3': ['.mp3']
                        }
                        
                        if extension.lower() not in valid_extensions.get(format_name, []):
                            if self.verbose:
                                print(f"  ⚠️ Invalid file type for {format_name}: {extension}")
                            downloaded_file.unlink()
                            continue
                        
                        if format_name == "stems":
                            new_name = f"{safe_beat_name}_stems{extension}"
                        else:
                            new_name = f"{safe_beat_name}.{format_name.lower()}"
                        
                        destination = beat_folder / new_name
                        
                        if destination.exists():
                            destination.unlink()
                        
                        shutil.move(str(downloaded_file), str(destination))
                        successful_downloads.append(format_name)
                        download_info["downloads"].append({"format": format_name, "filename": new_name})
                
                # Close any dialog/menu
                try:
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                    time.sleep(0.3) 
                except:
                    pass

            except (TimeoutException, NoSuchElementException) as e:
                if self.verbose:
                    print(f"  ⚠️ {format_name} unavailable")
                try:
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                except:
                    pass
                
                try:
                    self.driver.switch_to.window(main_window)
                except:
                    try:
                        self.driver.get(main_url)
                        time.sleep(1.5)
                    except:
                        pass
                        
            except Exception as e:
                if self.verbose:
                    print(f"  ❌ Error for {format_name}: {e}")
                try:
                    ActionChains(self.driver).send_keys(Keys.ESCAPE).perform()
                except:
                    pass
                
                try:
                    self.driver.switch_to.window(main_window)
                except:
                    try:
                        self.driver.get(main_url)
                        time.sleep(1.5)
                    except:
                        pass
        
        # FINAL: Ensure we end on main window
        try:
            if len(self.driver.window_handles) > 1:
                for handle in self.driver.window_handles:
                    if handle != main_window:
                        try:
                            self.driver.switch_to.window(handle)
                            self.driver.close()
                        except:
                            pass
            self.driver.switch_to.window(main_window)
        except:
            try:
                self.driver.get(main_url)
                time.sleep(1.5)
            except:
                pass
        
        if successful_downloads:
            if self.verbose:
                formats_str = ", ".join(successful_downloads)
                print(f"  ✓ Downloaded: {formats_str}")
        
        return download_info

    def detect_archive_type(self, archive_path):
        """Detect archive type from file extension"""
        archive_path = Path(archive_path)
        name_lower = archive_path.name.lower()
        
        if name_lower.endswith('.tar.gz') or name_lower.endswith('.tgz'):
            return ('tar.gz', '.tar.gz' if name_lower.endswith('.tar.gz') else '.tgz')
        elif name_lower.endswith('.tar.bz2') or name_lower.endswith('.tbz2'):
            return ('tar.bz2', '.tar.bz2' if name_lower.endswith('.tar.bz2') else '.tbz2')
        elif name_lower.endswith('.tar.xz'):
            return ('tar.xz', '.tar.xz')
        
        suffix = archive_path.suffix.lower()
        if suffix == '.zip':
            return ('zip', suffix)
        elif suffix == '.rar':
            return ('rar', suffix)
        elif suffix == '.7z':
            return ('7z', suffix)
        elif suffix == '.tar':
            return ('tar', suffix)
        elif suffix == '.gz':
            return ('gz', suffix)
        elif suffix == '.bz2':
            return ('bz2', suffix)
        
        return (None, None)
    
    def extract_archive(self, archive_path, extract_to):
        """Extract any supported archive format"""
        archive_type, _ = self.detect_archive_type(archive_path)
        
        if not archive_type:
            if self.verbose:
                print(f"  ⚠️ Unsupported archive format: {archive_path.suffix}")
            return False
        
        try:
            extract_to.mkdir(parents=True, exist_ok=True)
            
            if archive_type == 'zip':
                with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_to)
                return True
            
            elif archive_type == 'rar':
                if not RARFILE_AVAILABLE:
                    if self.verbose:
                        print(f"  ⚠️ rarfile library not available")
                    return False
                try:
                    with rarfile.RarFile(archive_path, 'r') as rar_ref:
                        rar_ref.extractall(extract_to)
                    return True
                except rarfile.RarCannotExec:
                    # Specific error when unrar tool is missing
                    print(f"  ⚠️ RAR extraction failed: unrar tool not found")
                    print(f"  ℹ️  Install unrar to extract RAR files:")
                    print(f"     Ubuntu/Debian: sudo apt-get install unrar")
                    print(f"     macOS: brew install unrar")
                    return False
                except Exception as e:
                    if self.verbose:
                        print(f"  ⚠️ RAR extraction error: {e}")
                    return False
            
            elif archive_type == '7z':
                if not PY7ZR_AVAILABLE:
                    if self.verbose:
                        print(f"  ⚠️ py7zr library not available")
                    return False
                with py7zr.SevenZipFile(archive_path, 'r') as seven_ref:
                    seven_ref.extractall(extract_to)
                return True
            
            elif archive_type in ['tar', 'tar.gz', 'tar.bz2', 'tar.xz']:
                mode_map = {
                    'tar': 'r',
                    'tar.gz': 'r:gz',
                    'tar.bz2': 'r:bz2',
                    'tar.xz': 'r:xz'
                }
                with tarfile.open(archive_path, mode_map[archive_type]) as tar_ref:
                    tar_ref.extractall(extract_to)
                return True
            
            elif archive_type == 'gz':
                import gzip
                output_path = extract_to / archive_path.stem
                with gzip.open(archive_path, 'rb') as gz_file:
                    with open(output_path, 'wb') as out_file:
                        shutil.copyfileobj(gz_file, out_file)
                return True
            
            elif archive_type == 'bz2':
                import bz2
                output_path = extract_to / archive_path.stem
                with bz2.open(archive_path, 'rb') as bz_file:
                    with open(output_path, 'wb') as out_file:
                        shutil.copyfileobj(bz_file, out_file)
                return True
            
        except Exception as e:
            if self.verbose:
                print(f"  ❌ Error extracting {archive_type} archive: {e}")
            return False
        
        return False

    def find_stems_archive(self, beat_folder, safe_beat_name=None):
        """
        Find stems archive - flexible matching (works with accent mismatches)
        Cherche n'importe quel fichier avec 'stems' dans le nom
        """
        # Extensions supportées
        extensions = ('.zip', '.rar', '.7z', '.tar.gz', '.tgz')
        
        for file in beat_folder.iterdir():
            if file.is_file():
                file_lower = file.name.lower()
                
                # Chercher 'stems' dans le nom (peu importe le reste)
                if 'stems' in file_lower:
                    # Vérifier que c'est une archive
                    if file_lower.endswith(extensions):
                        return file
        
        return None
    
    def cleanup_temp_folder(self, temp_dir):
        """
        Clean up temporary extraction folder
        
        Args:
            temp_dir: Path to the temporary directory to clean
        """
        try:
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir)
                if self.verbose:
                    print(f"   🧹 Cleaned up temporary folder: {temp_dir.name}")
        except Exception as e:
            if self.verbose:
                print(f"   ⚠️  Could not clean temp folder {temp_dir.name}: {e}")

    def process_stems_archive(self, beat_folder, safe_beat_name):
        """
        Process stems archive: extract, add WAV, rezip
        Based on old working version - SIMPLE and AGGRESSIVE
        """
        archive_path = self.find_stems_archive(beat_folder, safe_beat_name)
        
        if not archive_path:
            if self.verbose:
                print(f"  ℹ️  No stems archive found")
            return False
        
        # Find standalone WAV file
        wav_file = None
        for file in beat_folder.iterdir():
            if file.is_file() and file.name.lower().endswith('.wav'):
                if file.stem.lower() == safe_beat_name.lower():
                    wav_file = file
                    break
        
        if not wav_file:
            if self.verbose:
                print(f"  ⚠️  WAV file not found - cannot process archive")
            return False
        
        # Check if archive already has WAV inside (ONLY check - don't skip lightly!)
        try:
            if archive_path.suffix.lower() == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zipf:
                    # Get all files in archive
                    files_in_zip = zipf.namelist()
                    
                    # Check if standalone WAV filename is in the archive
                    wav_filename = wav_file.name
                    if wav_filename in files_in_zip:
                        if self.verbose:
                            print(f"  ✅ Archive already contains {wav_filename}")
                        return True
        except:
            pass
        
        # Archive needs processing!
        temp_dir = beat_folder / f"{safe_beat_name}_stems_temp"
        final_zip = beat_folder / f"{safe_beat_name}_stems.zip"
        
        # Clean up any leftover temp folders
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
            except:
                pass
        
        try:
            if self.verbose:
                print(f"  📦 Extracting {archive_path.name}...")
            
            # Extract
            temp_dir.mkdir(exist_ok=True)
            
            if not self.extract_archive(archive_path, temp_dir):
                print(f"   ❌ Extraction failed")
                if temp_dir.exists():
                    try:
                        shutil.rmtree(temp_dir)
                    except:
                        pass
                return False
            
            if self.verbose:
                print(f"  ✓ Extracted successfully")
            
            # Copy standalone WAV into temp directory
            wav_destination = temp_dir / wav_file.name
            shutil.copy2(wav_file, wav_destination)
            
            if self.verbose:
                print(f"  ✓ Copied {wav_file.name} into stems")
            
            # Delete original archive (whether ZIP or RAR)
            try:
                archive_path.unlink()
                if self.verbose:
                    print(f"  🗑️  Deleted original {archive_path.name}")
            except:
                pass
            
            # Create new compressed ZIP with everything
            with zipfile.ZipFile(final_zip, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(temp_dir)
                        zipf.write(file_path, arcname)
            
            if self.verbose:
                new_size = final_zip.stat().st_size / (1024 * 1024)
                print(f"  ✅ Created: {final_zip.name} ({new_size:.1f} MB with WAV + stems)")
            else:
                print(f"   ✅ Processed stems archive")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error processing archive: {e}")
            if self.verbose:
                import traceback
                traceback.print_exc()
            return False
            
        finally:
            # ALWAYS clean up temp
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                    if self.verbose:
                        print(f"  🧹 Cleaned up temp folder")
                except:
                    try:
                        shutil.rmtree(temp_dir, ignore_errors=True)
                    except:
                        pass


    def extract_and_download_beat(self, beat_element, beat_index, total_beats, skip_existing=True):
        """Extract beat info and download files"""
        beat_data = {"index": beat_index, "title": "", "bpm": "", "tags": [], "creation_date": ""}
        
        try:
            full_title_text = None
            
            # Method 1: JavaScript extraction with textContent
            if not full_title_text:
                try:
                    full_title_text = self.driver.execute_script("""
                        var element = arguments[0];
                        var titleSpan = element.querySelector('span.title, span[data-cy^="title-span-"]');
                        if (titleSpan) {
                            return (titleSpan.textContent || titleSpan.innerText || '').trim();
                        }
                        return null;
                    """, beat_element)
                    if full_title_text and len(full_title_text) > 3:
                        if self.verbose:
                            print(f"  [DEBUG] Title via JavaScript: {full_title_text}")
                except:
                    pass
            
            # Method 2: textContent attribute
            if not full_title_text:
                try:
                    title_elements = beat_element.find_elements(By.CSS_SELECTOR, "span.title, span[data-cy^='title-span-']")
                    for title_el in title_elements:
                        text = title_el.get_attribute('textContent')
                        if text and text.strip() and len(text.strip()) > 3:
                            full_title_text = text.strip()
                            break
                except:
                    pass
            
            if not full_title_text:
                try:
                    title_elements = beat_element.find_elements(By.CSS_SELECTOR, "span.title, span[data-cy^='title-span-']")
                    for title_el in title_elements:
                        text = title_el.get_attribute('innerText')
                        if text and text.strip() and len(text.strip()) > 3:
                            full_title_text = text.strip()
                            break
                except:
                    pass
            
            if not full_title_text:
                try:
                    full_title_text = self.driver.execute_script("""
                        var element = arguments[0];
                        var links = element.querySelectorAll('a');
                        for (var i = 0; i < links.length; i++) {
                            var text = (links[i].textContent || links[i].innerText || '').trim();
                            if (text && text.length > 10 && text.indexOf('-') > -1) {
                                var upper = text.toUpperCase();
                                if (upper.indexOf('PUBLISHED') === -1 && 
                                    upper.indexOf('DRAFT') === -1) {
                                    return text;
                                }
                            }
                        }
                        return null;
                    """, beat_element)
                    if full_title_text:
                        full_title_text = full_title_text.strip()
                except:
                    pass
            
            if not full_title_text:
                try:
                    all_text = self.driver.execute_script("""
                        return (arguments[0].textContent || arguments[0].innerText || '').trim();
                    """, beat_element)
                    
                    if all_text:
                        lines = [line.strip() for line in all_text.split('\n') if line.strip()]
                        for line in lines:
                            if len(line) > 10 and '-' in line:
                                if not any(kw in line.upper() for kw in ['PUBLISHED', 'DRAFT', 'BPM', 'MP3', 'WAV']):
                                    full_title_text = line
                                    break
                except:
                    pass
            
            if not full_title_text or full_title_text == "N/A" or len(full_title_text) < 3:
                beat_data["title"] = f"Beat_{beat_index}"
                beat_data["tags"] = []
            else:
                if " - " in full_title_text:
                    parts = full_title_text.split(" - ", 1)
                    beat_data["title"] = self.sanitize_filename(full_title_text)
                    tags_part = parts[1]
                    tags_part = re.sub(r'\s*(type beat|beat)\s*', '', tags_part, flags=re.IGNORECASE).strip()
                    beat_data["tags"] = [tag.strip().lower() for tag in re.split(r'\s*[x,]\s*', tags_part, flags=re.IGNORECASE) if tag.strip()]
                else:
                    beat_data["title"] = self.sanitize_filename(full_title_text)
                    beat_data["tags"] = []
            
            safe_beat_name = beat_data['title']
            beat_folder = self.download_folder / safe_beat_name
            
            # Check folder structure ONLY (no progress file check)
            if skip_existing and beat_folder.exists():
                mp3_file = None
                wav_file = None
                stems_archive = None
                
                # Find files (case-insensitive)
                for file in beat_folder.iterdir():
                    if file.is_file():
                        name_lower = file.name.lower()
                        if name_lower.endswith('.mp3') and file.stem.lower() == safe_beat_name.lower():
                            mp3_file = file
                        elif name_lower.endswith('.wav') and file.stem.lower() == safe_beat_name.lower():
                            wav_file = file
                
                stems_archive = self.find_stems_archive(beat_folder, safe_beat_name)
                
                if mp3_file and wav_file and stems_archive:
                    print(f"[{beat_index:03d}] ⏭️  {beat_data['title'][:50]} (already complete)")
                    self.mark_beat_completed(safe_beat_name)
                    return None
            
            beat_folder.mkdir(exist_ok=True)

            # Download artwork
            try:
                artwork_element = beat_element.find_element(By.CSS_SELECTOR, "img")
                artwork_url = artwork_element.get_attribute('src')

                if artwork_url:
                    response = requests.get(artwork_url, stream=True)
                    response.raise_for_status()
                    file_extension = Path(artwork_url).suffix if Path(artwork_url).suffix else '.jpg'
                    artwork_filename = f"{safe_beat_name}_artwork{file_extension}"
                    artwork_path = beat_folder / artwork_filename

                    with open(artwork_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
            except Exception as e:
                if self.verbose:
                    print(f"  ⚠️ Artwork not downloaded: {e}")
            
            beat_data["bpm"] = self.extract_bpm_robust(beat_element, beat_index)
            beat_data["creation_date"] = self.extract_creation_date_robust(beat_element, beat_index)
            
            print(f"🎵 [{beat_index:03d}] Processing: {beat_data['title'][:45]}...", end='', flush=True)
            
            beat_data["downloads"] = self.download_beat_files(beat_element, beat_data['title'], beat_folder)

            # Process stems archive (extract + add WAV + rezip)
            self.process_stems_archive(beat_folder, safe_beat_name)
            
            # IMMEDIATE VERIFICATION after download
            print("\n   📋 Verifying files...")
            
            # Check what we have
            mp3_file = None
            wav_file = None
            stems_archive = None
            artwork_file = None
            csv_file = None
            
            for file in beat_folder.iterdir():
                if file.is_file():
                    name_lower = file.name.lower()
                    if name_lower.endswith('.mp3'):
                        mp3_file = file
                        print(f"   ✓ MP3: {file.name}")
                    elif name_lower.endswith('.wav'):
                        wav_file = file
                        print(f"   ✓ WAV: {file.name}")
                    elif name_lower.endswith(('.jpg', '.jpeg', '.png')):
                        artwork_file = file
                        print(f"   ✓ Artwork: {file.name}")
                    elif name_lower.endswith('.csv'):
                        csv_file = file
                        print(f"   ✓ Metadata: {file.name}")
            
            stems_archive = self.find_stems_archive(beat_folder, safe_beat_name)
            if stems_archive:
                print(f"   ✓ STEMS: {stems_archive.name}")
            
            # CRITICAL: Check for leftover temp folder (indicates corruption)
            temp_folder = beat_folder / f"{safe_beat_name}_stems_temp"
            if temp_folder.exists():
                print(f"   ⚠️  WARNING: Temp folder found - archive may be corrupted!")
                print(f"   ⚠️  You can delete: {temp_folder.name}")
            
            # Check what's missing
            missing = []
            if not mp3_file:
                missing.append('mp3')
                print(f"   ⚠️  MP3 missing")
            if not wav_file:
                missing.append('wav')
                print(f"   ⚠️  WAV missing")
            if not stems_archive:
                missing.append('stems')
                print(f"   ⚠️  STEMS missing")
            
            if missing:
                print(f"   🔄 Retrying {len(missing)} missing file(s)...")
                retry_success = self.retry_missing_files(beat_element, beat_folder, safe_beat_name, missing)
                
                # Re-check after retry
                if retry_success:
                    for file_type in missing:
                        if file_type == 'mp3' and any(f.name.lower().endswith('.mp3') for f in beat_folder.iterdir()):
                            print(f"   ✓ MP3 downloaded (retry successful)")
                        elif file_type == 'wav' and any(f.name.lower().endswith('.wav') for f in beat_folder.iterdir()):
                            print(f"   ✓ WAV downloaded (retry successful)")
                        elif file_type == 'stems' and self.find_stems_archive(beat_folder, safe_beat_name):
                            print(f"   ✓ STEMS downloaded (retry successful)")
                
                if 'wav' in missing or 'stems' in missing:
                    self.process_stems_archive(beat_folder, safe_beat_name)
            
            # Final verdict
            mp3_ok = any(f.name.lower().endswith('.mp3') for f in beat_folder.iterdir())
            wav_ok = any(f.name.lower().endswith('.wav') for f in beat_folder.iterdir())
            stems_ok = self.find_stems_archive(beat_folder, safe_beat_name) is not None
            
            if mp3_ok and wav_ok and stems_ok:
                print(f"   ✅ Beat complete!\n")
            else:
                still_missing = []
                if not mp3_ok:
                    still_missing.append('MP3')
                if not wav_ok:
                    still_missing.append('WAV')
                if not stems_ok:
                    still_missing.append('STEMS')
                print(f"   ⚠️  Still missing: {', '.join(still_missing)} (will skip)\n")

            # Save metadata (CSV with title, BPM, tags, creation_date)
            flat_data = {
                "title": beat_data.get("title", ""),
                "bpm": re.sub(r'\D', '', beat_data.get("bpm", "")),
                "tags": ", ".join(beat_data.get("tags", [])),
                "creation_date": beat_data.get("creation_date", ""),
            }
            df = pd.DataFrame([flat_data])
            csv_path = beat_folder / f"{safe_beat_name}_metadata.csv"
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            
            # Mark as completed (metadata only)
            self.mark_beat_completed(safe_beat_name)

        except Exception as e:
            print(f"❌ Error on beat {beat_index:03d}: {e}")
            beat_data["error"] = str(e)
        
        return beat_data

    def get_beat_names_preview(self):
        """Get list of all available beat names"""
        time.sleep(1.5)
        
        beat_elements = self.driver.find_elements(By.CSS_SELECTOR, "studio-list-item")
        beat_names = []
        
        for idx, element in enumerate(beat_elements, 1):
            try:
                beat_name = None
                
                if not beat_name:
                    try:
                        title_elements = element.find_elements(By.CSS_SELECTOR, "span.title, span[data-cy^='title-span-']")
                        for title_el in title_elements:
                            text = title_el.get_attribute('textContent')
                            if text and text.strip() and len(text.strip()) > 3:
                                beat_name = text.strip()
                                if self.verbose and idx <= 3:
                                    print(f"  [DEBUG] Beat {idx} title via textContent: {beat_name}")
                                break
                    except:
                        pass
                
                if not beat_name:
                    try:
                        title_elements = element.find_elements(By.CSS_SELECTOR, "span.title, span[data-cy^='title-span-']")
                        for title_el in title_elements:
                            text = title_el.get_attribute('innerText')
                            if text and text.strip() and len(text.strip()) > 3:
                                beat_name = text.strip()
                                if self.verbose and idx <= 3:
                                    print(f"  [DEBUG] Beat {idx} title via innerText: {beat_name}")
                                break
                    except:
                        pass
                
                if not beat_name:
                    try:
                        beat_name = self.driver.execute_script("""
                            var element = arguments[0];
                            var titleSpan = element.querySelector('span.title, span[data-cy^="title-span-"]');
                            return titleSpan ? (titleSpan.textContent || titleSpan.innerText) : null;
                        """, element)
                        if beat_name:
                            beat_name = beat_name.strip()
                            if self.verbose and idx <= 3:
                                print(f"  [DEBUG] Beat {idx} title via JavaScript: {beat_name}")
                    except:
                        pass
                
                if not beat_name:
                    try:
                        beat_name = self.driver.execute_script("""
                            var element = arguments[0];
                            var links = element.querySelectorAll('a');
                            for (var i = 0; i < links.length; i++) {
                                var text = (links[i].textContent || links[i].innerText || '').trim();
                                if (text && text.length > 10 && text.indexOf('-') > -1) {
                                    var upper = text.toUpperCase();
                                    if (upper.indexOf('PUBLISHED') === -1 && 
                                        upper.indexOf('DRAFT') === -1 && 
                                        upper.indexOf('HTTP') === -1) {
                                        return text;
                                    }
                                }
                            }
                            return null;
                        """, element)
                        if beat_name:
                            beat_name = beat_name.strip()
                            if self.verbose and idx <= 3:
                                print(f"  [DEBUG] Beat {idx} title via JS link search: {beat_name}")
                    except:
                        pass
                
                if not beat_name:
                    try:
                        full_text = self.driver.execute_script("""
                            return (arguments[0].textContent || arguments[0].innerText || '').trim();
                        """, element)
                        
                        if full_text:
                            lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                            for line in lines:
                                if len(line) > 10 and '-' in line:
                                    if not any(kw in line.upper() for kw in ['PUBLISHED', 'DRAFT', 'BPM', 'MP3', 'WAV', 'RAR', 'ZIP']):
                                        beat_name = line
                                        if self.verbose and idx <= 3:
                                            print(f"  [DEBUG] Beat {idx} title via text parsing: {beat_name}")
                                        break
                    except:
                        pass
                
                if beat_name and beat_name != "":
                    beat_names.append({"index": idx, "name": beat_name})
                else:
                    beat_names.append({"index": idx, "name": f"Unknown Beat {idx}"})
                    if self.verbose:
                        print(f"  ⚠️ Could not extract title for beat {idx}")
                    
            except Exception as e:
                if self.verbose:
                    print(f"  ⚠️ Error extracting name for beat {idx}: {e}")
                beat_names.append({"index": idx, "name": f"Unknown Beat {idx}"})
        
        return beat_names

    def display_beats_list(self, beat_names):
        """Display formatted list of available beats with download status"""
        print(f"\n📊 Found {len(beat_names)} beats:")
        print("=" * 70)
        
        # First pass: Check status of ALL beats
        already_downloaded = []
        partially_downloaded = []
        not_downloaded = []
        
        for beat in beat_names:
            beat_name = beat['name']
            safe_beat_name = self.sanitize_filename(beat_name)
            beat_folder = self.download_folder / safe_beat_name
            
            if beat_folder.exists():
                mp3_file = None
                wav_file = None
                
                for file in beat_folder.iterdir():
                    if file.is_file():
                        name_lower = file.name.lower()
                        if name_lower.endswith('.mp3'):
                            mp3_file = file
                        elif name_lower.endswith('.wav'):
                            wav_file = file
                
                stems_archive = self.find_stems_archive(beat_folder, safe_beat_name)
                
                if mp3_file and wav_file and stems_archive:
                    already_downloaded.append(beat['index'])
                else:
                    partially_downloaded.append(beat['index'])
            else:
                not_downloaded.append(beat['index'])
        
        # Second pass: Display first 20 with status
        for beat in beat_names[:20]:
            beat_index = beat['index']
            beat_name = beat['name']
            
            if beat_index in already_downloaded:
                status = "✅"
            elif beat_index in partially_downloaded:
                status = "⚠️ "
            else:
                status = "  "
            
            print(f"  {status} {beat_index:3d}. {beat_name}")
        
        # Show summary if there are more than 20 beats
        if len(beat_names) > 20:
            print(f"  ... and {len(beat_names) - 20} more")
            
            # Show which beats beyond #20 are already downloaded
            already_downloaded_beyond_20 = [idx for idx in already_downloaded if idx > 20]
            if already_downloaded_beyond_20:
                # Group consecutive numbers for cleaner display
                ranges = self._group_consecutive(already_downloaded_beyond_20)
                print(f"      (Already downloaded: {ranges})")
        
        print("=" * 70)
        print(f"  ✅ Already downloaded: {len(already_downloaded)} beats")
        print(f"  ⚠️  Partially downloaded: {len(partially_downloaded)} beats")
        print(f"  📥 Not downloaded: {len(not_downloaded)} beats")
        print("=" * 70)
    
    def _group_consecutive(self, numbers):
        """Group consecutive numbers into ranges for display (e.g., [1,2,3,7,8,9] -> '1-3, 7-9')"""
        if not numbers:
            return ""
        
        numbers = sorted(numbers)
        ranges = []
        start = numbers[0]
        end = numbers[0]
        
        for num in numbers[1:]:
            if num == end + 1:
                end = num
            else:
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = num
                end = num
        
        # Add the last range
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")
        
        return ", ".join(ranges)

    def get_download_mode(self, total_beats):
        """Interactive menu to choose download mode"""
        print(f"\n📥 Download Options:")
        print(f"  1. Download all {total_beats} beats (skip existing)")
        print(f"  2. Download first N beats (skip existing)")
        print(f"  3. Download range (e.g., beats 1-50)")
        
        while True:
            try:
                choice = input("\nYour choice (1-3): ").strip()
                
                if choice == "1":
                    return {"mode": "all", "count": total_beats}
                
                elif choice == "2":
                    count = int(input(f"How many beats to download (1-{total_beats})? "))
                    if 1 <= count <= total_beats:
                        return {"mode": "from_start", "count": count}
                    else:
                        print(f"❌ Please enter a number between 1 and {total_beats}")
                
                elif choice == "3":
                    range_input = input(f"Enter range (e.g., 1-50): ").strip()
                    start, end = map(int, range_input.split('-'))
                    if 1 <= start <= end <= total_beats:
                        return {"mode": "range", "start": start, "end": end}
                    else:
                        print(f"❌ Invalid range. Please use 1-{total_beats}")
                
                else:
                    print("❌ Invalid choice. Please enter 1, 2, or 3")
                    
            except ValueError:
                print("❌ Invalid input. Please try again")
            except KeyboardInterrupt:
                raise

    def verify_beat_complete(self, beat_folder, safe_beat_name):
        """
        Verify if a beat has all required files
        Returns: (is_complete, missing_files)
        """
        missing_files = []
        
        # Find MP3
        mp3_file = None
        for file in beat_folder.iterdir():
            if file.is_file() and file.name.lower().endswith('.mp3'):
                if file.stem.lower() == safe_beat_name.lower():
                    mp3_file = file
                    break
        
        if not mp3_file:
            missing_files.append('mp3')
        
        # Find WAV
        wav_file = None
        for file in beat_folder.iterdir():
            if file.is_file() and file.name.lower().endswith('.wav'):
                if file.stem.lower() == safe_beat_name.lower():
                    wav_file = file
                    break
        
        if not wav_file:
            missing_files.append('wav')
        
        # Find STEMS archive
        stems_archive = self.find_stems_archive(beat_folder, safe_beat_name)
        
        if not stems_archive:
            missing_files.append('stems')
        else:
            # Check if WAV is inside the archive
            try:
                temp_check_dir = beat_folder / f"_temp_check_{safe_beat_name}"
                if self.extract_archive(stems_archive, temp_check_dir):
                    wav_in_archive = False
                    for file in temp_check_dir.rglob('*'):
                        if file.is_file() and file.name.lower().endswith('.wav'):
                            wav_in_archive = True
                            break
                    
                    shutil.rmtree(temp_check_dir)
                    
                    if not wav_in_archive:
                        missing_files.append('wav-in-archive')
                else:
                    missing_files.append('stems-corrupt')
            except Exception as e:
                if self.verbose:
                    print(f"  ⚠️ Error checking archive: {e}")
                missing_files.append('stems-corrupt')
        
        is_complete = len(missing_files) == 0
        return (is_complete, missing_files)

    def verify_beat_directories(self):
        """Quick verification - checks if MP3, WAV, and STEMS files exist + temp folders"""
        print("\n" + "="*70)
        print("🔍 VERIFICATION")
        print("="*70)
        
        beat_dirs = [d for d in self.download_folder.iterdir() if d.is_dir()]
        
        if not beat_dirs:
            print("\n❌ No beat directories found!")
            return {'total_beats': 0, 'complete_beats': 0, 'incomplete_beats': []}
        
        print(f"\n📊 Checking {len(beat_dirs)} beat(s)...")
        
        incomplete_beats = []
        complete_count = 0
        corrupted_archives = []
        
        for beat_dir in beat_dirs:
            beat_name = beat_dir.name
            issues = []  # ✅ AJOUTÉ - Déclare issues pour chaque beat
            
            mp3_file = None
            wav_file = None
            stems_archive = None
            
            for file in beat_dir.iterdir():
                if file.is_file():
                    name_lower = file.name.lower()
                    if name_lower.endswith('.mp3'):
                        mp3_file = file
                    elif name_lower.endswith('.wav'):
                        wav_file = file
            
            stems_archive = self.find_stems_archive(beat_dir, beat_name)
            
            # Check for temp folders and clean them
            temp_folders = list(beat_dir.glob('*_stems_temp'))
            if temp_folders:
                for temp_folder in temp_folders:
                    try:
                        shutil.rmtree(temp_folder)
                        if self.verbose:
                            print(f"   🧹 Auto-cleaned temp folder: {temp_folder.name}")
                    except Exception as e:
                        # ✅ CORRIGÉ - issues existe maintenant
                        issues.append(f"Temp folder found (could not auto-clean): {temp_folder.name}")
                        corrupted_archives.append(beat_name)  # ✅ AJOUTÉ - Marque comme corrompu
                        if self.verbose:
                            print(f"   ⚠️  Could not clean {temp_folder.name}: {e}")
            
            # Check for missing files
            missing_files = []
            if not mp3_file:
                missing_files.append('mp3')
            if not wav_file:
                missing_files.append('wav')
            if not stems_archive:
                missing_files.append('stems')
            
            # Report beat status
            # ✅ CORRIGÉ - Utilise issues au lieu de temp_folder.exists()
            if missing_files or issues:
                print(f"❌ {beat_name}")
                if missing_files:
                    print(f"   Missing: {', '.join(missing_files)}")
                for issue in issues:  # ✅ AJOUTÉ - Affiche les issues s'il y en a
                    print(f"   ⚠️  {issue}")
                incomplete_beats.append({
                    'name': beat_name,
                    'folder': beat_dir,
                    'missing_files': missing_files
                })
            else:
                complete_count += 1
        
        print("\n" + "="*70)
        print("📋 SUMMARY")
        print("="*70)
        print(f"✅ Complete: {complete_count}/{len(beat_dirs)}")
        print(f"❌ Incomplete: {len(incomplete_beats)}/{len(beat_dirs)}")
        if corrupted_archives:
            print(f"⚠️  Corrupted archives (temp cleanup failed): {len(corrupted_archives)}")
            for beat in corrupted_archives:
                print(f"   • {beat}")
        print("="*70)
        
        return {
            'total_beats': len(beat_dirs),
            'complete_beats': complete_count,
            'incomplete_beats': incomplete_beats,
            'corrupted_archives': corrupted_archives
        }

    def download_mp3_with_new_window(self, beat_url, beat_folder, safe_beat_name):
        """Download MP3 by handling the new window"""
        if not PYAUTOGUI_AVAILABLE:
            print("   ❌ pyautogui required for MP3 download")
            return False
        
        try:
            self.driver.get(beat_url)
            time.sleep(3)
            
            main_window = self.driver.current_window_handle
            
            download_selectors = [
                "button[aria-label='Download']",
                "button.download-btn",
                "a.download-link",
                "//button[contains(text(), 'Download')]",
                "//button[contains(text(), 'Télécharger')]",
                "//a[contains(@href, 'download')]",
                "//button[contains(@class, 'download')]"
            ]
            
            download_button = None
            for selector in download_selectors:
                try:
                    if selector.startswith("//"):
                        download_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        download_button = WebDriverWait(self.driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    break
                except:
                    continue
            
            if not download_button:
                return False
            
            download_button.click()
            time.sleep(2)
            
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda d: len(d.window_handles) > 1
                )
            except:
                return False
            
            all_windows = self.driver.window_handles
            new_window = None
            for window in all_windows:
                if window != main_window:
                    new_window = window
                    break
            
            if not new_window:
                return False
            
            self.driver.switch_to.window(new_window)
            time.sleep(2)
            
            window_size = self.driver.get_window_size()
            window_position = self.driver.get_window_position()
            
            center_x = window_position['x'] + (window_size['width'] // 2)
            center_y = window_position['y'] + (window_size['height'] // 2)
            
            pyautogui.moveTo(center_x, center_y, duration=0.3)
            time.sleep(0.5)
            pyautogui.rightClick()
            time.sleep(1.5)
            
            pyautogui.press('v')
            time.sleep(2)
            
            pyautogui.press('enter')
            time.sleep(2)
            
            pyautogui.press('left')
            time.sleep(0.3)
            pyautogui.press('enter')
            time.sleep(2)
            
            self.driver.close()
            self.driver.switch_to.window(main_window)
            time.sleep(1)
            
            return True
            
        except Exception as e:
            try:
                if len(self.driver.window_handles) > 1:
                    for window in self.driver.window_handles:
                        if window != main_window:
                            self.driver.switch_to.window(window)
                            self.driver.close()
                self.driver.switch_to.window(main_window)
            except:
                pass
            return False

    def redownload_missing_files(self, incomplete_beats_info):
        """
        Re-download missing files for incomplete beats.
        Assumes driver is already open and on the beats page.
        """
        if not incomplete_beats_info:
            return True
        
        print("\n" + "="*70)
        print("🔄 RE-DOWNLOADING MISSING FILES")
        print("="*70)
        
        print(f"\n📥 Processing {len(incomplete_beats_info)} beat(s)...")
        
        # ✅ NOUVEAU - Vérifier si le driver est ouvert et sur la bonne page
        driver_ready = False
        if self.driver:
            try:
                # Vérifie qu'on est sur la page BeatStars
                current_url = self.driver.current_url
                if "beatstars.com" in current_url and "studio" in current_url:
                    print("✅ Browser already on BeatStars page - using existing session")
                    driver_ready = True
                else:
                    print("⚠️  Browser on wrong page - reloading...")
            except:
                print("⚠️  Browser closed - reloading...")
        
        # Si le driver n'est pas prêt, recharge tout
        if not driver_ready:
            print("🔄 Loading BeatStars page...")
            
            # Réinitialiser le driver si nécessaire
            if not self.driver:
                self.setup_secure_driver()
            
            self.navigate_to_beatstars()
            
            print("⏬ Loading all beats (auto-scroll)...")
            self.scroll_to_load_all_beats()
            
            beat_names = self.get_beat_names_preview()
            total_beats = len(beat_names)
            print(f"✅ All beats loaded: {total_beats} total")
        else:
            # ✅ OPTIMISATION - Juste récupérer les éléments déjà chargés
            print("🔄 Using already loaded beats...")
            try:
                beat_names = self.get_beat_names_preview()
                print(f"✅ Found {len(beat_names)} beats on page")
            except:
                print("⚠️  Could not get beat names - reloading...")
                self.navigate_to_beatstars()
                self.scroll_to_load_all_beats()
                beat_names = self.get_beat_names_preview()
        
        # Le reste du code reste identique...
        for beat_info in incomplete_beats_info:
            beat_name = beat_info['name']
            beat_folder = beat_info['folder']
            missing_file_types = beat_info['missing_files']
            
            safe_beat_name = self.sanitize_filename(beat_name)
            
            print(f"\n🎵 {beat_name}")
            print(f"   Missing: {', '.join(missing_file_types).upper()}")
            
            if self.verbose:
                print(f"   🔍 Searching for: '{beat_name}'")
            
            # Find beat element
            beat_element = None
            normalized_target = self.normalize_for_comparison(beat_name)
            
            if self.verbose:
                print(f"   🔍 Normalized search: '{normalized_target}'")
            
            beat_elements = self.driver.find_elements(By.CSS_SELECTOR, "studio-list-item")
            
            if self.verbose:
                print(f"   📊 Checking {len(beat_elements)} beats...")
            
            for idx, element in enumerate(beat_elements):
                try:
                    # Use SAME selectors as main download code!
                    element_name = self.driver.execute_script("""
                        var element = arguments[0];
                        var titleSpan = element.querySelector('span.title, span[data-cy^="title-span-"]');
                        if (titleSpan) {
                            return (titleSpan.textContent || titleSpan.innerText || '').trim();
                        }
                        return '';
                    """, element)
                    
                    if not element_name:
                        continue
                    
                    normalized_found = self.normalize_for_comparison(element_name)
                    
                    # Strategy 1: Exact match
                    if normalized_target == normalized_found:
                        beat_element = element
                        print(f" ✓ Found (exact match) at position {idx+1}")
                        break
                    
                    # Strategy 2: Fuzzy match with 70% similarity
                    if normalized_target in normalized_found or normalized_found in normalized_target:
                        target_words = set(normalized_target.split())
                        found_words = set(normalized_found.split())
                        
                        if target_words and found_words:
                            overlap = len(target_words & found_words)
                            similarity = overlap / max(len(target_words), len(found_words))
                            
                            if similarity > 0.7:
                                beat_element = element
                                print(f" ✓ Found (fuzzy {similarity:.0%}) at position {idx+1}")
                                break
                except:
                    continue
            
            if not beat_element:
                print(f" ✗ NOT FOUND")
                if self.verbose:
                    print(f"   💡 Searched for: '{normalized_target}'")
                    print(f"   💡 Try checking the beat name on BeatStars web page")
                    print(f"   💡 First 3 beats on page:")
                    for i, elem in enumerate(beat_elements[:3]):
                        try:
                            name = self.driver.execute_script("""
                                var element = arguments[0];
                                var titleSpan = element.querySelector('span.title, span[data-cy^="title-span-"]');
                                return titleSpan ? (titleSpan.textContent || titleSpan.innerText || '').trim() : '';
                            """, elem)
                            print(f"      {i+1}. {name}")
                        except:
                            pass
                continue
            
            # Scroll to beat
            self.driver.execute_script("arguments[0].scrollIntoView(true);", beat_element)
            time.sleep(0.4)
            
            # Retry missing files
            print(f"   🔄 Retrying {len(missing_file_types)} file(s)...")
            retry_success = self.retry_missing_files(beat_element, beat_folder, safe_beat_name, missing_file_types)
            
            # Check results
            downloaded = []
            for file_type in missing_file_types:
                if file_type == 'mp3' and any(f.name.lower().endswith('.mp3') for f in beat_folder.iterdir()):
                    downloaded.append('MP3')
                    print(f"   ✓ MP3 downloaded")
                elif file_type == 'wav' and any(f.name.lower().endswith('.wav') for f in beat_folder.iterdir()):
                    downloaded.append('WAV')
                    print(f"   ✓ WAV downloaded")
                elif file_type == 'stems' and self.find_stems_archive(beat_folder, safe_beat_name):
                    downloaded.append('STEMS')
                    print(f"   ✓ STEMS downloaded")

            # ✅ Process stems archive if needed
            # Cas 1: STEMS téléchargé → extraire et créer ZIP avec WAV + stems
            # Cas 2: WAV téléchargé ET archive stems existe → recréer ZIP pour inclure nouveau WAV
            if 'STEMS' in downloaded:
                # Stems téléchargé, on traite l'archive
                self.process_stems_archive(beat_folder, safe_beat_name)
            elif 'WAV' in downloaded:
                # WAV téléchargé, vérifier si une archive stems existe
                stems_archive = self.find_stems_archive(beat_folder, safe_beat_name)
                if stems_archive:
                    # Archive existe, supprimer le ZIP existant pour le recréer avec le nouveau WAV
                    existing_zip = beat_folder / f"{safe_beat_name}_stems.zip"
                    if existing_zip.exists():
                        try:
                            existing_zip.unlink()
                            print(f"   🔄 Updating stems ZIP with new WAV...")
                        except:
                            pass
                    self.process_stems_archive(beat_folder, safe_beat_name)

            # Final verdict
            if len(downloaded) == len(missing_file_types):
                print(f"   ✅ All files recovered!")
            elif len(downloaded) > 0:
                print(f"   ⚠️  Partial success: {len(downloaded)}/{len(missing_file_types)} files")
            else:
                print(f"   ❌ Download failed")
        
        print("\n✅ Re-download process complete!")
        
        return True

    def scrape_beats(self, max_beats=999, interactive=True):
        """Main scraping method - checks folders, NOT progress file"""
        print("\n🔍 Analyzing available beats...")
        
        if self.verbose:
            try:
                first_beat = self.driver.find_element(By.CSS_SELECTOR, "studio-list-item")
                print("\n[DEBUG] First beat HTML structure:")
                print(first_beat.get_attribute('outerHTML')[:500])
            except:
                pass
        
        try:
            beat_names = self.get_beat_names_preview()
            total_beats = len(beat_names)
            
            if total_beats == 0:
                print("❌ No beats found!")
                return
            
            if self.verbose:
                print(f"\n[DEBUG] First 3 beat names extracted:")
                for beat in beat_names[:3]:
                    print(f"  {beat['index']}. {beat['name']}")
            
            beats_to_process = []
            
            if interactive:
                self.display_beats_list(beat_names)
                download_config = self.get_download_mode(total_beats)
                
                if download_config["mode"] == "from_start":
                    beats_to_process = beat_names[:download_config["count"]]
                    print(f"\n📥 Downloading first {download_config['count']} beats (skipping existing)...")
                elif download_config["mode"] == "all":
                    beats_to_process = beat_names
                    print(f"\n📥 Downloading all {total_beats} beats (skipping existing)...")
                elif download_config["mode"] == "range":
                    start = download_config["start"]
                    end = download_config["end"]
                    beats_to_process = beat_names[start-1:end]
                    print(f"\n📥 Downloading beats {start} to {end} (skipping existing)...")
            else:
                limit = min(max_beats, total_beats)
                beats_to_process = beat_names[:limit]
                print(f"📊 Processing {limit} beats (skipping existing)\n")
            
            beat_elements = self.driver.find_elements(By.CSS_SELECTOR, "studio-list-item")
            
            downloaded_count = 0
            skipped_count = 0
            
            for beat_info in beats_to_process:
                beat_idx = beat_info['index'] - 1
                
                # Refresh beat elements to avoid stale references
                try:
                    self.driver.execute_script("window.scrollTo(0, 0);")
                    time.sleep(0.4) 
                    
                    beat_elements = self.driver.find_elements(By.CSS_SELECTOR, "studio-list-item")
                    
                    if beat_idx >= len(beat_elements):
                        print(f"⚠️  Beat index {beat_idx+1} out of range after refresh, skipping")
                        continue
                        
                except Exception as e:
                    if self.verbose:
                        print(f"⚠️  Could not refresh beat elements: {e}")
                
                if beat_idx < len(beat_elements):
                    result = self.extract_and_download_beat(
                        beat_elements[beat_idx], 
                        beat_info['index'],
                        len(beats_to_process),
                        skip_existing=True
                    )
                    if result is None:
                        skipped_count += 1
                    else:
                        downloaded_count += 1

            print(f"\n✅ Download Complete!")
            print(f"   📥 Downloaded: {downloaded_count} beats")
            print(f"   ⏭️  Skipped (existing): {skipped_count} beats")
            print(f"   📊 Total processed: {len(beats_to_process)} beats")
            
            # Quick verification
            verification_results = self.verify_beat_directories()
            
            # Offer to re-download missing files
            if verification_results['incomplete_beats']:
                print(f"\n⚠️  Found {len(verification_results['incomplete_beats'])} incomplete beat(s)")
                user_input = input("Would you like to re-download missing files? (y/n): ").strip().lower()
                
                if user_input == 'y':
                    self.redownload_missing_files(verification_results['incomplete_beats'])
                    print("✅ Re-download complete!")
                else:
                    print("⏭️  Skipping re-download.")
            
        except Exception as e:
            print(f"❌ Scraping error: {e}")
            print("💾 Progress metadata saved")
    
    def close(self):
        print("\n🔒 Closing...")
        if self.driver: 
            self.driver.quit()
        self.cleanup()
        print("✅ Session terminated")

def main():
    """Standalone execution"""
    scraper = SecureBeatstarsScraper()  # Clean output by default
    try:
        scraper.setup_secure_driver()
        scraper.navigate_to_beatstars()
        scraper.scrape_beats(interactive=True)
    except KeyboardInterrupt: 
        print("\n⛔ User interruption")
    except Exception as e: 
        print(f"\n❌ Critical error: {e}")
    finally: 
        scraper.close()

if __name__ == "__main__":
    main()