# Objetivo: Abstraer la conexion a base de datos para que el resto del
# pipeline (load.py, train_model.py) no sepa ni le importe si esta hablando
# con el SQLite local o con un Cloud SQL (PostgreSQL) en la nube.
#
# Se elige con la variable de entorno DB_ENGINE:
#   DB_ENGINE=sqlite    (default, igual que hasta ahora, cero cambios)
#   DB_ENGINE=postgres  (Cloud SQL para PostgreSQL)
#
# Para Postgres se usa el Cloud SQL Python Connector, que es el metodo
# recomendado por Google para conectarse desde Cloud Run: maneja mTLS
# automaticamente y NO requiere levantar el Cloud SQL Auth Proxy como
# sidecar. La alternativa (socket unix /cloudsql/INSTANCE montado por
# Cloud Run con --add-cloudsql-instances) tambien se deja disponible por
# si se prefiere ese camino.

import os
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from config import DB_PATH

DB_ENGINE_KIND = os.environ.get("DB_ENGINE", "sqlite").lower()  # "sqlite" | "postgres"

CLOUDSQL_INSTANCE = os.environ.get("CLOUDSQL_INSTANCE")  # "project:region:instance"
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME", "bank_marketing")
CLOUDSQL_USE_CONNECTOR = os.environ.get("CLOUDSQL_USE_CONNECTOR", "true").lower() == "true"

_connector = None  # se reusa entre llamadas, no se crea uno por conexion


def _get_postgres_engine_via_connector() -> Engine:
    global _connector
    from google.cloud.sql.connector import Connector

    if _connector is None:
        _connector = Connector()

    def getconn():
        return _connector.connect(
            CLOUDSQL_INSTANCE,
            "pg8000",
            user=DB_USER,
            password=DB_PASSWORD,
            db=DB_NAME,
        )

    return create_engine("postgresql+pg8000://", creator=getconn, pool_pre_ping=True)


def _get_postgres_engine_via_socket() -> Engine:
    # Alternativa sin el connector: requiere que Cloud Run este configurado
    # con --add-cloudsql-instances=CLOUDSQL_INSTANCE, que monta el socket
    # unix en /cloudsql/INSTANCE_CONNECTION_NAME
    socket_path = f"/cloudsql/{CLOUDSQL_INSTANCE}"
    url = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@/{DB_NAME}?host={socket_path}"
    return create_engine(url, pool_pre_ping=True)


def get_engine() -> Engine:
    if DB_ENGINE_KIND == "postgres":
        faltantes = [v for v, val in [
            ("CLOUDSQL_INSTANCE", CLOUDSQL_INSTANCE),
            ("DB_USER", DB_USER),
            ("DB_PASSWORD", DB_PASSWORD),
        ] if not val]
        if faltantes:
            raise EnvironmentError(
                f"DB_ENGINE=postgres pero faltan variables de entorno: {faltantes}"
            )
        if CLOUDSQL_USE_CONNECTOR:
            return _get_postgres_engine_via_connector()
        return _get_postgres_engine_via_socket()

    # Default: SQLite local, exactamente igual que antes
    return create_engine(f"sqlite:///{DB_PATH}")
