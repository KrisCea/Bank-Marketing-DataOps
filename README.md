# Bank Marketing DataOps

## Descripción del proyecto

Este proyecto implementa un pipeline de DataOps para el dataset de Bank Marketing con enfoque en limpieza, validación, carga y entrenamiento de un modelo predictivo. El flujo está diseñado para ejecutarse tanto localmente como en un entorno de nube con Google Cloud Run y Cloud SQL.

El pipeline cubre las siguientes etapas:

1. Ingesta del archivo CSV crudo.
2. Limpieza y transformación de variables.
3. Validación estructural y semántica.
4. Carga a una base de datos relacional.
5. Entrenamiento de un modelo XGBoost.

## Objetivo

Preparar los datos para entrenar un modelo que prediga si un cliente suscribirá un depósito a plazo, manteniendo trazabilidad, reportes de calidad y una ejecución reproducible.

## Características principales

- Pipeline modular y fácil de extender.
- Procesamiento y limpieza de datos con imputación por moda.
- Transformación de variables binarias y categóricas.
- Escalado de variables numéricas.
- Validaciones automáticas con reportes en CSV y texto.
- Carga idempotente a SQLite o PostgreSQL.
- Entrenamiento con XGBoost y generación de métricas.
- Integración opcional con Google Cloud Storage para jobs batch en la nube.

## Estructura del proyecto

```text
bank-marketing-dataops/
├── data/
│   ├── raw/                     # Archivo fuente original
│   ├── processed/               # Datos ingeridos, limpios y preparados
│   └── reports/                 # Reportes de validación y carga
├── logs/                        # Archivos de log por etapa
├── models/                      # Modelo entrenado y metadata
├── src/
│   ├── clean_transform.py       # Limpieza y transformación
│   ├── cloud_storage.py         # Integración opcional con GCS
│   ├── config.py                # Configuración centralizada
│   ├── db.py                    # Conexión a SQLite/PostgreSQL
│   ├── ingest.py                # Ingesta del dataset
│   ├── load.py                  # Carga a base de datos
│   ├── run_pipeline.py          # Orquestador del pipeline
│   ├── train_model.py           # Entrenamiento del modelo
│   └── validate.py              # Validaciones del dataset
├── requirements.txt
└── README.md
```

## Requisitos

- Python 3.9 o superior
- pip actualizado
- Dependencias indicadas en [requirements.txt](requirements.txt)

## Instalación

1. Crear y activar un entorno virtual:

```bash
python -m venv .venv
source .venv/bin/activate
```

2. Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Ejecución local

### Opción 1: Ejecutar todo el pipeline

```bash
python src/run_pipeline.py
```

### Opción 2: Ejecutar etapa por etapa

```bash
python src/ingest.py
python src/clean_transform.py
python src/validate.py
python src/load.py
python src/train_model.py
```

## Archivos de entrada y salida

### Entrada esperada

- [data/raw/02_bank.csv](data/raw/02_bank.csv)

### Salidas principales

- [data/processed/02_bank_ingested.csv](data/processed/02_bank_ingested.csv)
- [data/processed/02_bank_clean.csv](data/processed/02_bank_clean.csv)
- [data/reports/validation_report.csv](data/reports/validation_report.csv)
- [data/reports/validation_report.txt](data/reports/validation_report.txt)
- [data/reports/load_report.csv](data/reports/load_report.csv)
- [models](models)
- [logs](logs)

## Descripción de las etapas

### 1. Ingesta

El script [src/ingest.py](src/ingest.py) copia el archivo CSV desde la carpeta raw a processed y registra información básica del dataset.

### 2. Limpieza y transformación

El script [src/clean_transform.py](src/clean_transform.py) realiza:

- Reemplazo de valores `unknown` por la moda de cada columna.
- Conversión de variables binarias tipo yes/no a 1/0.
- Codificación one-hot para variables categóricas.
- Escalado de variables numéricas con StandardScaler.

### 3. Validación

El script [src/validate.py](src/validate.py) verifica:

- Valores nulos en columnas críticas.
- Rangos válidos de edad, pdays y campaign.
- Que la variable objetivo tenga únicamente valores 0 y 1.

Los reportes se almacenan en [data/reports](data/reports).

### 4. Carga a base de datos

El script [src/load.py](src/load.py) carga los datos a una tabla en SQLite por defecto. También puede apuntar a PostgreSQL si se configura el entorno adecuado.

### 5. Entrenamiento del modelo

El script [src/train_model.py](src/train_model.py) entrena un modelo XGBoost y genera:

- Archivo del modelo en [models](models)
- Metadata del entrenamiento
- Reporte con métricas y variables más importantes

## Configuración de base de datos

Por defecto el proyecto usa SQLite y genera el archivo [bank_marketing.db](bank_marketing.db).

Si deseas usar PostgreSQL en Cloud SQL, define estas variables de entorno:

```bash
export DB_ENGINE=postgres
export CLOUDSQL_INSTANCE=project:region:instance
export DB_USER=postgres
export DB_PASSWORD=your_password
export DB_NAME=bank_marketing
export CLOUDSQL_USE_CONNECTOR=true
```

## Uso con Google Cloud Storage

El pipeline también puede ejecutarse como un job batch en la nube. Para habilitarlo, define:

```bash
export GCS_BUCKET=your-bucket-name
export GCS_RAW_BLOB=raw/02_bank.csv
export GCS_RUNS_PREFIX=runs
```

Con esta configuración, el pipeline descargará el archivo crudo desde GCS antes de ejecutar y subirá los artefactos generados al bucket al finalizar.

## Variables importantes

- [src/config.py](src/config.py): centraliza rutas, nombres de tablas y parámetros del modelo.
- [src/db.py](src/db.py): abstrae la conexión a SQLite o PostgreSQL.
- [src/run_pipeline.py](src/run_pipeline.py): orquesta la ejecución completa.

## Solución de problemas

- Si aparece un error de módulo faltante, vuelve a ejecutar:

```bash
pip install -r requirements.txt
```

- Si el archivo fuente no existe, asegúrate de que [data/raw/02_bank.csv](data/raw/02_bank.csv) esté presente.

- Si una etapa falla, revisa los logs en [logs](logs) para identificar el problema.

## Notas adicionales

El proyecto está preparado para ser extendido con nuevas etapas de feature engineering, despliegue del modelo o integración con herramientas de monitoreo y orquestación.

