# Objetivo: Cargar los datos de train/test a una base de datos relacional.
#
# Antes hablaba directo con sqlite3 (atado a SQLite). Ahora usa el motor
# que devuelva db.get_engine(), que segun DB_ENGINE puede ser SQLite local
# o Cloud SQL PostgreSQL: el mismo codigo sirve para migrar de uno a otro
# sin tocar una linea de este archivo, solo variables de entorno.
#
# Se mantienen los 2 fixes de la version anterior:
#   - Columnas bool (de pd.get_dummies) se castean a int antes de insertar,
#     para no repetir el bug de que quedaran como TEXT en vez de numericas.
#   - Carga idempotente: to_sql(if_exists="replace") reemplaza la tabla
#     completa en cada corrida, para que correr el pipeline N veces no
#     duplique filas.

import pandas as pd
import os
import logging
import sys
from datetime import datetime

from config import TRAIN_FILE, TEST_FILE, TABLE_TRAIN, TABLE_TEST, LOAD_REPORT, LOGS_DIR
from db import get_engine, DB_ENGINE_KIND

os.makedirs(LOGS_DIR, exist_ok=True)

logging.basicConfig(
    filename=os.path.join(LOGS_DIR, "load.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def load_to_database(csv_path, engine, table_name):
    """
    Carga un CSV ya validado y con features a una tabla relacional
    (SQLite o Cloud SQL PostgreSQL, segun DB_ENGINE), de forma idempotente.

    Retorna:
    tuple: (registros_exitosos, registros_fallidos)
    """
    try:
        df = pd.read_csv(csv_path)

        bool_cols = df.select_dtypes(include="bool").columns
        if len(bool_cols) > 0:
            df[bool_cols] = df[bool_cols].astype("int64")

        print(f"[INFO] Cargando {len(df)} registros desde {csv_path} -> tabla '{table_name}' ({DB_ENGINE_KIND})")
        logging.info(f"Iniciando carga de {len(df)} registros en '{table_name}' via {DB_ENGINE_KIND}")

        df.to_sql(
            table_name,
            engine,
            if_exists="replace",   # idempotente: reemplaza la tabla en cada corrida
            index=False,
            method="multi",        # insercion por lotes, no fila por fila
            chunksize=1000,        # evita el limite de parametros por statement en Postgres
        )

        registros_exitosos = len(df)
        registros_fallidos = 0

        reporte = {
            "fecha_carga": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "archivo_origen": csv_path,
            "motor": DB_ENGINE_KIND,
            "tabla_destino": table_name,
            "registros_totales": len(df),
            "registros_exitosos": registros_exitosos,
            "registros_fallidos": registros_fallidos,
            "carga_exitosa": True,
        }

        os.makedirs(os.path.dirname(LOAD_REPORT), exist_ok=True)
        modo = "a" if os.path.exists(LOAD_REPORT) else "w"
        pd.DataFrame([reporte]).to_csv(LOAD_REPORT, mode=modo, header=(modo == "w"), index=False)

        print(f"[OK] '{table_name}': {registros_exitosos} insertados, {registros_fallidos} fallidos")
        logging.info(f"Carga completada en '{table_name}': {registros_exitosos} ok / {registros_fallidos} fallidos")

        return registros_exitosos, registros_fallidos

    except Exception as e:
        logging.error(f"Error critico cargando '{table_name}': {str(e)}")
        print(f"[ERROR] {str(e)}")
        return 0, 0


if __name__ == "__main__":
    engine = get_engine()
    ok_train, fail_train = load_to_database(TRAIN_FILE, engine, TABLE_TRAIN)
    ok_test, fail_test = load_to_database(TEST_FILE, engine, TABLE_TEST)
    engine.dispose()

    exito = fail_train == 0 and fail_test == 0 and (ok_train + ok_test) > 0
    sys.exit(0 if exito else 1)
