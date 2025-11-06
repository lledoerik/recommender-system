#!/usr/bin/env python3
"""
Script per verificar i corregir l'encoding dels fitxers CSV
Converteix automàticament a UTF-8 si cal

Ús:
    python scripts/encoding.py
"""

import chardet
from pathlib import Path
import shutil

def detect_encoding(file_path):
    """Detecta l'encoding d'un fitxer"""
    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read(100000))  # Llegir primers 100KB
    return result['encoding'], result['confidence']

def convert_to_utf8(input_file, output_file, source_encoding):
    """Converteix un fitxer a UTF-8"""
    try:
        with open(input_file, 'r', encoding=source_encoding) as source:
            content = source.read()
        
        with open(output_file, 'w', encoding='utf-8') as target:
            target.write(content)
        
        return True
    except Exception as e:
        print(f"❌ Error convertint: {e}")
        return False

def fix_csv_encoding():
    """Verifica i corregeix l'encoding de tots els CSV"""
    
    data_dir = Path(__file__).resolve().parent.parent / 'data'
    
    csv_files = [
        'anime.csv',
        'rating.csv',
        'cleaned_data.csv'
    ]
    
    print("="*70)
    print("🔍 VERIFICADOR D'ENCODING DE FITXERS CSV")
    print("="*70)
    
    for csv_file in csv_files:
        file_path = data_dir / csv_file
        
        if not file_path.exists():
            print(f"\n⏭️  {csv_file}: No existeix")
            continue
        
        print(f"\n📄 Processant: {csv_file}")
        print("-" * 40)
        
        # Detectar encoding actual
        encoding, confidence = detect_encoding(file_path)
        file_size = file_path.stat().st_size / (1024 * 1024)
        
        print(f"   Mida: {file_size:.1f} MB")
        print(f"   Encoding detectat: {encoding} (confiança: {confidence*100:.1f}%)")
        
        # Si ja és UTF-8, no cal fer res
        if encoding and encoding.upper() in ['UTF-8', 'ASCII']:
            print(f"   ✅ Ja està en {encoding} - No cal conversió")
            continue
        
        # Preguntar si vol convertir
        print(f"   ⚠️  No és UTF-8!")
        
        response = input(f"   Vols convertir {csv_file} a UTF-8? (s/n): ").lower()
        
        if response == 's':
            # Crear backup
            backup_path = file_path.with_suffix('.csv.backup')
            print(f"   📦 Creant backup: {backup_path.name}")
            shutil.copy2(file_path, backup_path)
            
            # Convertir a UTF-8
            temp_path = file_path.with_suffix('.csv.utf8')
            
            if convert_to_utf8(file_path, temp_path, encoding):
                # Reemplaçar original
                shutil.move(temp_path, file_path)
                print(f"   ✅ Convertit correctament a UTF-8!")
                
                # Verificar
                new_encoding, _ = detect_encoding(file_path)
                print(f"   📝 Nou encoding: {new_encoding}")
            else:
                print(f"   ❌ Error en la conversió")
                if temp_path.exists():
                    temp_path.unlink()
        else:
            print(f"   ⏭️  Saltat")
    
    print("\n" + "="*70)
    print("✅ VERIFICACIÓ COMPLETADA")
    print("="*70)
    
    # Consells finals
    print("\n💡 CONSELLS:")
    print("   - Si encara tens problemes amb caràcters, prova:")
    print("     iconv -f ISO-8859-1 -t UTF-8 data/anime.csv > data/anime_utf8.csv")
    print("   - Recorda re-entrenar el model després de convertir els CSV")
    print("     python scripts/train_model.py")

if __name__ == "__main__":
    try:
        fix_csv_encoding()
    except KeyboardInterrupt:
        print("\n\n⚠️  Operació cancel·lada per l'usuari")
    except Exception as e:
        print(f"\n❌ Error inesperat: {e}")
        import traceback
        traceback.print_exc()
