#/bin/bash
# if any of the commands fail, the script will exit
set -e

. ./common_scripts.sh

print_disk_usage

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

log building and running function_callling demo
log ===========================================
cd ../demos/function_calling
docker compose up api_server --build -d
cd -

print_disk_usage

# log building model server
# log =====================
# cd ../model_server
# poetry install 2>&1 >> ../build.log
# print_disk_usage

# log starting model server
# log =====================
# mkdir -p ~/archgw_logs
# touch ~/archgw_logs/modelserver.log
# poetry run archgw_modelserver restart &
# tail -F ~/archgw_logs/modelserver.log &
# model_server_tail_pid=$!
# cd -

log building model server
log =====================
cd ../model_server
poetry install
cd -

log building archgw cli
log ===================
cd ../arch/tools
sh build_cli.sh
cd -

log building docker image for arch gateway
log ======================================
cd ../arch
sh build_filter_image.sh
cd -

log startup arch gateway with function calling demo
cd ..
touch ~/archgw_logs/modelserver.log
tail -F ~/archgw_logs/modelserver.log &
model_server_tail_pid=$!
archgw down
archgw up demos/function_calling/arch_config.yaml
kill $model_server_tail_pid
cd -

log running e2e tests
log =================
poetry install
poetry run pytest

log shutting down the arch gateway service
log ======================================
cd ../
archgw down
cd -

log shutting down the function_calling demo
log =======================================
cd ../demos/function_calling
docker compose down
cd -
