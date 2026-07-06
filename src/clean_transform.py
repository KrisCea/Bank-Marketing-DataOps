# src/clean_transform.py
# Objetivo: Limpiar datos y transformarlos para el modelo.

import pandas as pd
import numpy as np
import os
import logging
from sklearn.preprocessing import StandardScaler

# Crear carpeta logs si no existe
os.makedirs('logs', exist_ok=True)

# Configurar logging
logging.basicConfig(
    filename='logs/clean_transform.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def clean_and_transform(input_path, output_path):
    """
    Limpia y transforma el dataset Bank Marketing.
    
    Operaciones:
    1. Reemplaza valores 'unknown' por la moda (valor mas frecuente)
    2. Convierte variable objetivo 'deposit' a numerica (yes=1, no=0)
    3. Convierte variables binarias (yes/no) a numericas
    4. Aplica One-Hot Encoding a variables categoricas
    5. Escala variables numericas con StandardScaler
    
    Parametros:
    input_path (str): Ruta del archivo a procesar
    output_path (str): Ruta donde se guardara el resultado
    
    Retorna:
    bool: True si el proceso fue exitoso
    """
    try:
        # 1. Cargar datos
        df = pd.read_csv(input_path)
        print(f"[OK] Datos cargados: {df.shape[0]} filas, {df.shape[1]} columnas")
        logging.info(f"Datos cargados: {df.shape[0]} filas, {df.shape[1]} columnas")
        
        # 2. Reemplazar 'unknown' por NaN y luego por la moda
        #    Las columnas que tienen 'unknown' son: job, education, contact, poutcome
        columnas_categoricas = ['job', 'education', 'contact', 'poutcome']
        for col in columnas_categoricas:
            if col in df.columns:
                # Reemplazar 'unknown' por NaN
                df[col] = df[col].replace('unknown', np.nan)
                # Calcular la moda (valor mas frecuente) ignorando NaN
                moda = df[col].mode()[0] if not df[col].mode().empty else 'missing'
                # Llenar NaN con la moda
                df[col] = df[col].fillna(moda)
                logging.info(f"Columna {col}: 'unknown' reemplazados por '{moda}'")
        
        # 3. Convertir variable objetivo 'deposit' a numerica
        #    Esto es CLAVE para el modelo: yes=1, no=0
        if 'deposit' in df.columns:
            df['deposit'] = df['deposit'].map({'yes': 1, 'no': 0})
            print("[OK] 'deposit' convertida: yes=1, no=0")
            logging.info("Variable 'deposit' convertida a numerica (1/0)")
        
        # 4. Convertir otras columnas binarias a numericas
        #    default, housing, loan tambien tienen yes/no
        columnas_binarias = ['default', 'housing', 'loan']
        for col in columnas_binarias:
            if col in df.columns:
                df[col] = df[col].map({'yes': 1, 'no': 0})
                logging.info(f"Columna {col} convertida a numerica")
        
        # 5. One-Hot Encoding para variables categoricas
        #    Esto convierte cada categoria en una columna numerica (0 o 1)
        columnas_encoding = ['job', 'marital', 'education', 'contact', 'month', 'poutcome']
        df = pd.get_dummies(df, columns=columnas_encoding, drop_first=True)
        print(f"[OK] One-Hot Encoding aplicado. Nuevas dimensiones: {df.shape}")
        logging.info(f"One-Hot Encoding aplicado. Nuevas dimensiones: {df.shape}")
        
        # 6. Escalar variables numericas con StandardScaler
        #    Esto centra los datos en media=0 y desviacion=1
        columnas_numericas = ['age', 'balance', 'duration', 'campaign', 'pdays', 'previous']
        columnas_numericas = [col for col in columnas_numericas if col in df.columns]
        
        if columnas_numericas:
            scaler = StandardScaler()
            df[columnas_numericas] = scaler.fit_transform(df[columnas_numericas])
            print(f"[OK] Variables numericas escaladas: {columnas_numericas}")
            logging.info(f"Variables numericas escaladas: {columnas_numericas}")
        
        # 7. Verificar que deposit se convirtio correctamente
        if 'deposit' in df.columns:
            print(f"[OK] Valores de deposit: {df['deposit'].unique()}")
        
        # 8. Guardar dataset procesado
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)
        
        print(f"[OK] Limpieza y transformacion completada. Dimensiones finales: {df.shape}")
        logging.info(f"Dataset guardado en: {output_path}")
        
        return True
        
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        print(f"[ERROR] {str(e)}")
        return False

if __name__ == "__main__":
    # Intentar primero con el archivo ingerido
    archivo_entrada = "data/processed/02_bank_ingested.csv"
    
    # Si no existe, usar el original
    if not os.path.exists(archivo_entrada):
        print("[INFO] No se encuentra archivo ingerido. Usando archivo original.")
        archivo_entrada = "data/raw/02_bank.csv"
    
    archivo_salida = "data/processed/02_bank_clean.csv"
    
    clean_and_transform(archivo_entrada, archivo_salida)