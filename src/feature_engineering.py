import os
import sys
import logging
from datetime import datetime

import pandas as pd
from sklearn.model_selection import train_test_split

from config import TEST_FILE, TRAIN_FILE, RANDOM_SEED, TEST_SIZE, LOGS_DIR

os.makedirs(LOGS_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOGS_DIR, "feature_engineering.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)


def split_train_test(input_path, train_path, test_path, test_size, random_seed):
    try:
        # Verificar que el archivo de entrada exista antes de procesar.
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"No se encuentra el archivo de entrada: {input_path}")

        df = pd.read_csv(input_path)
        if df.empty:
            raise ValueError("El archivo de entrada esta vacio")

        # La columna de objetivo debe existir para hacer el split estratificado.
        if "deposit" not in df.columns:
            raise KeyError("No se encontro la columna 'deposit' en el dataset")

        print(f"[OK] Cargando datos para feature engineering: {df.shape[0]} filas, {df.shape[1]} columnas")
        logging.info(f"Datos cargados: {df.shape}")

        # Usar estratificacion si hay ambas clases en la columna deposit.
        # Esto mantiene la misma distribucion de la variable objetivo en train/test.
        stratify = df["deposit"] if df["deposit"].nunique() > 1 else None
        train_df, test_df = train_test_split(
            df,
            test_size=test_size,
            random_state=random_seed,
            stratify=stratify,
        )

        # Guardar los conjuntos resultantes en archivos separados.
        os.makedirs(os.path.dirname(train_path), exist_ok=True)
        train_df.to_csv(train_path, index=False)
        test_df.to_csv(test_path, index=False)

        logging.info(
            f"Split train/test completado: {len(train_df)} train, {len(test_df)} test"
        )
        print(f"[OK] Feature engineering completado. Train: {len(train_df)}, Test: {len(test_df)}")
        print(f"[INFO] Archivos guardados: {train_path}, {test_path}")

        return True

    except Exception as e:
        logging.error(f"Error en feature engineering: {str(e)}")
        print(f"[ERROR] {str(e)}")
        return False


if __name__ == "__main__":
    # Ruta del archivo limpio generado por clean_transform.py.
    input_file = os.path.join("data", "processed", "02_bank_clean.csv")
    success = split_train_test(input_file, TRAIN_FILE, TEST_FILE, TEST_SIZE, RANDOM_SEED)
    sys.exit(0 if success else 1)
