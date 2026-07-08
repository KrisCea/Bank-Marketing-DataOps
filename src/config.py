"""
Configuración centralizada del pipeline Bank Marketing DataOps
"""
import os
from pathlib import Path

# Directorios base
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
MODELS_DIR = os.path.join(BASE_DIR, "models")

# Archivos de datos
RAW_FILE = os.path.join(DATA_DIR, "raw", "02_bank.csv")
TRAIN_FILE = os.path.join(DATA_DIR, "processed", "02_bank_train.csv")
TEST_FILE = os.path.join(DATA_DIR, "processed", "02_bank_test.csv")

# Base de datos
DB_PATH = os.path.join(BASE_DIR, "bank_marketing.db")

# Tablas
TABLE_TRAIN = "train"
TABLE_TEST = "test"

# Columna target
# El dataset de Bank Marketing usa 'deposit' como variable objetivo.
TARGET_COL = "deposit"

# Modelos y reportes
MODEL_PATH = os.path.join(MODELS_DIR, "xgboost_model.json")
MODEL_METADATA_PATH = os.path.join(MODELS_DIR, "model_metadata.json")
TRAINING_REPORT = os.path.join(DATA_DIR, "reports", "training_report.json")
LOAD_REPORT = os.path.join(DATA_DIR, "reports", "load_report.csv")

# Parámetros de entrenamiento
RANDOM_SEED = 42
TEST_SIZE = 0.2

# Crear directorios si no existen
for directory in [DATA_DIR, LOGS_DIR, MODELS_DIR, 
                  os.path.join(DATA_DIR, "raw"), 
                  os.path.join(DATA_DIR, "processed"),
                  os.path.join(DATA_DIR, "reports"),
                  os.path.join(DATA_DIR, "validated")]:
    os.makedirs(directory, exist_ok=True)
