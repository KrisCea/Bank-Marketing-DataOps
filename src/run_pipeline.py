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

# El pipeline se ejecuta paso a paso. Cada paso llama a un script Python
# independiente que puede fallar sin afectar a los otros pasos.
# Esto facilita depurar su funcionamiento y mantener una estructura modular.

def run():
    src_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(src_dir)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    pasos = [
        ("Ingesta", ["python", os.path.join(src_dir, "ingest.py")]),
        ("Limpieza", ["python", os.path.join(src_dir, "clean_transform.py")]),
        ("Validacion", ["python", os.path.join(src_dir, "validate.py")]),
        ("Feature Engineering", ["python", os.path.join(src_dir, "feature_engineering.py")]),
        ("Carga a SQLite", ["python", os.path.join(src_dir, "load.py")]),
        ("Entrenamiento XGBoost", ["python", os.path.join(src_dir, "train_model.py")]),
    ]

    # Si GCS_BUCKET esta definida, el pipeline se ejecuta como un batch job
    # en la nube y descarga el archivo crudo antes de comenzar.
    use_gcs = bool(os.environ.get("GCS_BUCKET"))
    if use_gcs:
        from cloud_storage import download_raw_input, upload_outputs
        print(f"[INFO] GCS_BUCKET detectado. Corriendo como batch job (run_id={run_id})")
        download_raw_input(RAW_FILE)

    codigo_salida = 0
    for nombre, comando in pasos:
        print(f"\n{'='*60}\n>>> {nombre}\n{'='*60}")
        # Ejecutar cada paso desde la carpeta raiz para que los scripts
        # relativos (data/, logs/, etc.) funcionen correctamente.
        resultado = subprocess.run(comando, cwd=base_dir)
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
