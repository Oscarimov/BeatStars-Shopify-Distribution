"""
UNIFIED BUILD SCRIPT - BeatStars Shopify Tools
Builds BOTH executables with shared Playwright browsers
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Windows consoles default to cp1252, which can't encode the emoji used
# throughout this script's prints - force UTF-8 so it never crashes.
if sys.platform == 'win32':
    try:
        os.system('chcp 65001 > nul')
    except Exception:
        pass
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

def check_prerequisites():
    """Check if all requirements are met"""
    print("=" * 70)
    print("  PRE-BUILD CHECKS".center(70))
    print("=" * 70)
    
    errors = []
    warnings = []
    
    # Check Python version
    if sys.version_info < (3, 8):
        errors.append("Python 3.8+ required")
    else:
        print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Check required files for main tool
    required_files = {
        'main.py': 'Main tool entry point',
        'scraper.py': 'BeatStars scraper',
        'uploader.py': 'Shopify uploader',
        'single_upload.py': 'Single upload tool',
    }

    for file, description in required_files.items():
        if Path(file).exists():
            print(f"✅ {file} - {description}")
        else:
            print(f"❌ {file} - NOT FOUND")
            errors.append(f"Missing file: {file}")

    # The build always ships config.example.json (the neutral, tracked
    # template) as the distributed config.json - never the developer's own
    # local config.json, which accumulates real personal data over time.
    if Path('config.example.json').exists():
        print(f"✅ config.example.json - Configuration template")
    else:
        print(f"❌ config.example.json - NOT FOUND")
        errors.append("Missing file: config.example.json")
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller installed")
    except ImportError:
        print("❌ PyInstaller - NOT INSTALLED")
        errors.append("PyInstaller not installed (pip install pyinstaller)")
    
    # The tool drives the user's real, installed Google Chrome (channel="chrome")
    # for the Shopify features - it no longer launches Playwright's own bundled
    # Chromium at all, so there's nothing to bundle here anymore. Just confirm
    # Chrome is installed on THIS machine so the launch self-test below is
    # meaningful (end users need their own Chrome installed too - that's
    # documented in the README, not something we can bundle for them).
    chrome_candidates = [
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    if not any(p.exists() for p in chrome_candidates):
        print("❌ Google Chrome NOT FOUND on this machine")
        errors.append("Google Chrome not found. Install it from https://www.google.com/chrome/")
    else:
        print("✅ Google Chrome found")

        # Confirm Playwright can actually drive it (catches a missing VC++
        # Redistributable or a broken Playwright driver install before it
        # becomes an end-user support ticket).
        verify_script = Path(__file__).parent / '_verify_playwright.py'
        result = subprocess.run([sys.executable, str(verify_script)], capture_output=True, text=True)
        if result.returncode != 0:
            print("❌ Chrome is installed but Playwright FAILED to launch it")
            print(result.stdout.strip())
            print(result.stderr.strip())
            errors.append(
                "Playwright can't launch Chrome (missing VC++ Redistributable or a "
                "broken Playwright install). Run scripts/setup_playwright.bat to repair it."
            )
        else:
            print("✅ Chrome launch self-test passed")

    login_bat = Path('login_shopify_chrome.bat')
    if login_bat.exists():
        print(f"✅ {login_bat.name} - one-time Shopify login helper")
    else:
        print(f"❌ {login_bat.name} - NOT FOUND")
        errors.append(f"Missing file: {login_bat.name}")
    
    if errors:
        print("\n" + "=" * 70)
        print("❌ BUILD CANNOT PROCEED")
        print("=" * 70)
        for error in errors:
            print(f"  • {error}")
        print()
        return False
    
    print("\n✅ All prerequisites met")
    return True

def build_main_tool():
    """Build the main BeatStars-Shopify tool"""
    print("\n" + "=" * 70)
    print("  BUILDING MAIN TOOL".center(70))
    print("=" * 70)
    print()
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--console',
        '--name=BeatStars-Shopify-Tool',
        '--hidden-import=selenium',
        '--hidden-import=selenium.webdriver',
        '--hidden-import=selenium.webdriver.chrome',
        '--hidden-import=pandas',
        '--hidden-import=requests',
        '--hidden-import=playwright',
        '--hidden-import=playwright.async_api',
        '--hidden-import=playwright.sync_api',
        '--hidden-import=nest_asyncio',
        '--hidden-import=asyncio',
        '--hidden-import=mutagen',
        '--hidden-import=mutagen.mp3',
        '--hidden-import=pyautogui',
        '--hidden-import=rarfile',
        '--hidden-import=py7zr',
        '--collect-all=selenium',
        '--collect-all=playwright',
        '--collect-all=pyautogui',
        '--noupx',
        '--clean',
        'main.py'
    ]
    
    print("📦 Building main tool...")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        exe_path = Path('dist') / 'BeatStars-Shopify-Tool.exe'
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"✅ Main tool built: {size_mb:.1f} MB")
            return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False

def build_single_upload_tool():
    """Build the single upload tool"""
    print("\n" + "=" * 70)
    print("  BUILDING SINGLE UPLOAD TOOL".center(70))
    print("=" * 70)
    print()
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--console',
        '--name=Single-Upload-Tool',
        '--hidden-import=selenium',
        '--hidden-import=pandas',
        '--hidden-import=requests',
        '--hidden-import=playwright',
        '--hidden-import=playwright.async_api',
        '--hidden-import=nest_asyncio',
        '--hidden-import=mutagen',
        '--hidden-import=tkinter',
        '--hidden-import=tkinter.filedialog',
        '--hidden-import=tkinter.simpledialog',
        '--hidden-import=tkinter.messagebox',
        '--hidden-import=pyautogui',
        '--hidden-import=rarfile',
        '--hidden-import=py7zr',
        '--collect-all=playwright',
        '--collect-all=tkinter',
        '--noupx',
        '--clean',
        'single_upload.py'
    ]
    
    print("📦 Building single upload tool...")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        exe_path = Path('dist') / 'Single-Upload-Tool.exe'
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"✅ Single upload tool built: {size_mb:.1f} MB")
            return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        return False

def create_distribution():
    """Create complete distribution package"""
    print("\n" + "=" * 70)
    print("  CREATING DISTRIBUTION PACKAGE".center(70))
    print("=" * 70)
    print()
    
    dist_folder = Path('BeatStars-Shopify-Complete')
    dist_folder.mkdir(exist_ok=True)
    
    # Copy executables
    for exe in ['BeatStars-Shopify-Tool.exe', 'Single-Upload-Tool.exe']:
        src = Path('dist') / exe
        if src.exists():
            shutil.copy2(src, dist_folder / exe)
            print(f"   ✓ {exe}")
    
    # Copy the one-time Shopify login helper (drives the user's real Chrome -
    # see README - the tool no longer bundles its own browser at all)
    login_bat = Path('login_shopify_chrome.bat')
    if login_bat.exists():
        shutil.copy2(login_bat, dist_folder / login_bat.name)
        print(f"   ✓ {login_bat.name}")

    # Always ship the tracked, neutral template - NEVER the developer's own
    # local config.json. That file accumulates real personal data over time
    # (artist name, real collection name, credentials, ...) and trying to
    # scrub it field-by-field is exactly how a real vendor name and
    # collection name leaked into a build once already. config.example.json
    # is deliberately kept generic for this purpose.
    config_source = Path('config.example.json')
    if config_source.exists():
        shutil.copy2(config_source, dist_folder / 'config.json')
        print(f"   ✓ config.json (template, from {config_source.name})")
    else:
        print(f"   ⚠️ {config_source} not found - no config.json shipped")
    
    # Copy README files (they live at the repo root, one level up from scripts/)
    for readme in ['README.md', 'README_EN.md']:
        readme_path = Path('..') / readme
        if readme_path.exists():
            shutil.copy2(readme_path, dist_folder / readme)
            print(f"   ✓ {readme}")
        else:
            print(f"   ⚠️ {readme} not found at {readme_path.resolve()}")
    
    print(f"\n✅ Distribution created: {dist_folder}/")
    print(f"   Total size: ~{sum(f.stat().st_size for f in dist_folder.rglob('*') if f.is_file()) / (1024*1024):.0f} MB")

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  UNIFIED BUILD - BEATSTARS SHOPIFY TOOLS".center(70))
    print("  Builds BOTH executables with shared browsers".center(70))
    print("=" * 70)
    
    try:
        # Check prerequisites
        if not check_prerequisites():
            input("\nPress ENTER to exit...")
            sys.exit(1)
        
        # Build both tools
        print("\n🔨 Starting build process...\n")
        
        success_main = build_main_tool()
        success_single = build_single_upload_tool()
        
        if not (success_main and success_single):
            print("\n❌ One or more builds failed!")
            input("\nPress ENTER to exit...")
            sys.exit(1)

        # Create distribution
        create_distribution()

        # Summary
        print("\n" + "=" * 70)
        print("  ✅ BUILD COMPLETE".center(70))
        print("=" * 70)

        print("\n📦 DISTRIBUTION CONTENTS:")
        print("   BeatStars-Shopify-Complete/")
        print("   ├── BeatStars-Shopify-Tool.exe     (batch uploads from BeatStars)")
        print("   ├── Single-Upload-Tool.exe         (manual single uploads)")
        print("   ├── login_shopify_chrome.bat       (one-time Shopify login)")
        print("   ├── config.json                    (must be edited by user)")
        print("   ├── README.md")
        print("   └── README_EN.md")

        print("\n👤 USER INSTRUCTIONS:")
        print("   1. Extract the entire folder (keep structure)")
        print("   2. Install Google Chrome if not already installed")
        print("   3. Edit config.json with credentials")
        print("   4. Run login_shopify_chrome.bat once and log into Shopify")
        print("   5. Run either executable:")
        print("      • BeatStars-Shopify-Tool.exe → Batch uploads")
        print("      • Single-Upload-Tool.exe → Manual uploads")

        print("\n✅ No bundled browser - the tool drives the user's real Chrome")
        print("✅ Works on any Windows PC with Chrome installed (no Python required)")
        
    except KeyboardInterrupt:
        print("\n\n⛔ Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    input("\n\nPress ENTER to exit...")