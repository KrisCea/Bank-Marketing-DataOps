# Objetivo: Sincronizar archivos con Google Cloud Storage (GCS) para que
# el pipeline pueda correr como un Cloud Run Job (contenedor efimero: todo
# lo que no se suba a un bucket se pierde cuando el job termina).
#
# Se activa solo si la variable de entorno GCS_BUCKET esta definida.
# Si no esta definida, el pipeline corre igual que en local/Docker, sin
# tocar la nube para nada (util para desarrollo o para otros proveedores).

import os
import logging
from google.cloud import storage

logger = logging.getLogger(__name__)

GCS_BUCKET = os.environ.get("GCS_BUCKET")  # ej: "mi-bucket-bank-marketing"
GCS_RAW_BLOB = os.environ.get("GCS_RAW_BLOB", "raw/02_bank.csv")
GCS_RUNS_PREFIX = os.environ.get("GCS_RUNS_PREFIX", "runs")


def is_enabled():
    return bool(GCS_BUCKET)


def download_raw_input(local_raw_path):
    """Descarga el CSV crudo desde gs://{GCS_BUCKET}/{GCS_RAW_BLOB} al
    filesystem local del contenedor, antes de correr ingest.py."""
    if not is_enabled():
        return False

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(GCS_RAW_BLOB)

    os.makedirs(os.path.dirname(local_raw_path), exist_ok=True)
    blob.download_to_filename(local_raw_path)
    print(f"[GCS] Descargado gs://{GCS_BUCKET}/{GCS_RAW_BLOB} -> {local_raw_path}")
    return True


def upload_outputs(base_dir, run_id):
    """Sube data/processed, data/reports, models/ y logs/ al bucket, bajo
    un prefijo unico por corrida (run_id), para trazabilidad entre corridas
    del batch job."""
    if not is_enabled():
        return False

    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)

    carpetas = ["data/processed", "data/reports", "models", "logs"]
    subidos = 0
    for carpeta in carpetas:
        local_dir = os.path.join(base_dir, carpeta)
        if not os.path.isdir(local_dir):
            continue
        for root, _, files in os.walk(local_dir):
            for fname in files:
                local_path = os.path.join(root, fname)
                rel_path = os.path.relpath(local_path, base_dir)
                blob_path = f"{GCS_RUNS_PREFIX}/{run_id}/{rel_path}"
                bucket.blob(blob_path).upload_from_filename(local_path)
                subidos += 1

    print(f"[GCS] Subidos {subidos} archivos a gs://{GCS_BUCKET}/{GCS_RUNS_PREFIX}/{run_id}/")
    return True
