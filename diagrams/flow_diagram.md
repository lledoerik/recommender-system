# 🔄 FLUX COMPLET D'INTEGRACIÓ KAGGLE → APP

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        KAGGLE MYANIMELIST DATASET                        │
│                     (azathoth42/myanimelist v9)                         │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ python scripts/download_kaggle_data.py
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│              ~/.cache/kagglehub/...myanimelist/versions/9/              │
├─────────────────────────────────────────────────────────────────────────┤
│  ⚠️  ARXIUS ORIGINALS (format Kaggle, NO compatibles amb l'app)        │
│                                                                          │
│  📄 anime_cleaned.csv (6 MB)                                            │
│     Columns: anime_id, title, genre, members, score, ...                │
│                                                                          │
│  📄 animelists_filtered.csv (2.16 GB)                                   │
│     Columns: username, anime_id, my_score, my_status, ...               │
│                                                                          │
│  📄 + 7 more files (UserAnimeList, users_cleaned, etc.)                 │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ python scripts/convert_kaggle_to_app_format.py
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
        ┌─────────────────────┐   ┌─────────────────────────┐
        │  CONVERSIÓ ANIME    │   │   CONVERSIÓ RATINGS     │
        └──────────┬──────────┘   └───────────┬─────────────┘
                   │                           │
        ┌──────────▼──────────┐     ┌──────────▼──────────────┐
        │ • title → name      │     │ • my_score → rating     │
        │ • Selecciona només: │     │ • username → user_id    │
        │   anime_id, name,   │     │   (string → numeric)    │
        │   genre, members    │     │ • Filtra my_score == 0  │
        └──────────┬──────────┘     └───────────┬─────────────┘
                   │                             │
                   │                             │
                   ▼                             ▼
        ┌─────────────────────┐      ┌──────────────────────┐
        │  data/anime.csv     │      │  data/rating.csv     │
        │  (~1 MB)            │      │  (~1.5 GB)           │
        └─────────────────────┘      └──────────┬───────────┘
                                                 │
                                                 │ python scripts/data_cleaner.py
                                                 │ (OPCIONAL pero RECOMANAT)
                                                 │
                                      ┌──────────▼──────────────┐
                                      │ • Elimina rating == -1  │
                                      │ • Users >= 100 ratings  │
                                      │ • Animes >= 50 ratings  │
                                      └──────────┬──────────────┘
                                                 │
                                                 ▼
                                      ┌──────────────────────┐
                                      │ data/cleaned_data.csv│
                                      │ (~200 MB)            │
                                      └──────────┬───────────┘
                                                 │
                                                 │ python scripts/train_model.py
                                                 │
                                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          model/corr_matrix_v1.pkl                        │
│                              (~500 MB)                                   │
├─────────────────────────────────────────────────────────────────────────┤
│  • Matriu de correlació de Pearson                                      │
│  • 12,000+ animes                                                        │
│  • 70,000+ usuaris                                                       │
│  • Min periods: 100                                                      │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ python app.py
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        🎬 ANIME RECOMMENDER APP                          │
│                    https://recomanador.hermes.cat                        │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 RESUM D'ARXIUS

| Arxiu Original (Kaggle) | → | Arxiu Convertit (App) | Mida | Necessari? |
|-------------------------|---|-----------------------|------|------------|
| `anime_cleaned.csv` | → | `data/anime.csv` | 1 MB | ✅ SÍ |
| `animelists_filtered.csv` | → | `data/rating.csv` | 1.5 GB | ⚠️ Temporal |
| - | → | `data/cleaned_data.csv` | 200 MB | ✅ SÍ |
| - | → | `model/corr_matrix_v1.pkl` | 500 MB | ✅ SÍ |

**Pots eliminar:**
- ✅ `data/rating.csv` després de crear `cleaned_data.csv`
- ✅ `~/.cache/kagglehub/...` si necessites espai (es redownloadarà)

---

## 🔧 CONVERSIONS APLICADES

### anime_cleaned.csv → anime.csv

```python
# Columnes originals
anime_id | title | genre | members | score | ...

# Conversió
anime_id | name | genre | members
    ↓       ↓      ↓        ↓
  (same) (rename) (same)  (same)
```

### animelists_filtered.csv → rating.csv

```python
# Columnes originals
username | anime_id | my_score | my_status | ...

# Conversió
user_id | anime_id | rating
   ↓         ↓         ↓
(hash)    (same)   (rename)
```

**Mapping example:**
```
"karthiga"        → user_id: 1
"RedvelvetDaisuki" → user_id: 2
"Damonashu"       → user_id: 3
...
```

---

## ⚡ QUICK REFERENCE

### Instal·lació inicial (només un cop):
```bash
pip install kagglehub
# Configurar ~/.kaggle/kaggle.json
```

### Flux complet (executa en ordre):
```bash
1. python scripts/download_kaggle_data.py        # ~2-5 min
2. python scripts/convert_kaggle_to_app_format.py # ~5-10 min
3. python scripts/train_model.py                  # ~5-10 min
4. python app.py                                  # Instant
```

### Actualitzar dades (cada 1-3 mesos):
```bash
python scripts/download_kaggle_data.py
python scripts/convert_kaggle_to_app_format.py
python scripts/train_model.py
# L'app detectarà el nou model automàticament en 30 segons
```

---

## 🎯 AVANTATGES DEL NOU SISTEMA

| Abans | Ara (amb Kaggle) |
|-------|------------------|
| ❌ Dades estàtiques/manuals | ✅ Dades actualitzades periòdicament |
| ❌ Dataset petit | ✅ Dataset complet de MyAnimeList |
| ❌ Actualització manual | ✅ Script automàtic |
| ❌ Possibles errors en les dades | ✅ Dades netes i verificades |
| ❌ Difícil d'estendre | ✅ Fàcil d'actualitzar |

---

**Total temps primera vegada:** ~20-30 minuts  
**Total temps actualitzacions:** ~10-15 minuts  
**Espai necessari:** ~1 GB (amb cleaned_data, sense rating.csv ni cache)
