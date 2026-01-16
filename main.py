import os
import sys
import json
from pathlib import Path
import tempfile

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    print("=" * 70)
    print("  BEATSTARS → SHOPIFY AUTOMATION TOOL".center(70))
    print("  Professional Edition".center(70))
    print("=" * 70)
    print()

def load_config():
    if getattr(sys, 'frozen', False):
        application_path = Path(sys.executable).parent
    else:
        application_path = Path(__file__).parent
    
    config_path = application_path / "config.json"
    
    if not config_path.exists():
        print("❌ ERROR: config.json not found!")
        print(f"📍 Expected location: {config_path}")
        print(f"📍 Looking in: {application_path}")
        input("\nPress ENTER to exit...")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ ERROR: Invalid JSON in config.json: {e}")
        input("\nPress ENTER to exit...")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Cannot read config.json: {e}")
        input("\nPress ENTER to exit...")
        sys.exit(1)

def verify_config(config):
    required_base = {
        'store_url': 'Shopify store URL',
        'beats_folder': 'Beats folder path'
    }
    
    missing = []
    placeholder = []
    
    for field, description in required_base.items():
        value = config.get(field, '')
        if not value:
            missing.append(description)
        elif any(x in str(value).upper() for x in ['YOUR_', 'PLACEHOLDER', 'EXAMPLE', 'VOTRE']):
            placeholder.append(description)
    
    has_legacy = 'access_token' in config and config.get('access_token', '').startswith('shpat_')
    has_new = 'client_id' in config and 'client_secret' in config
    
    if not has_legacy and not has_new:
        missing.append('Authentication (either access_token OR client_id+client_secret)')
    
    if missing:
        print("❌ ERROR: Missing configuration values:")
        for item in missing:
            print(f"   • {item}")
        print("\nPlease edit config.json with your actual values.")
        print("\nAuthentication options:")
        print("  - Legacy mode: 'access_token': 'shpat_...'")
        print("  - New mode (2026+): 'client_id' + 'client_secret'")
        input("\nPress ENTER to exit...")
        sys.exit(1)
    
    if placeholder:
        print("⚠️  WARNING: Configuration contains placeholder values:")
        for item in placeholder:
            print(f"   • {item}")
        response = input("\nContinue anyway? (y/N): ").strip().lower()
        if response != 'y':
            sys.exit(1)
    
    beats_path = Path(config['beats_folder'])
    beats_path.mkdir(parents=True, exist_ok=True)

def show_menu():
    print("\n" + "=" * 70)
    print("  MAIN MENU".center(70))
    print("=" * 70)
    print("\n  1. 📥  Download beats from BeatStars")
    print("  2. 📤  Upload beats to Shopify (requires beats from option 1)")
    print("  3. 🔄  Complete workflow (Download + Upload)")
    print("  4. ⚙️   View configuration")
    print("  5. ❌  Exit")
    print("\n" + "=" * 70)

def show_config(config):
    print("\n" + "=" * 70)
    print("  CONFIGURATION".center(70))
    print("=" * 70)
    
    print(f"\n  🪐 Shopify Store:")
    print(f"     {config.get('store_url', 'Not configured')}")
    
    has_legacy = 'access_token' in config and config.get('access_token', '').startswith('shpat_')
    has_new = 'client_id' in config and 'client_secret' in config
    
    print(f"\n  🔑 Authentication Mode:")
    if has_legacy:
        print(f"     Legacy token (permanent)")
    elif has_new:
        print(f"     Client credentials (auto-refresh 24h)")
    else:
        print(f"     ❌ Not configured")
    
    print(f"\n  📁 Beats Folder:")
    print(f"     {config.get('beats_folder', 'Not configured')}")
    
    print(f"\n  📦 Product Type:")
    print(f"     {config.get('product_type', 'Beat')}")
    
    
    variants = config.get('variants', [])
    if variants:
        print(f"\n  💰 Pricing Variants: ({len(variants)} configured)")
        for v in variants:
            files = ', '.join(v.get('digital_files', []))
            print(f"     • {v.get('name', 'N/A')}: ${v.get('price', '0')} [{files}]")
    
    print(f"\n  🛠 Debug Settings:")
    print(f"     Verbose: {'ON' if config.get('verbose') else 'OFF'}")
    
    print("\n" + "=" * 70)
    input("\nPress ENTER to return to menu...")

def run_scraper(config):
    print("\n" + "=" * 70)
    print("  BEATSTARS DOWNLOAD".center(70))
    print("=" * 70)
    print()
    
    scraper = None
    
    try:
        from scraper import SecureBeatstarsScraper
        
        scraper = SecureBeatstarsScraper(download_folder=config['beats_folder'])
        
        scraper.setup_secure_driver()
        scraper.navigate_to_beatstars()
        
        scraper.scrape_beats(interactive=True)
        
        print("\n✅ Download process completed!")
        return True
        
    except KeyboardInterrupt:
        print("\n\n⛔ Process interrupted by user")
        return False
    except ImportError as e:
        print(f"\n❌ ERROR: Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"\n⚠️ ERROR: {e}")
        if config.get('verbose'):
            import traceback
            traceback.print_exc()
        return False
    finally:
        try:
            if scraper:
                scraper.close()
        except:
            pass

def run_uploader(config):
    print("\n" + "=" * 70)
    print("  SHOPIFY UPLOAD".center(70))
    print("=" * 70)
    print()
    
    beats_path = Path(config['beats_folder'])
    beat_folders = [f for f in beats_path.iterdir() if f.is_dir() and list(f.glob("*_metadata.csv"))]
    
    if not beat_folders:
        print("⚠️  WARNING: No beats found in the beats folder!")
        print(f"📍 Looking in: {beats_path}")
        print("\n💡 You need to download beats first (Option 1) before uploading.")
        print("   Or make sure your beats_folder path in config.json is correct.")
        input("\nPress ENTER to return to menu...")
        return False
    
    print(f"✅ Found {len(beat_folders)} beat(s) ready to upload\n")
    
    temp_config_file = None
    
    try:
        from uploader import ShopifyGraphQLUploader
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
            json.dump(config, f, indent=2)
            temp_config_file = f.name
        
        uploader = ShopifyGraphQLUploader(config_path=temp_config_file)
        
        uploader.process_beats()
        
        print("\n✅ Upload process completed!")
        return True
        
    except KeyboardInterrupt:
        print("\n\n⛔ Process interrupted by user")
        return False
    except ImportError as e:
        print(f"\n❌ ERROR: Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        if 'playwright' in str(e).lower():
            print("\nPlaywright also requires: python -m playwright install")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if temp_config_file:
            try:
                os.unlink(temp_config_file)
            except:
                pass

def main():
    try:
        while True:
            clear_screen()
            print_banner()
            
            config = load_config()
            verify_config(config)
            
            show_menu()
            
            choice = input("\n  → Your choice (1-5): ").strip()
            
            if choice == '1':
                success = run_scraper(config)
                input("\nPress ENTER to continue...")
                
            elif choice == '2':
                success = run_uploader(config)
                input("\nPress ENTER to continue...")
                
            elif choice == '3':
                print("\n" + "=" * 70)
                print("  COMPLETE WORKFLOW".center(70))
                print("=" * 70)
                print("\n  Phase 1: Download from BeatStars")
                print("  Phase 2: Upload to Shopify")
                print("\n" + "=" * 70)
                input("\nPress ENTER to start...")
                
                if run_scraper(config):
                    print("\n✅ Phase 1 complete: Beats downloaded")
                    input("\nPress ENTER to begin Phase 2 (Upload)...")
                    
                    run_uploader(config)
                else:
                    print("\n⚠️ Phase 1 failed. Aborting workflow.")
                
                input("\nPress ENTER to continue...")
                
            elif choice == '4':
                show_config(config)
                
            elif choice == '5':
                print("\n  👋 Goodbye!")
                print()
                break
                
            else:
                print("\n  ⚠️ Invalid choice. Please select 1-5.")
                input("\n  Press ENTER to continue...")
    
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        input("\nPress ENTER to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()