#/bin/bash
# if any of the commands fail, the script will exit
set -e

pwd

. ./common_scripts.sh

log building function_callling demo
log ===============================
cd ../demos/function_calling
docker compose build

log starting the function_calling demo
docker compose up -d
cd -

log building model server
log =====================
cd ../model_server
poetry install
log starting model server
poetry run archgw_modelserver restart
cd -

log building llm and prompt gateway rust modules
log ============================================
cd ../arch
sh build_filter_image.sh
log starting the arch gateway service
log =================================
docker compose down
docker compose up &
wait_for_healthz "http://localhost:10000/healthz" 60
cd -

log running e2e tests
log =================
poetry install
poetry run pytest

log shutting down the arch gateway service
log ======================================
cd ../arch
docker compose stop
cd -

log shutting down the function_calling demo
log =======================================
cd ../demos/function_calling
docker compose down
cd -
