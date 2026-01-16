"""
UNIFIED BUILD SCRIPT - BeatStars Shopify Tools
Builds BOTH executables with shared Playwright browsers
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

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
        'config.json': 'Configuration file'
    }
    
    for file, description in required_files.items():
        if Path(file).exists():
            print(f"✅ {file} - {description}")
        else:
            print(f"❌ {file} - NOT FOUND")
            errors.append(f"Missing file: {file}")
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"✅ PyInstaller installed")
    except ImportError:
        print("❌ PyInstaller - NOT INSTALLED")
        errors.append("PyInstaller not installed (pip install pyinstaller)")
    
    # Check Playwright browsers
    playwright_path = Path.home() / 'AppData' / 'Local' / 'ms-playwright'
    chromium_headless_dirs = list(playwright_path.glob('chromium_headless_shell-*'))
    chromium_full_dirs = list(playwright_path.glob('chromium-[0-9]*'))
    
    all_chromium = chromium_headless_dirs + chromium_full_dirs
    
    if not all_chromium:
        print("❌ Playwright browser NOT INSTALLED")
        errors.append("Playwright browser not found. Run: python -m playwright install chromium")
    else:
        for browser in all_chromium:
            print(f"✅ Playwright browser found: {browser.name}")
    
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

def bundle_playwright_browsers():
    """Bundle Playwright browsers once for both executables"""
    print("\n" + "=" * 70)
    print("  BUNDLING PLAYWRIGHT BROWSERS".center(70))
    print("=" * 70)
    print()
    
    playwright_source = Path.home() / 'AppData' / 'Local' / 'ms-playwright'
    dist_folder = Path('dist')
    playwright_dest = dist_folder / 'ms-playwright'
    
    # Find BOTH chromium directories (headless and full version)
    chromium_headless_dirs = list(playwright_source.glob('chromium_headless_shell-*'))
    chromium_full_dirs = list(playwright_source.glob('chromium-[0-9]*'))
    
    all_chromium_dirs = chromium_headless_dirs + chromium_full_dirs
    
    if not all_chromium_dirs:
        print("❌ No Chromium browser found!")
        return False
    
    print(f"📦 Found {len(all_chromium_dirs)} browser version(s):")
    for browser_dir in all_chromium_dirs:
        size_mb = sum(f.stat().st_size for f in browser_dir.rglob('*') if f.is_file()) / (1024*1024)
        print(f"   • {browser_dir.name} ({size_mb:.1f} MB)")
    
    print(f"\n   Copying to: {playwright_dest}")
    print(f"   This may take 2-3 minutes...\n")
    
    playwright_dest.mkdir(exist_ok=True)
    
    # Copy ALL chromium directories
    for chromium_dir in all_chromium_dirs:
        dest_chromium = playwright_dest / chromium_dir.name
        
        try:
            if dest_chromium.exists():
                shutil.rmtree(dest_chromium)
            
            print(f"   Copying {chromium_dir.name}...")
            shutil.copytree(chromium_dir, dest_chromium)
            print(f"   ✅ {chromium_dir.name} copied")
            
        except Exception as e:
            print(f"   ❌ Failed to copy {chromium_dir.name}: {e}")
            return False
    
    print(f"\n✅ All browsers bundled successfully!")
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
    
    # Copy browsers (shared)
    browsers_src = Path('dist') / 'ms-playwright'
    if browsers_src.exists():
        browsers_dest = dist_folder / 'ms-playwright'
        if browsers_dest.exists():
            shutil.rmtree(browsers_dest)
        shutil.copytree(browsers_src, browsers_dest)
        print(f"   ✓ ms-playwright/ (shared browsers)")
    
    # Copy config template
    if Path('config.json').exists():
        import json
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        config['store_url'] = 'your-store.myshopify.com'
        config['access_token'] = 'shpat_your_token_here'
        config['beats_folder'] = 'C:/Users/YourName/Documents/Beats'
        
        with open(dist_folder / 'config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        print(f"   ✓ config.json (template)")
    
    # Copy README files
    for readme in ['README.md', 'README_FR.md']:
        if Path(readme).exists():
            shutil.copy2(readme, dist_folder / readme)
            print(f"   ✓ {readme}")
    
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
        
        # Bundle browsers (once, shared)
        if not bundle_playwright_browsers():
            print("\n⚠️  WARNING: Browsers not bundled!")
        
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
        print("   ├── ms-playwright/                 (shared browsers, ~150 MB)")
        print("   ├── config.json                    (must be edited by user)")
        print("   ├── README.md")
        print("   └── README_FR.md")
        
        print("\n👤 USER INSTRUCTIONS:")
        print("   1. Extract the entire folder (keep structure)")
        print("   2. Edit config.json with credentials")
        print("   3. Run either executable:")
        print("      • BeatStars-Shopify-Tool.exe → Batch uploads")
        print("      • Single-Upload-Tool.exe → Manual uploads")
        
        print("\n✅ Both tools share the same ms-playwright folder")
        print("✅ No Playwright installation needed by users")
        print("✅ Works on any Windows PC (no Python required)")
        
    except KeyboardInterrupt:
        print("\n\n⛔ Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    input("\n\nPress ENTER to exit...")