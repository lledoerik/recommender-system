# Anime Recommendation System v2.0

Intelligent recommendation system based on collaborative filtering with Pearson correlation. Now with support for negative ratings, multiple anime selection, and automatic model reloading.

## New Features in v2.0

### Key Improvements

- **Rating-adjusted recommendations:**
   - High (4-5): Find similar animes
   - Medium (3): Moderately related animes
   - Low (1-2): Discover different alternatives

- **Multiple anime selector:** When multiple animes match the same name, you can choose the correct one

- **Automatic model reloading:** Detects and loads new models every 30 seconds without restarting

- **Better UTF-8 support:** Correctly displays Japanese names and special characters

- **Production-ready API:** Works both on localhost and recomanador.hermes.cat

- **Improved correlation algorithm:** Minimum 100 common users for reliable recommendations

- **Better scoring system:** Prioritizes similarity (90%) over average rating (10%) for high ratings

## Features

- **Intelligent recommendations** with adjusted Pearson correlation
- **Automatic training** every day at 2:30 AM
- **Model versioning system** (v1, v2, v3...)
- **Real-time footer** showing model version
- **Fast loading** (2-3 seconds vs 20 minutes)
- **Background training** without blocking
- **Complete REST API** with Flask
- **Modern and responsive web interface**

## Installation

### 1. Requirements
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Train the Model (REQUIRED first time)
```bash
python scripts/train_model.py
```

**Estimated time:** 5-10 minutes depending on dataset size

### 3. Run the Application
```bash
python app.py
```

Access at:
- Local: `http://localhost:5000`
- Production: `https://recomanador.hermes.cat`

## How the System Works

### Rating System

The system intelligently interprets ratings:

| Rating | Behavior | Example |
|--------|----------|---------|
| 4-5 stars | Search similar animes | If you like "Death Note", recommends psychological thrillers |
| 3 stars | Search moderate animes | Neutral recommendations, neither very similar nor very different |
| 1-2 stars | Search alternatives | If you don't like "One Piece", recommends short animes or other genres |

### Automatic Model Reloading

The application checks every **30 seconds** for new models:
- If you train manually with `train_model.py`, it's detected automatically
- No need to restart the API
- Users don't notice any interruption

### Multiple Matches

If you search for "Detective Conan" and multiple results exist:
1. System shows all matching animes
2. You can select the exact anime you want
3. Recommendations are based on your specific selection

## Correlation Algorithm

The system uses Pearson correlation with the following parameters:

- **Minimum common users (min_periods):** 100
  - Ensures reliable correlations
  - Prevents random similarities from small sample sizes

- **Minimum ratings per anime:** 100
  - Only recommends animes with sufficient data
  - Filters out obscure animes with few ratings

- **Scoring for high ratings (4-5):**
  ```python
  score = similarity * 0.9 + (avg_rating / 10) * 0.1
  # Prioritizes similarity heavily (90%) over average rating (10%)
  # Only considers animes with correlation > 0.5 (strong positive correlation)
  ```

- **Scoring for low ratings (1-2):**
  ```python
  score = (avg_rating / 10) * 0.6 + (popularity / max_popularity) * 0.4
  # Prioritizes well-rated and popular animes
  # Only considers animes with correlation < 0.2 (low or negative correlation)
  ```

## API Endpoints

### Main Recommendations
```bash
POST /api/recommendations
{
  "anime": "Death Note",
  "rating": 4.5
}

# Response with multiple matches (HTTP 300):
{
  "status": "multiple_matches",
  "matches": [
    {"name": "Death Note", "genre": "Thriller"},
    {"name": "Death Note: Rewrite", "genre": "Recap"}
  ]
}

# Response with recommendations (HTTP 200):
{
  "anime": "Death Note",  # Exact name used
  "user_rating": 4.5,
  "recommendations": [...]
}
```

### Model Information
```bash
GET /api/model-info

{
  "version": 3,
  "loaded_at": "2025-10-31T12:30:45",
  "num_animes": 12294,
  "num_users": 73516,
  "training_in_progress": false
}
```

## Troubleshooting

### Recommendations don't seem good

**Possible causes:**
1. **Dataset too small**: The file `rating_balanceado.csv` has too many filters
2. **Few users in common**: Lower the `min_periods` in correlation (currently at 100)

**Solution:**
```python
# In recommendation_system.py, change:
self.corrMatrix = self.userRatings_pivot.corr(method='pearson', min_periods=50)  # Lower
```

### Japanese characters not displaying correctly

**Implemented solution:**
- All CSVs are read with `encoding='utf-8'`
- HTML has `<meta charset="UTF-8">`
- CSS includes Japanese fonts

If you still have problems, convert CSVs:
```bash
iconv -f ISO-8859-1 -t UTF-8 data/anime.csv > data/anime_utf8.csv
mv data/anime_utf8.csv data/anime.csv
```

### API connection error

**For production:**
- App MUST always run with `host='0.0.0.0'`
- Domain `recomanador.hermes.cat` must point to server
- JavaScript uses `window.location.origin` to find API

### Automatic training not working

Verify that:
1. Scheduler is active (check logs)
2. CSV files have actually changed
3. Training is not already in progress

## Model Improvements

### To improve recommendation quality:

1. **Increase dataset:**
   - Use original `rating.csv` with fewer filters
   - Or lower thresholds in `data_cleaner.py`

2. **Adjust parameters:**
   ```python
   # Minimum users to calculate correlation
   min_periods=50  # Lower for more coverage
   
   # Minimum ratings per anime
   popular_animes = self.animeStats['rating'] >= 50  # Lower for more variety
   ```

3. **Add more factors:**
   - Genres
   - Release year
   - Global popularity

## Usage Tips

### For users:
- **Rate high (4-5)** animes you like to find similar ones
- **Rate low (1-2)** animes you don't like to discover alternatives
- **Rate neutral (3)** to explore moderately

### For developers:
- New models are automatically detected every 30 seconds
- Manual training doesn't block the API
- You can have multiple model versions

## Technical Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Flask API  │────▶│Recommendation│
│  JavaScript  │     │   (app.py)   │     │    System    │
└──────────────┘     └──────────────┘     └──────────────┘
                            │                      │
                     ┌──────▼──────┐      ┌───────▼──────┐
                     │  Scheduler  │      │ Pickle Models│
                     │ (APScheduler)│      │  (v1,v2,v3) │
                     └──────────────┘      └──────────────┘
```

## Why v1.0 Recommendations Were Poor

The original system had several issues:

1. **min_periods=50 too low:**
   - Correlations calculated with only 50 common users weren't reliable
   - Led to random similarities from small sample sizes
   - Many false positive correlations

2. **Poor scoring formula:**
   - Mixed similarity (70%) with avg_rating (30%)
   - Didn't filter by minimum correlation strength
   - Allowed weakly correlated animes to be recommended

3. **Low popularity filter:**
   - Only required 50 ratings per anime
   - Recommended obscure animes without sufficient data

4. **Wrong approach for negative ratings:**
   - Searched for animes with similarity < 0.3
   - This included animes with unreliable or no correlation
   - Didn't prioritize good alternatives

### v2.0 Improvements:

1. **min_periods=100:**
   - More reliable correlations
   - Better signal-to-noise ratio

2. **Better scoring (high ratings):**
   - Prioritizes similarity (90%) over rating (10%)
   - Only considers correlation > 0.5 (strong positive)
   - Filters out weakly related animes

3. **Higher popularity threshold:**
   - Requires 100 ratings minimum
   - Ensures recommended animes have sufficient data

4. **Better negative rating handling:**
   - Searches for animes with correlation < 0.2
   - Prioritizes well-rated (60%) and popular (40%) alternatives
   - Provides good animes that are genuinely different

## Future Roadmap

- [ ] Implement recommendation caching
- [ ] Add genre filtering
- [ ] Login system and user profiles
- [ ] Recommendation history
- [ ] Export/import models
- [ ] Integration with external APIs (MyAnimeList, etc.)

---

**Developed with care for the anime community**

*Version 2.0 - November 2025*
