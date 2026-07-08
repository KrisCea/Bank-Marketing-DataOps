# Despliega el pipeline como un Cloud Run Job: un contenedor que se ejecuta
# hasta terminar (a diferencia de un Cloud Run "service", que queda
# escuchando HTTP). Solo se cobra por los segundos que efectivamente corre.
#
# Requisitos previos (una sola vez):
#   1. Cuenta de GCP (el "free trial" da credito inicial para probar esto).
#   2. gcloud CLI instalado: gcloud init && gcloud auth login
#   3. (Opcional, para RDBMS en la nube) Haber corrido antes
#      provision_cloud_sql.sh, que imprime el CLOUDSQL_INSTANCE a usar aca.
#
# Uso SIN Cloud SQL (sigue usando SQLite dentro del contenedor):
#   ./deploy_cloud_run_job.sh TU_PROJECT_ID TU_BUCKET_NAME
#
# Uso CON Cloud SQL (RDBMS en la nube, requiere provision_cloud_sql.sh antes):
#   ./deploy_cloud_run_job.sh TU_PROJECT_ID TU_BUCKET_NAME PROJECT:REGION:INSTANCE

set -euo pipefail

PROJECT_ID="${1:?Uso: ./deploy_cloud_run_job.sh PROJECT_ID BUCKET_NAME [CLOUDSQL_INSTANCE]}"
BUCKET_NAME="${2:?Uso: ./deploy_cloud_run_job.sh PROJECT_ID BUCKET_NAME [CLOUDSQL_INSTANCE]}"
CLOUDSQL_INSTANCE="${3:-}"   # opcional: "project:region:instance"

REGION="us-central1"
REPO_NAME="bank-marketing-repo"
JOB_NAME="bank-marketing-pipeline"
IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${JOB_NAME}:latest"
DB_NAME="bank_marketing"
DB_USER="pipeline_app"
SECRET_NAME="bank-marketing-db-password"

echo ">>> Configurando proyecto activo"
gcloud config set project "${PROJECT_ID}"

echo ">>> Habilitando APIs necesarias"
APIS="run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com storage.googleapis.com"
if [ -n "${CLOUDSQL_INSTANCE}" ]; then
  APIS="${APIS} sqladmin.googleapis.com secretmanager.googleapis.com"
fi
gcloud services enable ${APIS}

echo ">>> Creando bucket de GCS (si no existe)"
gsutil ls -b "gs://${BUCKET_NAME}" >/dev/null 2>&1 || \
  gsutil mb -l "${REGION}" "gs://${BUCKET_NAME}"

echo ">>> Subiendo el CSV crudo al bucket (ajusta la ruta local si es distinta)"
gsutil cp data/raw/02_bank.csv "gs://${BUCKET_NAME}/raw/02_bank.csv"

echo ">>> Creando repositorio de Artifact Registry (si no existe)"
gcloud artifacts repositories describe "${REPO_NAME}" --location="${REGION}" >/dev/null 2>&1 || \
  gcloud artifacts repositories create "${REPO_NAME}" \
    --repository-format=docker \
    --location="${REGION}"

echo ">>> Construyendo y subiendo la imagen con Cloud Build"
gcloud builds submit --tag "${IMAGE_URI}" .

ENV_VARS="GCS_BUCKET=${BUCKET_NAME},PIPELINE_RANDOM_SEED=42,PIPELINE_TEST_SIZE=0.2,PIPELINE_SCALE_FEATURES=false"
DEPLOY_FLAGS=()

if [ -n "${CLOUDSQL_INSTANCE}" ]; then
  echo ">>> Modo RDBMS en la nube: se conectara a Cloud SQL ${CLOUDSQL_INSTANCE}"
  ENV_VARS="${ENV_VARS},DB_ENGINE=postgres,CLOUDSQL_INSTANCE=${CLOUDSQL_INSTANCE},DB_USER=${DB_USER},DB_NAME=${DB_NAME},CLOUDSQL_USE_CONNECTOR=true"
  DEPLOY_FLAGS+=(--set-secrets "DB_PASSWORD=${SECRET_NAME}:latest")
  DEPLOY_FLAGS+=(--add-cloudsql-instances "${CLOUDSQL_INSTANCE}")
else
  echo ">>> Modo SQLite (sin RDBMS externo). Para migrar a Cloud SQL,"
  echo "    corre primero provision_cloud_sql.sh y vuelve a llamar a este"
  echo "    script pasando el CLOUDSQL_INSTANCE como tercer argumento."
fi

echo ">>> Creando/actualizando el Cloud Run Job"
gcloud run jobs deploy "${JOB_NAME}" \
  --image "${IMAGE_URI}" \
  --region "${REGION}" \
  --memory 1Gi \
  --cpu 1 \
  --max-retries 1 \
  --task-timeout 900 \
  --set-env-vars "${ENV_VARS}" \
  "${DEPLOY_FLAGS[@]}"

echo ">>> Dando permisos al service account del job"
SERVICE_ACCOUNT=$(gcloud run jobs describe "${JOB_NAME}" --region "${REGION}" \
  --format='value(spec.template.spec.template.spec.serviceAccountName)')
if [ -n "${SERVICE_ACCOUNT}" ]; then
  gsutil iam ch "serviceAccount:${SERVICE_ACCOUNT}:roles/storage.objectAdmin" "gs://${BUCKET_NAME}"

  if [ -n "${CLOUDSQL_INSTANCE}" ]; then
    gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
      --member="serviceAccount:${SERVICE_ACCOUNT}" \
      --role="roles/cloudsql.client" \
      --condition=None
    gcloud secrets add-iam-policy-binding "${SECRET_NAME}" \
      --member="serviceAccount:${SERVICE_ACCOUNT}" \
      --role="roles/secretmanager.secretAccessor"
  fi
fi

echo ""
echo ">>> Listo. Para ejecutar el job manualmente:"
echo "    gcloud run jobs execute ${JOB_NAME} --region ${REGION}"
echo ""
echo ">>> Para ver logs de la ultima ejecucion:"
echo "    gcloud run jobs executions list --job ${JOB_NAME} --region ${REGION}"
echo ""
echo ">>> (Opcional) Para programarlo periodicamente con Cloud Scheduler:"
echo "    gcloud scheduler jobs create http ${JOB_NAME}-scheduler \\"
echo "      --location ${REGION} \\"
echo "      --schedule '0 6 * * *' \\"
echo "      --uri \"https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run\" \\"
echo "      --http-method POST \\"
echo "      --oauth-service-account-email ${SERVICE_ACCOUNT}"
