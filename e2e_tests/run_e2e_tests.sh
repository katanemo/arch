#/bin/sh
# if any of the commands fail, the script will exit
set -e

pwd

. ./common_scripts.sh

log building function_callling demo
pushd ../demos/function_calling
docker compose build

log starting the function_calling demo
docker compose up -d
popd

log building model server
pushd ../model_server
poetry install
log starting model server
archgw_modelserver restart
popd

log building llm and prompt gateway rust modules
pushd ../arch
sh build_filter_image.sh
log starting the arch gateway service
ARCH_CONFIG_FILE=../demos/function_calling/arch_config.yaml
docker compose -f docker-compose.dev.yaml down
docker compose -f docker-compose.dev.yaml up -d
popd

wait_for_healthz "http://localhost:10000/healthz" 60

log running e2e tests
poetry install
poetry run pytest

log shutting down the arch gateway service
pushd ../arch
docker compose -f docker-compose.dev.yaml stop
popd

log shutting down the function_calling demo
pushd ../demos/function_calling
docker compose down
popd
