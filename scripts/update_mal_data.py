"""
Script per descarregar dades d'animes de MyAnimeList via Jikan API
Actualitza el dataset amb animes moderns (Jujutsu Kaisen, Chainsaw Man, etc.)

Jikan API: https://jikan.moe/
Documentació: https://docs.api.jikan.moe/

Ús:
    python scripts/update_mal_data.py
"""

import requests
import pandas as pd
import time
from pathlib import Path
from datetime import datetime


class MALDataUpdater:
    def __init__(self):
        self.base_url = "https://api.jikan.moe/v4"
        self.data_dir = Path(__file__).resolve().parent.parent / 'data'
        self.anime_csv = self.data_dir / 'anime.csv'
        
        # Rate limiting: Jikan has 3 requests/second, 60 requests/minute
        self.request_delay = 0.4  # seconds between requests
        
    def get_top_anime(self, page=1, limit=25):
        """
        Get top anime from MAL
        
        Args:
            page: Page number (1-based)
            limit: Results per page (max 25)
        
        Returns:
            List of anime data
        """
        url = f"{self.base_url}/top/anime"
        params = {
            'page': page,
            'limit': limit
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get('data', [])
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            return []
    
    def get_seasonal_anime(self, year=None, season='winter'):
        """
        Get seasonal anime (current or specific season)
        
        Args:
            year: Year (e.g., 2024), None for current
            season: 'winter', 'spring', 'summer', 'fall'
        
        Returns:
            List of anime data
        """
        if year is None:
            url = f"{self.base_url}/seasons/now"
        else:
            url = f"{self.base_url}/seasons/{year}/{season}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            return data.get('data', [])
        except Exception as e:
            print(f"Error fetching seasonal anime: {e}")
            return []
    
    def search_anime(self, query):
        """
        Search anime by name
        
        Args:
            query: Anime name to search
        
        Returns:
            List of anime data
        """
        url = f"{self.base_url}/anime"
        params = {
            'q': query,
            'limit': 25
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            return data.get('data', [])
        except Exception as e:
            print(f"Error searching '{query}': {e}")
            return []
    
    def parse_anime_data(self, anime_data):
        """
        Parse Jikan API anime data to our CSV format
        
        Returns:
            Dict with keys: anime_id, name, genre, members
        """
        # Extract genres
        genres = [g['name'] for g in anime_data.get('genres', [])]
        genre_str = ', '.join(genres) if genres else 'Unknown'
        
        return {
            'anime_id': anime_data.get('mal_id'),
            'name': anime_data.get('title'),
            'genre': genre_str,
            'members': anime_data.get('members', 0),
            'score': anime_data.get('score', 0),
            'episodes': anime_data.get('episodes', 0),
            'type': anime_data.get('type', 'Unknown'),
            'status': anime_data.get('status', 'Unknown')
        }
    
    def fetch_popular_animes(self, num_pages=10):
        """
        Fetch top popular animes from MAL
        
        Args:
            num_pages: Number of pages to fetch (25 animes per page)
        
        Returns:
            List of parsed anime data
        """
        print(f"\n{'='*70}")
        print("DESCARREGANT ANIMES POPULARS DE MYANIMELIST")
        print(f"{'='*70}\n")
        
        all_animes = []
        
        for page in range(1, num_pages + 1):
            print(f"Descarregant pàgina {page}/{num_pages}...")
            
            animes = self.get_top_anime(page=page)
            
            for anime in animes:
                parsed = self.parse_anime_data(anime)
                all_animes.append(parsed)
                print(f"  - {parsed['name']} ({parsed['score']}★, {parsed['members']:,} members)")
            
            # Rate limiting
            time.sleep(self.request_delay)
        
        print(f"\n✓ Descarregats {len(all_animes)} animes")
        return all_animes
    
    def fetch_specific_animes(self, anime_names):
        """
        Fetch specific animes by name
        
        Args:
            anime_names: List of anime names to search
        
        Returns:
            List of parsed anime data
        """
        print(f"\n{'='*70}")
        print("CERCANT ANIMES ESPECÍFICS")
        print(f"{'='*70}\n")
        
        all_animes = []
        
        for name in anime_names:
            print(f"Cercant '{name}'...")
            
            results = self.search_anime(name)
            
            if results:
                # Take first result (most relevant)
                anime = results[0]
                parsed = self.parse_anime_data(anime)
                all_animes.append(parsed)
                print(f"  ✓ Trobat: {parsed['name']} ({parsed['score']}★)")
            else:
                print(f"  ✗ No trobat")
            
            # Rate limiting
            time.sleep(self.request_delay)
        
        print(f"\n✓ Trobats {len(all_animes)}/{len(anime_names)} animes")
        return all_animes
    
    def merge_with_existing(self, new_animes):
        """
        Merge new anime data with existing CSV
        
        Args:
            new_animes: List of new anime data dicts
        
        Returns:
            Updated DataFrame
        """
        print(f"\n{'='*70}")
        print("FUSIONANT AMB DADES EXISTENTS")
        print(f"{'='*70}\n")
        
        # Load existing data
        if self.anime_csv.exists():
            existing_df = pd.read_csv(self.anime_csv, encoding='utf-8')
            print(f"Dades existents: {len(existing_df)} animes")
        else:
            existing_df = pd.DataFrame()
            print("No hi ha dades existents. Creant nou dataset.")
        
        # Create DataFrame from new animes
        new_df = pd.DataFrame(new_animes)
        print(f"Noves dades: {len(new_df)} animes")
        
        # Merge
        if not existing_df.empty:
            # Remove duplicates by anime_id
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=['anime_id'], keep='last')
            
            print(f"\nResultat:")
            print(f"  - Total animes: {len(combined_df)}")
            print(f"  - Nous afegits: {len(combined_df) - len(existing_df)}")
            print(f"  - Actualitzats: {len(new_df) - (len(combined_df) - len(existing_df))}")
        else:
            combined_df = new_df
            print(f"\nNou dataset creat amb {len(combined_df)} animes")
        
        return combined_df
    
    def save_data(self, df, backup=True):
        """
        Save updated data to CSV
        
        Args:
            df: DataFrame to save
            backup: If True, create backup of old file
        """
        print(f"\n{'='*70}")
        print("GUARDANT DADES")
        print(f"{'='*70}\n")
        
        # Create backup
        if backup and self.anime_csv.exists():
            backup_path = self.anime_csv.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
            self.anime_csv.rename(backup_path)
            print(f"✓ Backup creat: {backup_path.name}")
        
        # Save
        df.to_csv(self.anime_csv, index=False, encoding='utf-8')
        size_mb = self.anime_csv.stat().st_size / (1024 * 1024)
        print(f"✓ Guardat: {self.anime_csv} ({size_mb:.1f} MB)")
        
        print(f"\n{'='*70}")
        print("ACTUALITZACIÓ COMPLETADA!")
        print(f"{'='*70}")
        print(f"\n📝 Següent pas: Reentrena el model")
        print(f"   python scripts/train_model.py")


def main():
    updater = MALDataUpdater()
    
    print("="*70)
    print("ACTUALITZADOR DE DADES DE MYANIMELIST")
    print("="*70)
    print("\nOpcions:")
    print("  1. Descarregar top animes populars")
    print("  2. Cercar animes específics")
    print("  3. Descarregar animes de temporada actual")
    print("  4. Sortir")
    
    choice = input("\nSelecciona una opció (1-4): ").strip()
    
    if choice == '1':
        pages = input("Quantes pàgines vols descarregar? (1 pàgina = 25 animes): ").strip()
        try:
            pages = int(pages)
            animes = updater.fetch_popular_animes(num_pages=pages)
            df = updater.merge_with_existing(animes)
            updater.save_data(df)
        except ValueError:
            print("Error: Has d'introduir un número")
    
    elif choice == '2':
        # Lista de animes moderns que falten
        modern_animes = [
            'Jujutsu Kaisen',
            'Chainsaw Man',
            'Kimetsu no Yaiba',
            'Demon Slayer',
            'Spy x Family',
            'Bocchi the Rock',
            'Frieren: Beyond Journey\'s End',
            'Oshi no Ko',
            'Vinland Saga',
            'Blue Lock',
            'Cyberpunk: Edgerunners',
            'Lycoris Recoil',
            'Mob Psycho 100',
            'One Punch Man',
            'Tokyo Revengers',
            'Horimiya',
            'Shingeki no Kyojin: The Final Season',
            'Kaguya-sama: Love is War',
            'Re:Zero kara Hajimeru Isekai Seikatsu',
            'Mushoku Tensei',
            'Sono Bisque Doll wa Koi wo Suru'
        ]
        
        print("\nCercant animes moderns...")
        animes = updater.fetch_specific_animes(modern_animes)
        df = updater.merge_with_existing(animes)
        updater.save_data(df)
    
    elif choice == '3':
        print("\nDescarregant animes de temporada actual...")
        animes_data = updater.get_seasonal_anime()
        animes = [updater.parse_anime_data(a) for a in animes_data]
        df = updater.merge_with_existing(animes)
        updater.save_data(df)
    
    elif choice == '4':
        print("Sortint...")
    
    else:
        print("Opció no vàlida")


if __name__ == "__main__":
    main()
