"""
Anime Recommendation System
Main engine with collaborative filtering and Pearson correlation
"""

from src.models.anime import Anime
from src.models.user import User
import pandas as pd
import numpy as np
import pickle
import os
from pathlib import Path
from datetime import datetime


class RecommendationSystem:

    def __init__(self, anime_csv_path='data/anime.csv', rating_csv_path='data/cleaned_data.csv', model_dir='model'):
        """
        Initialize the recommendation system by loading the most recent model
        """
        self.animes_dict = {}
        self.users_dict = {}
        self.ratings_df = None
        self.userRatings_pivot = None
        self.corrMatrix = None
        self.animeStats = None
        self.animePopularity = None
        self.animeAvgRating = None
        self.model_dir = Path(__file__).resolve().parent.parent / model_dir
        self.anime_csv_path = Path(anime_csv_path)
        self.rating_csv_path = Path(rating_csv_path)
        
        # Model info
        self.current_model_version = None
        self.model_load_time = None
        self.data_files_hash = None
        
        # Create model directory if it doesn't exist
        self.model_dir.mkdir(exist_ok=True)
        
        # Try to load trained model
        if not self._load_latest_model():
            print("\n" + "="*70)
            print("WARNING: NO TRAINED MODEL FOUND")
            print("="*70)
            print("\nThe 'model/' directory is empty or doesn't contain valid models.")
            print("\nTo generate the model, run:")
            print("   python scripts/train_model.py")
            print("\nOr from root directory:")
            print("   ./scripts/train_auto.sh")
            print("="*70)
            raise FileNotFoundError(
                "No trained model found. "
                "Run train_model() before using the system."
            )
    
    def get_data_files_hash(self):
        """
        Calculate a hash of data files to detect changes
        Uses modification timestamp of CSV files
        """
        try:
            anime_mtime = self.anime_csv_path.stat().st_mtime
            rating_mtime = self.rating_csv_path.stat().st_mtime
            return f"{anime_mtime}_{rating_mtime}"
        except Exception:
            return None
    
    def has_data_changed(self):
        """
        Check if data files have changed since last training
        
        Returns:
            bool: True if data has changed, False otherwise
        """
        current_hash = self.get_data_files_hash()
        if current_hash is None or self.data_files_hash is None:
            return False
        return current_hash != self.data_files_hash
    
    def _get_latest_version(self):
        """
        Find the latest model version available
        
        Returns:
            int: Most recent version number (0 if none exist)
        """
        if not self.model_dir.exists():
            return 0
        
        versions = []
        for file in self.model_dir.glob('corr_matrix_v*.pkl'):
            try:
                version_str = file.stem.split('_v')[1]
                versions.append(int(version_str))
            except (IndexError, ValueError):
                continue
        
        return max(versions) if versions else 0
    
    def _get_next_version(self):
        """
        Returns the next available version number
        """
        return self._get_latest_version() + 1
    
    def _load_latest_model(self):
        """
        Load the latest trained model version
        
        Returns:
            bool: True if loaded successfully, False otherwise
        """
        latest_version = self._get_latest_version()
        
        if latest_version == 0:
            return False
        
        model_path = self.model_dir / f'corr_matrix_v{latest_version}.pkl'
        
        print(f"\nLoading model v{latest_version} from {model_path}...")
        
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            # Load saved data
            self.animes_dict = model_data['animes_dict']
            self.users_dict = model_data['users_dict']
            self.ratings_df = model_data['ratings_df']
            self.userRatings_pivot = model_data['userRatings_pivot']
            self.corrMatrix = model_data['corrMatrix']
            self.animeStats = model_data['animeStats']
            
            # Load additional statistics if they exist
            self.animePopularity = model_data.get('animePopularity')
            self.animeAvgRating = model_data.get('animeAvgRating')
            
            # If they don't exist, calculate them
            if self.animePopularity is None:
                self._calculate_anime_stats()
            
            # Save model info
            self.current_model_version = latest_version
            self.model_load_time = datetime.now()
            self.data_files_hash = model_data.get('data_files_hash')
            
            print(f"Model v{latest_version} loaded successfully!")
            print(f"   - {len(self.animes_dict)} animes")
            print(f"   - {len(self.users_dict)} users")
            print(f"   - Correlation matrix: {self.corrMatrix.shape}")
            
            return True
            
        except Exception as e:
            print(f"Error loading model: {str(e)}")
            return False
    
    def _calculate_anime_stats(self):
        """
        Calculate additional anime statistics
        """
        if self.ratings_df is not None:
            # Popularity (number of ratings)
            self.animePopularity = self.ratings_df.groupby('name')['rating'].count()
            
            # Average rating
            self.animeAvgRating = self.ratings_df.groupby('name')['rating'].mean()
    
    def reload_model(self):
        """
        Reload the most recent available model
        Useful when a new model has been trained in the background
        
        Returns:
            bool: True if reloaded successfully
        """
        print("\nReloading latest model...")
        return self._load_latest_model()
    
    def train_model(self, save=True):
        """
        Train the model by calculating the correlation matrix
        This process can take several minutes with large datasets
        
        Args:
            save (bool): If True, save model to a versioned PKL file
        """
        print("\n" + "="*70)
        print("STARTING MODEL TRAINING")
        print("="*70)
        
        # Load data from CSVs
        self._load_data_for_training(self.anime_csv_path, self.rating_csv_path)
        
        if save:
            # Save model with next version
            next_version = self._get_next_version()
            model_path = self.model_dir / f'corr_matrix_v{next_version}.pkl'
            
            print(f"\nSaving model v{next_version} to {model_path}...")
            
            # Calculate data files hash
            data_hash = self.get_data_files_hash()
            
            model_data = {
                'animes_dict': self.animes_dict,
                'users_dict': self.users_dict,
                'ratings_df': self.ratings_df,
                'userRatings_pivot': self.userRatings_pivot,
                'corrMatrix': self.corrMatrix,
                'animeStats': self.animeStats,
                'animePopularity': self.animePopularity,
                'animeAvgRating': self.animeAvgRating,
                'version': next_version,
                'anime_csv_path': str(self.anime_csv_path),
                'rating_csv_path': str(self.rating_csv_path),
                'data_files_hash': data_hash,
                'created_at': datetime.now().isoformat()
            }
            
            try:
                with open(model_path, 'wb') as f:
                    pickle.dump(model_data, f, protocol=pickle.HIGHEST_PROTOCOL)
                
                print(f"Model v{next_version} saved successfully!")
                print(f"   File size: {model_path.stat().st_size / (1024*1024):.1f} MB")
                
                # Update current model info
                self.current_model_version = next_version
                self.model_load_time = datetime.now()
                self.data_files_hash = data_hash
                
            except Exception as e:
                print(f"Error saving model: {str(e)}")
                raise
        
        print("="*70)
        print("TRAINING COMPLETED!")
        print("="*70)
    
    def _load_data_for_training(self, anime_csv_path, rating_csv_path):
        """
        Load and process data from CSVs to train the model
        """
        print("\nLoading data from CSVs...")
        
        # Read anime.csv with UTF-8 encoding
        a_cols = ['anime_id', 'name', 'genre', 'members']
        animes_df = pd.read_csv(
            anime_csv_path, 
            sep=',', 
            usecols=a_cols, 
            encoding="utf-8",
            on_bad_lines='skip'
        )
        
        # Read rating CSV with UTF-8 encoding
        ratings_df = pd.read_csv(
            rating_csv_path, 
            sep=',', 
            encoding="utf-8",
            on_bad_lines='skip'
        )
        
        # Merge data
        self.ratings_df = pd.merge(animes_df, ratings_df)
        
        print(f"   Data loaded: {len(self.ratings_df)} ratings")
        
        # Create Anime objects
        print(f"\nProcessing animes...")
        for _, row in animes_df.iterrows():
            anime = Anime(row['anime_id'], row['name'], row['members'])
            anime.genre = row['genre']
            self.animes_dict[row['anime_id']] = anime
        
        print(f"   {len(self.animes_dict)} animes processed")
        
        # Create User objects
        print(f"\nProcessing users...")
        for _, row in self.ratings_df.iterrows():
            user_id = row['user_id']
            anime_id = row['anime_id']
            rating = row['rating']
            
            user = User(user_id, anime_id, rating)
            
            if user_id not in self.users_dict:
                self.users_dict[user_id] = []
            self.users_dict[user_id].append(user)
        
        print(f"   {len(self.users_dict)} users processed")
        
        # Create pivot table
        print(f"\nCreating pivot table...")
        self.userRatings_pivot = self.ratings_df.pivot_table(
            index='user_id', 
            columns='name', 
            values='rating'
        )
        print(f"   Pivot table created: {self.userRatings_pivot.shape}")
        
        # Calculate correlation matrix with minimum 100 common users for reliable correlations
        print(f"\nCalculating correlation matrix...")
        self.corrMatrix = self.userRatings_pivot.corr(method='pearson', min_periods=100)
        print(f"   Correlation matrix calculated: {self.corrMatrix.shape}")
        
        # Calculate statistics
        print(f"\nCalculating statistics...")
        self.animeStats = self.ratings_df.groupby('name').agg({'rating': np.size})
        
        # Calculate popularity and average rating
        self._calculate_anime_stats()
        
        print(f"   Statistics calculated")
        
        print(f"\nAll data processed successfully!")
    
    def get_model_info(self):
        """
        Return information about the current model
        
        Returns:
            dict: Model information (version, load time, statistics)
        """
        return {
            'version': int(self.current_model_version) if self.current_model_version else 0,
            'loaded_at': self.model_load_time.isoformat() if self.model_load_time else None,
            'num_animes': len(self.animes_dict),
            'num_users': len(self.users_dict),
            'num_ratings': len(self.ratings_df) if self.ratings_df is not None else 0,
            'data_changed': self.has_data_changed()
        }
    
    def search_anime_exact(self, query):
        """
        Search for animes that match exactly or partially with the query
        
        Returns:
            list: List of matching animes
        """
        query_lower = query.lower()
        matches = []
        
        for anime_name in self.userRatings_pivot.columns:
            anime_name_lower = anime_name.lower()
            
            # Exact match
            if anime_name_lower == query_lower:
                return [{'name': anime_name, 'match_type': 'exact'}]
            
            # Partial match
            if query_lower in anime_name_lower:
                anime_info = self.ratings_df[self.ratings_df['name'] == anime_name].iloc[0]
                matches.append({
                    'name': anime_name,
                    'genre': str(anime_info.get('genre', 'Unknown')),
                    'match_type': 'partial'
                })
        
        return matches
    
    def get_recommendations_adjusted(self, anime_name, user_rating=5, num_recommendations=6):
        """
        Get recommendations adjusted based on user rating
        
        - If rating >= 4: Return similar animes (high positive correlation)
        - If rating <= 2: Return different animes (low or negative correlation)
        - If rating = 3: Return moderately similar animes
        
        Returns:
            tuple: (recommendations list, exact anime name used)
        """
        
        # Find exact anime name
        exact_anime_name = None
        if anime_name not in self.userRatings_pivot.columns:
            matching = [col for col in self.userRatings_pivot.columns if anime_name.lower() in col.lower()]
            if not matching:
                return None, None
            exact_anime_name = matching[0]
        else:
            exact_anime_name = anime_name
        
        # Get correlations
        anime_ratings = self.userRatings_pivot[exact_anime_name]
        similar_animes = self.userRatings_pivot.corrwith(anime_ratings)
        similar_animes = similar_animes.dropna()
        
        # Create DataFrame with correlations
        df = pd.DataFrame(similar_animes, columns=['similarity'])
        
        # Filter by popularity (minimum 100 ratings for reliable recommendations)
        popular_animes = self.animeStats['rating'] >= 100
        df = self.animeStats[popular_animes].join(df)
        df = df.dropna()
        
        # Add average rating and popularity
        if self.animeAvgRating is not None:
            df = df.join(self.animeAvgRating.rename('avg_rating'))
        if self.animePopularity is not None:
            df = df.join(self.animePopularity.rename('popularity'))
        
        # Remove the current anime from results
        df = df[df.index != exact_anime_name]
        
        # ADJUST BASED ON USER RATING
        if user_rating >= 4:
            # User likes it: return most similar animes with high correlation
            # Filter: only animes with correlation > 0.5 (strong positive correlation)
            df = df[df['similarity'] > 0.5]
            
            # Score: prioritize similarity heavily (90%) with some weight on avg_rating (10%)
            df['score'] = df['similarity'] * 0.9 + (df.get('avg_rating', 7) / 10) * 0.1
            df = df.sort_values('score', ascending=False)
            
        elif user_rating <= 2:
            # User doesn't like it: return different animes
            # Filter: animes with low correlation or negative correlation
            df = df[df['similarity'] < 0.2]
            
            # Score: prioritize good rating and popularity
            df['difference_score'] = (df.get('avg_rating', 7) / 10) * 0.6 + \
                                    (df.get('popularity', 0) / df.get('popularity', 1).max()) * 0.4
            df = df.sort_values('difference_score', ascending=False)
            
        else:  # rating around 3
            # Neutral: moderately similar animes
            df = df[(df['similarity'] > 0.3) & (df['similarity'] < 0.6)]
            df['score'] = df['similarity'] * 0.6 + (df.get('avg_rating', 7) / 10) * 0.4
            df = df.sort_values('score', ascending=False)
        
        # Get top recommendations
        top_recommendations = df.head(num_recommendations)
        
        recommendations = []
        for anime_name_rec in top_recommendations.index:
            anime_info = self.ratings_df[self.ratings_df['name'] == anime_name_rec].iloc[0]
            
            # Get correlation and score
            correlation = top_recommendations.loc[anime_name_rec, 'similarity']
            avg_rating = top_recommendations.loc[anime_name_rec].get('avg_rating', anime_info.get('rating', 0))
            
            recommendations.append({
                "title": str(anime_name_rec),
                "score": float(round(avg_rating, 1)) if pd.notna(avg_rating) else 0.0,
                "genre": str(anime_info.get('genre', 'Unknown')),
                "year": None,
                "correlation": float(round(correlation, 2)) if pd.notna(correlation) else 0.0
            })
        
        return recommendations, exact_anime_name
    
    def get_recommendations(self, anime_name, user_rating=None, num_recommendations=6):
        """
        Legacy version for compatibility - redirects to get_recommendations_adjusted
        """
        recommendations, exact_name = self.get_recommendations_adjusted(anime_name, user_rating or 5, num_recommendations)
        return recommendations
    
    def get_recommendations_for_user(self, user_ratings_dict, num_recommendations=10):
        """
        Get recommendations based on multiple user ratings
        """
        simCandidates = pd.Series(dtype=float)
        
        for anime_name, rating in user_ratings_dict.items():
            if anime_name not in self.corrMatrix.columns:
                matching = [col for col in self.corrMatrix.columns if anime_name.lower() in col.lower()]
                if not matching:
                    print(f"Anime '{anime_name}' not found")
                    continue
                anime_name = matching[0]
            
            sims = self.corrMatrix[anime_name].dropna()
            
            # Adjust based on rating
            if rating >= 4:
                # User likes it: keep positive correlations
                sims = sims.map(lambda x: x * rating)
            elif rating <= 2:
                # User doesn't like it: invert correlations
                sims = sims.map(lambda x: -x * (6 - rating))
            else:
                # Neutral: weight less
                sims = sims.map(lambda x: x * rating * 0.5)
            
            simCandidates = pd.concat([simCandidates, sims])
        
        simCandidates = simCandidates.groupby(simCandidates.index).sum()
        simCandidates = simCandidates.sort_values(ascending=False)
        
        # Remove already rated animes
        for anime_name in user_ratings_dict.keys():
            if anime_name in simCandidates.index:
                simCandidates = simCandidates.drop(anime_name)
        
        top_recommendations = simCandidates.head(num_recommendations)
        
        recommendations = []
        for anime_name_rec, similarity_score in top_recommendations.items():
            anime_info = self.ratings_df[self.ratings_df['name'] == anime_name_rec].iloc[0]
            
            recommendations.append({
                "title": str(anime_name_rec),
                "score": float(round(anime_info.get('rating', 0), 1)) if pd.notna(anime_info.get('rating', 0)) else 0.0,
                "genre": str(anime_info.get('genre', 'Unknown')),
                "year": None,
                "correlation": float(round(similarity_score / sum(user_ratings_dict.values()), 2))
            })
        
        return recommendations
    
    def get_all_animes(self):
        """Return all available animes"""
        animes_list = []
        seen_names = set()
        
        for _, row in self.ratings_df[['name', 'genre']].drop_duplicates('name').iterrows():
            if row['name'] not in seen_names:
                seen_names.add(row['name'])
                animes_list.append({
                    "name": str(row['name']),
                    "genre": str(row['genre'])
                })
        
        return sorted(animes_list, key=lambda x: x['name'])
    
    def search_anime(self, query):
        """Search animes by name"""
        query_lower = query.lower()
        results = []
        
        for anime_name in self.userRatings_pivot.columns:
            if query_lower in anime_name.lower():
                anime_info = self.ratings_df[self.ratings_df['name'] == anime_name].iloc[0]
                results.append({
                    "name": str(anime_name),
                    "genre": str(anime_info.get('genre', 'Unknown'))
                })
        
        return results[:20]
    
    def list_available_models(self):
        """List all available models in model/ directory"""
        if not self.model_dir.exists():
            return []
        
        models = []
        for file in sorted(self.model_dir.glob('corr_matrix_v*.pkl')):
            try:
                version_str = file.stem.split('_v')[1]
                version = int(version_str)
                size_mb = file.stat().st_size / (1024 * 1024)
                models.append({
                    'version': version,
                    'path': str(file),
                    'size_mb': round(size_mb, 2)
                })
            except (IndexError, ValueError):
                continue
        
        return models
