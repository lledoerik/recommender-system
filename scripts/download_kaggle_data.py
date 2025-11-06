"""
Script to download anime data from Kaggle using kagglehub
Downloads MyAnimeList dataset and copies it to data/ directory

Usage:
    python scripts/download_kaggle_data.py
"""

import kagglehub
import shutil
from pathlib import Path
import sys


def download_and_setup_data():
    """
    Download MyAnimeList dataset from Kaggle and set up in data/ directory
    """
    print("="*70)
    print("DOWNLOADING MYANIMELIST DATASET FROM KAGGLE")
    print("="*70)
    
    try:
        # Download dataset
        print("\nDownloading dataset...")
        path = kagglehub.dataset_download("azathoth42/myanimelist")
        print(f"Dataset downloaded to: {path}")
        
        source_path = Path(path)
        
        # Define destination directory
        script_dir = Path(__file__).resolve().parent
        root_dir = script_dir.parent
        data_dir = root_dir / 'data'
        
        # Create data directory if it doesn't exist
        data_dir.mkdir(exist_ok=True)
        print(f"\nDestination directory: {data_dir}")
        
        # Files to copy
        files_to_copy = ['anime.csv', 'rating.csv']
        
        # Check and copy files
        print("\nCopying files...")
        copied_files = []
        
        for filename in files_to_copy:
            source_file = source_path / filename
            dest_file = data_dir / filename
            
            if source_file.exists():
                shutil.copy2(source_file, dest_file)
                file_size = dest_file.stat().st_size / (1024 * 1024)
                print(f"  ✓ {filename} copied ({file_size:.1f} MB)")
                copied_files.append(filename)
            else:
                print(f"  ✗ {filename} not found in dataset")
        
        if not copied_files:
            print("\n✗ ERROR: No files were copied")
            return False
        
        # Check if we need to run data_cleaner
        cleaned_data_file = data_dir / 'cleaned_data.csv'
        
        if not cleaned_data_file.exists() and (data_dir / 'rating.csv').exists():
            print("\n" + "="*70)
            print("PREPROCESSING DATA")
            print("="*70)
            print("\nRunning data_cleaner to create cleaned_data.csv...")
            
            # Import and run data_cleaner
            sys.path.insert(0, str(script_dir))
            from data_cleaner import preprocess_ratings
            
            rating_csv = data_dir / 'rating.csv'
            cleaned_csv = data_dir / 'cleaned_data.csv'
            
            if preprocess_ratings(input_file=rating_csv, output_file=cleaned_csv):
                print("\n✓ Data preprocessing completed!")
            else:
                print("\n⚠ Warning: Could not preprocess data")
                print("   You may need to run manually:")
                print("   python scripts/data_cleaner.py")
        
        print("\n" + "="*70)
        print("DOWNLOAD COMPLETED SUCCESSFULLY!")
        print("="*70)
        print("\nNext steps:")
        print("  1. Train the model:")
        print("     python scripts/train_model.py")
        print("  2. Start the application:")
        print("     python app.py")
        print("="*70)
        
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
        print("     - Linux/Mac: ~/.kaggle/kaggle.json")
        print("     - Windows: C:\\Users\\YourUsername\\.kaggle\\kaggle.json")
        print("="*70)
        
        return False


if __name__ == "__main__":
    import time
    
    start_time = time.time()
    
    if download_and_setup_data():
        elapsed_time = time.time() - start_time
        print(f"\nTotal time: {elapsed_time:.1f} seconds")
    else:
        print("\nDownload failed. Check errors above.")
        sys.exit(1)
