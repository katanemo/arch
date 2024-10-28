#/bin/bash
# if any of the commands fail, the script will exit
set -e

. ./common_scripts.sh

print_debug() {
  log "Received signal to stop"
  log "Printing debug logs for model_server"
  log "===================================="
  tail -n 500 ~/archgw_logs/modelserver.log
  log "Printing debug logs for docker"
  log "===================================="
  tail -n 500 ../build.log
}

trap 'print_debug' INT TERM ERR

log starting > ../build.log

log building function_callling demo
log ===============================
cd ../demos/function_calling
docker compose build -q

log starting the function_calling demo
docker compose up -d
cd -

log building model server
log =====================
cd ../model_server
poetry install 2>&1 >> ../build.log
log starting model server
log =====================
touch ~/archgw_logs/modelserver.log
poetry run archgw_modelserver restart &
tail -F ~/archgw_logs/modelserver.log &
model_server_tail_pid=$!
cd -

log building llm and prompt gateway rust modules
log ============================================
cd ../arch
docker build  -f Dockerfile .. -t katanemo/archgw -q
log starting the arch gateway service
log =================================
docker compose -f docker-compose.e2e.yaml down
log waiting for model service to be healthy
wait_for_healthz "http://localhost:51000/healthz" 300
kill $model_server_tail_pid
docker compose -f docker-compose.e2e.yaml up -d
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
docker compose -f docker-compose.e2e.yaml stop 2>&1 >> ../build.log
cd -

log shutting down the function_calling demo
log =======================================
cd ../demos/function_calling
docker compose down 2>&1 >> ../build.log
cd -

log shutting down the model server
log ==============================
cd ../model_server
poetry run archgw_modelserver stop 2>&1 >> ../build.log
cd -
