#/bin/bash
# if any of the commands fail, the script will exit
set -e

pwd

. ./common_scripts.sh

log building function_callling demo
log ===============================
cd ../demos/function_calling
docker compose build 2>&1 > ../build.log

log starting the function_calling demo
docker compose up -d 2>&1 >> ../build.log
cd -

log building model server
log =====================
cd ../model_server
poetry install 2>&1 >> ../build.log
log starting model server
log =====================
poetry run archgw_modelserver restart &
cd -

log building llm and prompt gateway rust modules
log ============================================
cd ../arch
sh build_filter_image.sh 2>&1 >> ../build.log
log starting the arch gateway service
log =================================
docker compose down 2>&1 >> ../build.log
log waiting for model service to be healthy
wait_for_healthz "http://localhost:51000/healthz" 300
docker compose up -d 2>&1 >> ../build.log
log waiting for arch gateway service to be healthy
wait_for_healthz "http://localhost:10000/healthz" 60
log waiting for arch gateway service to be healthy
cd -

log running e2e tests
log =================
poetry install 2>&1 >> ../build.log
poetry run pytest

log shutting down the arch gateway service
log ======================================
cd ../arch
docker compose stop 2>&1 >> ../build.log
cd -

log shutting down the function_calling demo
log =======================================
cd ../demos/function_calling
docker compose down 2>&1 >> ../build.log
cd -
