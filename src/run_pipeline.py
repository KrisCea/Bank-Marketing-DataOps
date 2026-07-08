# Objetivo: Orquestar el pipeline completo en orden, deteniendose en el primer paso que falle. 
# Este es el entrypoint que usa el contenedor Docker y, en la nube, el Cloud Run Job.
#
# Si la variable de entorno GCS_BUCKET esta definida:
# Si GCS_BUCKET no esta definida, el pipeline corre exactamente igual que
# en local/Docker: no se importa siquiera el cliente de GCS.

import subprocess
import sys
import os
from datetime import datetime

from config import BASE_DIR, RAW_FILE

PASOS = [
    ("Ingesta", ["python", "ingest.py"]),
    ("Limpieza", ["python", "clean_transform.py"]),
    ("Validacion", ["python", "validate.py"]),
    ("Feature Engineering", ["python", "feature_engineering.py"]),
    ("Carga a SQLite", ["python", "load.py"]),
    ("Entrenamiento XGBoost", ["python", "train_model.py"]),
]


def run():
    src_dir = os.path.dirname(os.path.abspath(__file__))
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    use_gcs = bool(os.environ.get("GCS_BUCKET"))
    if use_gcs:
        from cloud_storage import download_raw_input, upload_outputs
        print(f"[INFO] GCS_BUCKET detectado. Corriendo como batch job (run_id={run_id})")
        download_raw_input(RAW_FILE)

    codigo_salida = 0
    for nombre, comando in PASOS:
        print(f"\n{'='*60}\n>>> {nombre}\n{'='*60}")
        resultado = subprocess.run(comando, cwd=src_dir)
        if resultado.returncode != 0:
            print(f"\n[PIPELINE DETENIDO] El paso '{nombre}' fallo (codigo {resultado.returncode}).")
            codigo_salida = resultado.returncode
            break
    else:
        print("\n[PIPELINE COMPLETO] Todos los pasos finalizaron correctamente.")

    if use_gcs:
        # Se sube lo que se haya alcanzado a producir, incluso si el
        # pipeline fallo a mitad de camino: sirve para depurar la corrida
        # revisando los logs/reportes subidos.
        upload_outputs(BASE_DIR, run_id)

    sys.exit(codigo_salida)


if __name__ == "__main__":
    run()
