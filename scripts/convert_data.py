"""
Data Converter for MyAnimeList Dataset

Converts raw Kaggle data to app-compatible format:
- data/raw/*.csv → data/anime.csv + data/rating.csv (clean)

Features:
- Reads from data/raw/ (project directory)
- Applies all cleaning and transformations
- Outputs anime.csv and rating.csv ready to use
- No intermediate files needed

Usage:
    python scripts/convert_data.py
"""

import pandas as pd
from pathlib import Path
import sys
import time


# Path configuration (everything relative to project)
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"

# Source files (in raw/)
ANIME_SOURCE = RAW_DATA_DIR / "anime_cleaned.csv"
RATING_SOURCE = RAW_DATA_DIR / "animelists_filtered.csv"

# Destination files (in data/)
ANIME_DEST = DATA_DIR / "anime.csv"
RATING_DEST = DATA_DIR / "rating.csv"


def check_raw_data():
    """
    Check if raw data exists and is valid
    
    Returns:
        bool: True if raw data exists and is valid
    """
    if not RAW_DATA_DIR.exists():
        print(f"\n✗ ERROR: Raw data directory not found: {RAW_DATA_DIR}")
        print(f"\n💡 TIP: Run 'python scripts/download_data.py' first")
        return False
    
    if not ANIME_SOURCE.exists():
        print(f"\n✗ ERROR: Raw anime file not found: {ANIME_SOURCE.name}")
        print(f"\n💡 TIP: Run 'python scripts/download_data.py' first")
        return False
    
    if not RATING_SOURCE.exists():
        print(f"\n✗ ERROR: Raw rating file not found: {RATING_SOURCE.name}")
        print(f"\n💡 TIP: Run 'python scripts/download_data.py' first")
        return False
    
    return True


def convert_anime_file():
    """
    Convert anime_cleaned.csv to anime.csv format
    
    Changes:
    - Rename 'title' → 'name'
    - Keep only: anime_id, name, genre, members
    """
    print("\n" + "="*70)
    print("STEP 1: CONVERTING ANIME FILE")
    print("="*70)
    
    print(f"\n📂 Reading: {ANIME_SOURCE.name}")
    print(f"   Size: {ANIME_SOURCE.stat().st_size / (1024*1024):.1f} MB")
    
    try:
        # Read source file
        df = pd.read_csv(ANIME_SOURCE, encoding='utf-8')
        print(f"✓ File loaded: {len(df):,} rows")
        
        # Select and rename columns
        columns_map = {
            'anime_id': 'anime_id',
            'title': 'name',  # RENAME
            'genre': 'genre',
            'members': 'members'
        }
        
        # Check columns
        missing = [col for col in columns_map.keys() if col not in df.columns]
        if missing:
            print(f"✗ ERROR: Missing columns: {missing}")
            return False
        
        # Transform
        df_converted = df[list(columns_map.keys())].rename(columns=columns_map)
        
        print(f"\n🔧 Conversion:")
        print(f"   Columns: {list(df_converted.columns)}")
        print(f"   Animes: {len(df_converted):,}")
        
        # Save
        df_converted.to_csv(ANIME_DEST, index=False, encoding='utf-8')
        
        dest_size = ANIME_DEST.stat().st_size / (1024*1024)
        print(f"\n✓ Saved: {ANIME_DEST.name}")
        print(f"   Size: {dest_size:.1f} MB")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def convert_rating_file_clean():
    """
    Convert animelists_filtered.csv to rating.csv format
    Includes all cleaning - output is ready to use!
    
    Steps:
    1. Filter out my_score == 0 (not rated)
    2. Convert username → numeric user_id
    3. Filter users with < 100 ratings
    4. Filter animes with < 50 ratings
    5. Save as rating.csv (CLEAN)
    """
    print("\n" + "="*70)
    print("STEP 2: CONVERTING & CLEANING RATING FILE")
    print("="*70)
    
    print(f"\n📂 Reading: {RATING_SOURCE.name}")
    print(f"   Size: {RATING_SOURCE.stat().st_size / (1024*1024):.1f} MB")
    print(f"   ⚠️  This may take a few minutes...")
    
    try:
        # Read source file
        df = pd.read_csv(RATING_SOURCE, encoding='utf-8')
        initial_rows = len(df)
        print(f"✓ File loaded: {initial_rows:,} rows")
        
        # STEP 1: Filter my_score == 0
        print(f"\n🔧 Cleaning step 1/4: Filter my_score == 0...")
        df = df[df['my_score'] > 0]
        after_step1 = len(df)
        print(f"   Removed {initial_rows - after_step1:,} unrated animes")
        print(f"   Remaining: {after_step1:,} rows")
        
        # STEP 2: Convert username → user_id
        print(f"\n🔧 Cleaning step 2/4: Convert username → user_id...")
        unique_users_before = df['username'].nunique()
        print(f"   Unique users: {unique_users_before:,}")
        
        # Create mapping
        username_to_id = {username: idx for idx, username in enumerate(df['username'].unique(), start=1)}
        df['user_id'] = df['username'].map(username_to_id)
        
        print(f"   ✓ Mapped to numeric IDs")
        
        # Rename and select columns
        df.rename(columns={'my_score': 'rating'}, inplace=True)
        df = df[['user_id', 'anime_id', 'rating']].copy()
        
        # STEP 3: Filter users with < 100 ratings
        print(f"\n🔧 Cleaning step 3/4: Filter users with < 100 ratings...")
        users_before = df['user_id'].nunique()
        
        user_counts = df['user_id'].value_counts()
        valid_users = user_counts[user_counts >= 100].index
        df = df[df['user_id'].isin(valid_users)]
        
        users_after = df['user_id'].nunique()
        print(f"   Removed {users_before - users_after:,} users")
        print(f"   Remaining users: {users_after:,}")
        print(f"   Remaining rows: {len(df):,}")
        
        # STEP 4: Filter animes with < 50 ratings
        print(f"\n🔧 Cleaning step 4/4: Filter animes with < 50 ratings...")
        animes_before = df['anime_id'].nunique()
        
        anime_counts = df['anime_id'].value_counts()
        valid_animes = anime_counts[anime_counts >= 50].index
        df = df[df['anime_id'].isin(valid_animes)]
        
        animes_after = df['anime_id'].nunique()
        print(f"   Removed {animes_before - animes_after:,} animes")
        print(f"   Remaining animes: {animes_after:,}")
        print(f"   Remaining rows: {len(df):,}")
        
        # Statistics
        print(f"\n📊 Final statistics:")
        print(f"   Total ratings: {len(df):,}")
        print(f"   Unique users: {df['user_id'].nunique():,}")
        print(f"   Unique animes: {df['anime_id'].nunique():,}")
        print(f"   Avg ratings/user: {len(df) / df['user_id'].nunique():.1f}")
        print(f"   Avg ratings/anime: {len(df) / df['anime_id'].nunique():.1f}")
        print(f"   Rating range: {df['rating'].min():.0f} - {df['rating'].max():.0f}")
        print(f"   Avg rating: {df['rating'].mean():.2f}")
        
        # Save
        print(f"\n💾 Saving: {RATING_DEST.name}...")
        print(f"   ⚠️  This may take a few minutes...")
        
        df.to_csv(RATING_DEST, index=False, encoding='utf-8')
        
        dest_size = RATING_DEST.stat().st_size / (1024*1024)
        print(f"\n✓ Saved: {RATING_DEST.name}")
        print(f"   Size: {dest_size:.1f} MB")
        
        source_size = RATING_SOURCE.stat().st_size / (1024*1024)
        print(f"   Reduction: {(1 - dest_size / source_size) * 100:.1f}%")
        
        return True
        
    except Exception as e:
        print(f"\n✗ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    Main function
    """
    print("\n" + "="*70)
    print("DATA CONVERTER - RAW TO APP FORMAT")
    print("="*70)
    
    print(f"\nSource: {RAW_DATA_DIR}")
    print(f"Destination: {DATA_DIR}")
    
    # Check raw data
    if not check_raw_data():
        return False
    
    start_time = time.time()
    
    # Step 1: Convert anime
    if not convert_anime_file():
        print("\n❌ Anime conversion failed")
        return False
    
    # Step 2: Convert & clean ratings
    if not convert_rating_file_clean():
        print("\n❌ Rating conversion failed")
        return False
    
    # Summary
    elapsed = time.time() - start_time
    
    print("\n" + "="*70)
    print("✅ CONVERSION COMPLETED!")
    print("="*70)
    
    print(f"\n📊 Output files:")
    
    if ANIME_DEST.exists():
        size_mb = ANIME_DEST.stat().st_size / (1024*1024)
        print(f"   ✓ {ANIME_DEST.name:20s} {size_mb:8.1f} MB")
    
    if RATING_DEST.exists():
        size_mb = RATING_DEST.stat().st_size / (1024*1024)
        print(f"   ✓ {RATING_DEST.name:20s} {size_mb:8.1f} MB")
    
    print(f"\n⏱️  Total time: {elapsed/60:.1f} minutes")
    
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)
    print("\n1. Train the model:")
    print("   python scripts/train_model.py")
    print("\n2. Start the application:")
    print("   python app.py")
    print("\n" + "="*70)
    print("NOTE: anime.csv and rating.csv are clean and ready!")
    print("="*70)
    
    return True


if __name__ == "__main__":
    try:
        # Show help
        if '--help' in sys.argv or '-h' in sys.argv:
            print("""
Usage: python scripts/convert_data.py

Converts raw Kaggle data to app-compatible format:
  data/raw/anime_cleaned.csv       → data/anime.csv
  data/raw/animelists_filtered.csv → data/rating.csv (clean)

The conversion includes:
  - Column renaming (title → name, my_score → rating)
  - Username to numeric user_id conversion
  - Filtering (users >= 100 ratings, animes >= 50 ratings)
  - Removal of unrated animes (score == 0)

Output files are clean and ready to use for training!
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
