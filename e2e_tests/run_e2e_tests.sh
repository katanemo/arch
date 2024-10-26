#/bin/sh
# if any of the commands fail, the script will exit
set -e

pwd

. ./common_scripts.sh

log building function_callling demo
cd ../demos/function_calling
docker compose build

log starting the function_calling demo
docker compose up -d
cd -

log building model server
cd ../model_server
poetry install
log starting model server
poetry run archgw_modelserver restart
cd -

log building llm and prompt gateway rust modules
cd ../arch
sh build_filter_image.sh
log starting the arch gateway service
docker compose -f docker-compose.yaml down
docker compose -f docker-compose.yaml up -d
cd -

wait_for_healthz "http://localhost:10000/healthz" 60

log running e2e tests
poetry install
poetry run pytest

log shutting down the arch gateway service
cd ../arch
docker compose -f docker-compose.yaml stop
cd -

log shutting down the function_calling demo
cd ../demos/function_calling
docker compose down
cd -
