# src/ingest.py
# Objetivo: Copiar el archivo CSV desde data/raw/ a data/processed/
# y registrar informacion basica del dataset.

import pandas as pd
import shutil
import os
import logging

# Crear carpeta logs si no existe
os.makedirs('logs', exist_ok=True)

# Configurar logging
logging.basicConfig(
    filename='logs/ingest.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def ingest_data(origen, destino):
    """
    Copia el archivo CSV desde origen a destino y registra informacion.
    
    Parametros:
    origen (str): Ruta del archivo fuente
    destino (str): Ruta donde se copiara el archivo
    
    Retorna:
    bool: True si la ingesta fue exitosa, False en caso contrario
    """
    try:
        # Verificar que el archivo origen existe
        if not os.path.exists(origen):
            raise FileNotFoundError(f"No se encuentra el archivo: {origen}")
        
        # Crear la carpeta de destino si no existe
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        
        # Copiar el archivo
        shutil.copy(origen, destino)
        
        # Leer el archivo copiado para contar registros
        df = pd.read_csv(destino)
        
        # Registrar en el log
        logging.info(f"Ingesta exitosa: {origen} -> {destino}")
        logging.info(f"Registros copiados: {len(df)}")
        logging.info(f"Columnas del dataset: {list(df.columns)}")
        
        print(f"[OK] Ingesta completada. Registros: {len(df)}")
        return True
        
    except Exception as e:
        logging.error(f"Error en ingesta: {str(e)}")
        print(f"[ERROR] {str(e)}")
        return False

if __name__ == "__main__":
    # Rutas de entrada y salida
    archivo_origen = "data/raw/02_bank.csv"
    archivo_destino = "data/processed/02_bank_ingested.csv"
    
    ingest_data(archivo_origen, archivo_destino)