#/bin/bash
# if any of the commands fail, the script will exit
set -e

. ./common_scripts.sh

print_disk_usage

mkdir -p ~/archgw_logs
touch ~/archgw_logs/modelserver.log

print_debug() {
  log "Received signal to stop"
  log "Printing debug logs for model_server"
  log "===================================="
  tail -n 100 ~/archgw_logs/modelserver.log
  log "Printing debug logs for docker"
  log "===================================="
  tail -n 100 ../build.log
  archgw logs --debug | tail -n 100
}

trap 'print_debug' INT TERM ERR

log starting > ../build.log

log building and running function_callling demo
log ===========================================
cd ../../demos/weather_forecast/
docker compose up weather_forecast_service --build -d
cd -

log building and install model server
log =================================
cd ../../model_server
poetry install
cd -

log building and installing archgw cli
log ==================================
cd ../../arch/tools
poetry install
cd -

log building docker image for arch gateway
log ======================================
cd ../../
archgw build
cd -

log startup arch gateway with function calling demo
cd ../../
tail -F ~/archgw_logs/modelserver.log &
model_server_tail_pid=$!
archgw down
archgw up demos/weather_forecast/arch_config.yaml
kill $model_server_tail_pid
cd -

log running e2e tests
log =================
poetry install
poetry run pytest

log shutting down the arch gateway service
log ======================================
archgw down

log shutting down the weather_forecast demo
log =======================================
cd ../../demos/weather_forecast
docker compose down
cd -
