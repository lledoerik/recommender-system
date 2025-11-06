"""
Script per netejar i preprocessar el fitxer rating.csv original
Executa aquest script abans d'usar el sistema si tens el CSV original sense processar

Segueix la lògica del notebook Anime.ipynb per netejar les dades
"""

from pathlib import Path
import pandas as pd
import os

DATA_DIR = Path(__file__).resolve().parent / '../data'
ANIME_CSV = DATA_DIR / 'anime.csv'
RATING_CSV = DATA_DIR / 'rating.csv'
CLEANED_DATA_CSV = DATA_DIR / 'cleaned_data.csv'


def preprocess_ratings(input_file=RATING_CSV, output_file=CLEANED_DATA_CSV):
    """
    Neteja el fitxer de valoracions seguint aquests passos:
    1. Eliminar valoracions -1 (usuaris que van veure però no valorar)
    2. Filtrar usuaris amb almenys 100 valoracions
    3. Filtrar animes amb almenys 50 valoracions
    """

    print("=" * 50)
    print("PREPROCESSAMENT DEL DATASET DE VALORACIONS")
    print("=" * 50)

    # Verificar que existeix el fitxer d'entrada
    if not os.path.exists(input_file):
        print(f"\n✗ ERROR: No s'ha trobat el fitxer '{input_file}'")
        print(f"  Especifica la ruta correcta o col·loca el fitxer a la carpeta actual")
        return False

    print(f"\n📂 Llegint '{input_file}'...")

    try:
        # Carregar el CSV original
        df = pd.read_csv(input_file)
        print(f"✓ Fitxer carregat correctament")
        print(f"  Forma inicial: {df.shape}")
        print(f"  Columnes: {list(df.columns)}")

        # Verificar columnes necessàries
        required_cols = ['user_id', 'anime_id', 'rating']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            print(f"\n✗ ERROR: Falten columnes: {missing_cols}")
            return False

        # Pas 1: Eliminar valoracions -1
        print(f"\n🔧 Pas 1: Eliminant valoracions -1...")
        before = len(df)
        df = df[df['rating'] != -1]
        after = len(df)
        removed = before - after
        print(f"  ✓ Eliminades {removed:,} files amb rating=-1")
        print(f"  Nova forma: {df.shape}")

        # Pas 2: Filtrar usuaris amb almenys 100 valoracions
        print(f"\n🔧 Pas 2: Filtrant usuaris amb almenys 100 valoracions...")
        before_users = df['user_id'].nunique()

        conteo_usuarios = df['user_id'].value_counts()
        usuarios_validos = conteo_usuarios[conteo_usuarios >= 100].index
        df = df[df['user_id'].isin(usuarios_validos)]

        after_users = df['user_id'].nunique()
        removed_users = before_users - after_users
        print(f"  ✓ Eliminats {removed_users:,} usuaris")
        print(f"  Usuaris restants: {after_users:,}")
        print(f"  Nova forma: {df.shape}")

        # Pas 3: Filtrar animes amb almenys 50 valoracions
        print(f"\n🔧 Pas 3: Filtrant animes amb almenys 50 valoracions...")
        before_animes = df['anime_id'].nunique()

        conteo_animes = df['anime_id'].value_counts()
        animes_validos = conteo_animes[conteo_animes >= 50].index
        df = df[df['anime_id'].isin(animes_validos)]

        after_animes = df['anime_id'].nunique()
        removed_animes = before_animes - after_animes
        print(f"  ✓ Eliminats {removed_animes:,} animes")
        print(f"  Animes restants: {after_animes:,}")
        print(f"  Forma final: {df.shape}")

        # Guardar el nou CSV
        print(f"\n💾 Guardant '{output_file}'...")
        df.to_csv(output_file, index=False)
        print(f"  ✓ Fitxer guardat correctament")

        # Resum final
        print("\n" + "=" * 70)
        print("RESUM DEL PREPROCESSAMENT")
        print("=" * 70)

        file_size_before = os.path.getsize(input_file) / (1024 * 1024)  # MB
        file_size_after = os.path.getsize(output_file) / (1024 * 1024)  # MB

        print(f"\n📊 ESTADÍSTIQUES:")
        print(f"  Fitxer original:  {before:,} files, {file_size_before:.1f} MB")
        print(f"  Fitxer processat: {len(df):,} files, {file_size_after:.1f} MB")
        print(f"  Reducció:         {(1 - len(df) / before) * 100:.1f}%")
        print()
        print(f"  Usuaris:  {before_users:,} → {after_users:,}")
        print(f"  Animes:   {before_animes:,} → {after_animes:,}")
        print()
        print(f"✓ Preprocessament completat amb èxit!")
        print(f"  Ara pots utilitzar '{output_file}' al sistema de recomanacions")
        print("=" * 70)

        return True

    except Exception as e:
        print(f"\n✗ ERROR durant el preprocessament:")
        print(f"  {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def analyze_dataset(file_path):
    """
    Analitza un dataset de valoracions i mostra estadístiques
    """
    print("\n" + "=" * 70)
    print(f"ANÀLISI DEL DATASET: {file_path}")
    print("=" * 70)

    if not os.path.exists(file_path):
        print(f"\n✗ ERROR: No s'ha trobat el fitxer '{file_path}'")
        return

    try:
        df = pd.read_csv(file_path)

        print(f"\n📊 INFORMACIÓ BÀSICA:")
        print(f"  Files totals:     {len(df):,}")
        print(f"  Columnes:         {list(df.columns)}")
        print(f"  Mida del fitxer:  {os.path.getsize(file_path) / (1024 * 1024):.1f} MB")

        if 'rating' in df.columns:
            print(f"\n📈 VALORACIONS:")
            print(f"  Valoracions úniques: {df['rating'].nunique()}")
            print(f"  Mitjana:             {df['rating'].mean():.2f}")
            print(f"  Mediana:             {df['rating'].median():.2f}")
            print(f"  Desviació estàndard: {df['rating'].std():.2f}")
            print(f"  Mínim:               {df['rating'].min()}")
            print(f"  Màxim:               {df['rating'].max()}")

            # Comptar -1
            minus_ones = (df['rating'] == -1).sum()
            if minus_ones > 0:
                print(f"  ⚠ Valoracions -1:    {minus_ones:,} ({minus_ones / len(df) * 100:.1f}%)")

        if 'user_id' in df.columns:
            print(f"\n👥 USUARIS:")
            print(f"  Usuaris únics:       {df['user_id'].nunique():,}")
            user_counts = df['user_id'].value_counts()
            print(f"  Valoracions/usuari:")
            print(f"    - Mitjana:         {user_counts.mean():.1f}")
            print(f"    - Mediana:         {user_counts.median():.1f}")
            print(f"    - Mínim:           {user_counts.min()}")
            print(f"    - Màxim:           {user_counts.max()}")

        if 'anime_id' in df.columns:
            print(f"\n🎬 ANIMES:")
            print(f"  Animes únics:        {df['anime_id'].nunique():,}")
            anime_counts = df['anime_id'].value_counts()
            print(f"  Valoracions/anime:")
            print(f"    - Mitjana:         {anime_counts.mean():.1f}")
            print(f"    - Mediana:         {anime_counts.median():.1f}")
            print(f"    - Mínim:           {anime_counts.min()}")
            print(f"    - Màxim:           {anime_counts.max()}")

        print("=" * 70)

    except Exception as e:
        print(f"\n✗ ERROR durant l'anàlisi:")
        print(f"  {str(e)}")


if __name__ == "__main__":
    import sys

    print("\n🎬 PREPROCESSADOR DE DADES D'ANIMES\n")

    # Comprovar arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == '--analyze':
            # Mode anàlisi
            file_to_analyze = sys.argv[2] if len(sys.argv) > 2 else 'rating.csv'
            analyze_dataset(file_to_analyze)
        elif sys.argv[1] == '--help':
            print("Ús:")
            print("  python preprocessing_data.py                    # Preprocessar rating.csv")
            print("  python preprocessing_data.py --analyze [file]   # Analitzar un fitxer")
            print("  python preprocessing_data.py --help             # Mostrar aquesta ajuda")
    else:
        # Mode preprocessament per defecte
        print("Opcions:")
        print("  1. Preprocessar rating.csv → cleaned_data.csv")
        print("  2. Analitzar rating.csv")
        print("  3. Analitzar cleaned_data.csv")
        print("  4. Sortir")

        choice = input("\nSelecciona una opció (1-4): ").strip()

        if choice == '1':
            preprocess_ratings()
        elif choice == '2':
            analyze_dataset(RATING_CSV)
        elif choice == '3':
            analyze_dataset(CLEANED_DATA_CSV)
        elif choice == '4':
            print("Sortint...")
        else:
            print("Opció no vàlida")
