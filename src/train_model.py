# Objetivo: Entrenar un modelo XGBoost sobre las features ya cargadas en SQLite.

import pandas as pd
import numpy as np
import json
import logging
import os
import sys
from datetime import datetime

import xgboost as xgb
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report,
)

from config import (
    TABLE_TRAIN, TABLE_TEST, TARGET_COL,
    MODEL_PATH, MODEL_METADATA_PATH, TRAINING_REPORT,
    RANDOM_SEED, LOGS_DIR, MODELS_DIR,
)
from db import get_engine, DB_ENGINE_KIND

os.makedirs(LOGS_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOGS_DIR, "train_model.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def load_split_from_db(engine):
    train_df = pd.read_sql(f'SELECT * FROM "{TABLE_TRAIN}"', engine)
    test_df = pd.read_sql(f'SELECT * FROM "{TABLE_TEST}"', engine)

    # 'id' solo existiria si se cargo con un esquema que lo agrega
    # explicitamente; se descarta por si acaso, no es una feature.
    train_df = train_df.drop(columns=["id"], errors="ignore")
    test_df = test_df.drop(columns=["id"], errors="ignore")
    return train_df, test_df


def train_and_evaluate():
    try:
        engine = get_engine()
        train_df, test_df = load_split_from_db(engine)
        engine.dispose()
        print(f"[OK] Train cargado: {train_df.shape} | Test cargado: {test_df.shape} (motor: {DB_ENGINE_KIND})")

        y_train = train_df[TARGET_COL]
        X_train = train_df.drop(columns=[TARGET_COL])
        y_test = test_df[TARGET_COL]
        X_test = test_df.drop(columns=[TARGET_COL])

        # Alinear columnas por si acaso (deberian coincidir tras feature_engineering.py)
        X_test = X_test.reindex(columns=X_train.columns, fill_value=0)

        # Manejo de desbalance de clases: XGBoost soporta esto de forma nativa
        # via scale_pos_weight, sin necesidad de sobre/sub-muestrear.
        n_neg = (y_train == 0).sum()
        n_pos = (y_train == 1).sum()
        scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1.0

        model = xgb.XGBClassifier(
            n_estimators=500,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=RANDOM_SEED,
            early_stopping_rounds=30,
            n_jobs=-1,
        )

        model.fit(
            X_train, y_train,
            eval_set=[(X_test, y_test)],
            verbose=False,
        )

        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred),
            "recall": recall_score(y_test, y_pred),
            "f1": f1_score(y_test, y_pred),
            "roc_auc": roc_auc_score(y_test, y_proba),
            "best_iteration": int(model.best_iteration) if hasattr(model, "best_iteration") else None,
        }

        importancias = pd.Series(model.feature_importances_, index=X_train.columns)
        importancias = importancias.sort_values(ascending=False).head(15)

        # Guardar modelo en formato nativo (portable entre versiones/lenguajes)
        model.save_model(MODEL_PATH)

        metadata = {
            "fecha_entrenamiento": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "features": list(X_train.columns),
            "n_train": len(X_train),
            "n_test": len(X_test),
            "scale_pos_weight": scale_pos_weight,
            "metrics": metrics,
        }
        with open(MODEL_METADATA_PATH, "w") as f:
            json.dump(metadata, f, indent=2)

        with open(TRAINING_REPORT, "w", encoding="utf-8") as f:
            f.write("=" * 50 + "\n")
            f.write("REPORTE DE ENTRENAMIENTO - XGBOOST\n")
            f.write("=" * 50 + "\n")
            f.write(f"Fecha: {metadata['fecha_entrenamiento']}\n")
            f.write(f"Train: {metadata['n_train']} filas | Test: {metadata['n_test']} filas\n\n")
            f.write("METRICAS:\n")
            for k, v in metrics.items():
                f.write(f"  {k}: {v}\n")
            f.write("\nTOP 15 FEATURES MAS IMPORTANTES:\n")
            for feat, val in importancias.items():
                f.write(f"  {feat}: {val:.4f}\n")
            f.write("\n" + classification_report(y_test, y_pred))

        print("\n" + "=" * 50)
        print("RESULTADO DEL ENTRENAMIENTO")
        print("=" * 50)
        for k, v in metrics.items():
            print(f"  {k}: {v}")
        print(f"\n[OK] Modelo guardado en: {MODEL_PATH}")
        print(f"[OK] Metadata guardada en: {MODEL_METADATA_PATH}")
        print(f"[OK] Reporte guardado en: {TRAINING_REPORT}")

        logging.info(f"Entrenamiento completado. Metricas: {metrics}")
        return True

    except Exception as e:
        logging.error(f"Error durante entrenamiento: {str(e)}")
        print(f"[ERROR] {str(e)}")
        return False


if __name__ == "__main__":
    ok = train_and_evaluate()
    sys.exit(0 if ok else 1)
