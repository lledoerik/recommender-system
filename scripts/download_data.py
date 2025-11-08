"""
Smart Data Downloader for MyAnimeList Dataset

Features:
- Downloads to data/raw/ (inside project)
- Checks if new version available before downloading
- Saves version info to avoid unnecessary downloads
- Self-contained (no external cache dependencies)

Usage:
    python scripts/download_data.py
"""

import kagglehub
import shutil
import json
from pathlib import Path
import sys
import time


# Path configuration (everything relative to project)
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
VERSION_FILE = RAW_DATA_DIR / ".dataset_version.json"

# Kaggle dataset info
DATASET_NAME = "azathoth42/myanimelist"


def get_current_version():
    """
    Get the current dataset version we have downloaded
    
    Returns:
        dict: Version info or None if not downloaded yet
    """
    if not VERSION_FILE.exists():
        return None
    
    try:
        with open(VERSION_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return None


def save_version_info(version, download_path):
    """
    Save version information to track what we have
    """
    version_info = {
        'version': version,
        'dataset': DATASET_NAME,
        'download_path': str(download_path),
        'downloaded_at': time.strftime('%Y-%m-%d %H:%M:%S')
    }
    
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(VERSION_FILE, 'w') as f:
        json.dump(version_info, f, indent=2)


def download_dataset(force=False):
    """
    Download MyAnimeList dataset from Kaggle
    
    Args:
        force (bool): Force download even if version hasn't changed
    
    Returns:
        bool: True if downloaded, False if skipped
    """
    print("\n" + "="*70)
    print("MYANIMELIST DATASET DOWNLOADER")
    print("="*70)
    
    # Check current version
    current_version = get_current_version()
    
    if current_version and not force:
        print(f"\n📦 Current version: {current_version.get('version', 'unknown')}")
        print(f"   Downloaded at: {current_version.get('downloaded_at', 'unknown')}")
        print(f"\n🔍 Checking for updates...")
    else:
        print(f"\n🔍 No local version found. Downloading dataset...")
    
    try:
        # Download dataset (kagglehub downloads to its cache first)
        print(f"\n📥 Downloading {DATASET_NAME}...")
        print(f"   ⚠️  This may take 2-5 minutes depending on your connection...")
        
        # kagglehub will download to its cache
        cache_path = kagglehub.dataset_download(DATASET_NAME)
        cache_path = Path(cache_path)
        
        print(f"\n✓ Dataset downloaded to kagglehub cache")
        print(f"   Cache location: {cache_path}")
        
        # Extract version from path
        # Path format: .../azathoth42/myanimelist/versions/9/
        version_parts = cache_path.parts
        try:
            version_index = version_parts.index('versions')
            version = version_parts[version_index + 1]
        except (ValueError, IndexError):
            version = 'unknown'
        
        # Check if this is a new version
        if current_version and current_version.get('version') == version and not force:
            print(f"\n✅ Already have latest version (v{version})")
            print(f"   No download needed!")
            return False
        
        # Copy to our project's data/raw/ directory
        print(f"\n📁 Copying to project directory...")
        print(f"   Destination: {RAW_DATA_DIR}")
        
        # Clear old raw data if exists
        if RAW_DATA_DIR.exists():
            print(f"   Removing old raw data...")
            for item in RAW_DATA_DIR.iterdir():
                if item.is_file() and item.suffix == '.csv':
                    item.unlink()
        
        RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Copy all CSV files
        csv_files = list(cache_path.glob('*.csv'))
        
        if not csv_files:
            print(f"\n✗ ERROR: No CSV files found in downloaded dataset")
            return False
        
        print(f"\n   Found {len(csv_files)} CSV files:")
        
        for csv_file in csv_files:
            dest_file = RAW_DATA_DIR / csv_file.name
            shutil.copy2(csv_file, dest_file)
            
            file_size = dest_file.stat().st_size / (1024 * 1024)
            print(f"   ✓ {csv_file.name} ({file_size:.1f} MB)")
        
        # Save version info
        save_version_info(version, cache_path)
        
        print(f"\n" + "="*70)
        print("✅ DOWNLOAD COMPLETED!")
        print("="*70)
        print(f"\n📊 Summary:")
        print(f"   Version: {version}")
        print(f"   Files: {len(csv_files)} CSV files")
        print(f"   Location: {RAW_DATA_DIR}")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
        print("\n" + "="*70)
        print("TROUBLESHOOTING")
        print("="*70)
        print("\nIf you see authentication errors:")
        print("  1. Make sure you have a Kaggle account")
        print("  2. Go to https://www.kaggle.com/settings")
        print("  3. Create a new API token (downloads kaggle.json)")
        print("  4. Place kaggle.json in:")
        print("     - Windows: %USERPROFILE%\\.kaggle\\kaggle.json")
        print("     - Linux/Mac: ~/.kaggle/kaggle.json")
        print("="*70)
        
        return False


def list_downloaded_files():
    """
    List all files in raw data directory
    """
    if not RAW_DATA_DIR.exists():
        print(f"\n📁 Raw data directory doesn't exist yet: {RAW_DATA_DIR}")
        return
    
    csv_files = list(RAW_DATA_DIR.glob('*.csv'))
    
    if not csv_files:
        print(f"\n📁 Raw data directory is empty: {RAW_DATA_DIR}")
        return
    
    print(f"\n📁 Files in {RAW_DATA_DIR}:")
    
    total_size = 0
    for csv_file in sorted(csv_files):
        file_size = csv_file.stat().st_size / (1024 * 1024)
        total_size += file_size
        print(f"   {csv_file.name:30s} {file_size:8.1f} MB")
    
    print(f"   {'─'*30} {'─'*8}")
    print(f"   {'TOTAL':30s} {total_size:8.1f} MB")


def main():
    """
    Main function
    """
    print("\n🎬 MYANIMELIST DATA DOWNLOADER")
    
    # Check arguments
    force = '--force' in sys.argv or '-f' in sys.argv
    list_only = '--list' in sys.argv or '-l' in sys.argv
    
    if list_only:
        list_downloaded_files()
        return True
    
    if force:
        print("\n⚠️  Force mode: Will download even if version is current")
    
    start_time = time.time()
    
    # Download
    downloaded = download_dataset(force=force)
    
    elapsed = time.time() - start_time
    
    if downloaded:
        print(f"\n⏱️  Total time: {elapsed:.1f} seconds")
        
        print("\n" + "="*70)
        print("NEXT STEPS")
        print("="*70)
        print("\n1. Convert raw data to app format:")
        print("   python scripts/convert_data.py")
        print("\n2. Train the model:")
        print("   python scripts/train_model.py")
        print("\n3. Start the application:")
        print("   python app.py")
        print("="*70)
    else:
        print("\n" + "="*70)
        print("NO UPDATES AVAILABLE")
        print("="*70)
        print("\nYou already have the latest version!")
        print("Use --force to re-download anyway:")
        print("  python scripts/download_data.py --force")
        print("="*70)
    
    # Show what's downloaded
    list_downloaded_files()
    
    return downloaded


if __name__ == "__main__":
    try:
        # Show help
        if '--help' in sys.argv or '-h' in sys.argv:
            print("""
Usage: python scripts/download_data.py [OPTIONS]

Options:
  --force, -f    Force download even if latest version already downloaded
  --list, -l     List downloaded files without downloading
  --help, -h     Show this help message

Examples:
  python scripts/download_data.py           # Smart download (only if new)
  python scripts/download_data.py --force   # Force re-download
  python scripts/download_data.py --list    # Show downloaded files
""")
            sys.exit(0)
        
        success = main()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
