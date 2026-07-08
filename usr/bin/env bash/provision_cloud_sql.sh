# Crea una instancia de Cloud SQL para PostgreSQL para reemplazar el
# SQLite local, mas la base de datos, el usuario, y guarda la contrasena
# en Secret Manager (nunca en texto plano en variables de entorno).
#
# IMPORTANTE SOBRE COSTOS (a diferencia del Cloud Run Job del batch,
# que solo cobra mientras corre): Cloud SQL es un servidor que queda
# corriendo de forma continua. Incluso en el tier mas chico disponible
# (db-f1-micro, pensado solo para desarrollo/pruebas, sin SLA), tiene un
# costo mensual aproximado de unos pocos dolares por mes en la region
# us-central1, ademas del almacenamiento. Si el presupuesto es cero por
# ahora, dos alternativas:
#   a) Crear la instancia, probarla, y borrarla cuando no la necesites
#      (gcloud sql instances delete), o
#   b) Detenerla entre corridas del batch job:
#        gcloud sql instances patch INSTANCE_NAME --activation-policy=NEVER
#      y reactivarla antes de correr el job:
#        gcloud sql instances patch INSTANCE_NAME --activation-policy=ALWAYS
#      (el almacenamiento se sigue cobrando aunque este detenida, pero el
#      computo no). Revisa la calculadora de precios oficial antes de
#      dejarla corriendo de forma permanente.
#
# Uso:
#   chmod +x provision_cloud_sql.sh
#   ./provision_cloud_sql.sh TU_PROJECT_ID

set -euo pipefail

PROJECT_ID="${1:?Uso: ./provision_cloud_sql.sh PROJECT_ID}"
REGION="us-central1"
INSTANCE_NAME="bank-marketing-db"
DB_NAME="bank_marketing"
DB_USER="pipeline_app"
SECRET_NAME="bank-marketing-db-password"

echo ">>> Configurando proyecto activo"
gcloud config set project "${PROJECT_ID}"

echo ">>> Habilitando APIs necesarias"
gcloud services enable \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com

echo ">>> Generando contrasena aleatoria y guardandola en Secret Manager"
DB_PASSWORD=$(openssl rand -base64 24)
if gcloud secrets describe "${SECRET_NAME}" >/dev/null 2>&1; then
  echo -n "${DB_PASSWORD}" | gcloud secrets versions add "${SECRET_NAME}" --data-file=-
else
  echo -n "${DB_PASSWORD}" | gcloud secrets create "${SECRET_NAME}" --data-file=-
fi

echo ">>> Creando instancia Cloud SQL PostgreSQL (tier db-f1-micro, el mas economico)"
gcloud sql instances describe "${INSTANCE_NAME}" >/dev/null 2>&1 || \
  gcloud sql instances create "${INSTANCE_NAME}" \
    --database-version=POSTGRES_16 \
    --tier=db-f1-micro \
    --region="${REGION}" \
    --storage-size=10GB \
    --storage-auto-increase

echo ">>> Creando base de datos '${DB_NAME}'"
gcloud sql databases describe "${DB_NAME}" --instance="${INSTANCE_NAME}" >/dev/null 2>&1 || \
  gcloud sql databases create "${DB_NAME}" --instance="${INSTANCE_NAME}"

echo ">>> Creando usuario '${DB_USER}'"
gcloud sql users create "${DB_USER}" \
  --instance="${INSTANCE_NAME}" \
  --password="${DB_PASSWORD}" 2>/dev/null || \
  gcloud sql users set-password "${DB_USER}" \
    --instance="${INSTANCE_NAME}" \
    --password="${DB_PASSWORD}"

INSTANCE_CONNECTION_NAME=$(gcloud sql instances describe "${INSTANCE_NAME}" \
  --format='value(connectionName)')

echo ""
echo ">>> Listo. Datos de conexion:"
echo "    CLOUDSQL_INSTANCE=${INSTANCE_CONNECTION_NAME}"
echo "    DB_NAME=${DB_NAME}"
echo "    DB_USER=${DB_USER}"
echo "    (password guardado en Secret Manager, secreto: ${SECRET_NAME})"
echo ""
echo ">>> Siguiente paso: correr deploy_cloud_run_job.sh con estos valores"
echo "    para que el Cloud Run Job se conecte a esta instancia."
