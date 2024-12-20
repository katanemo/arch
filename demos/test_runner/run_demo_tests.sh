#!/bin/bash
set -u

for demo in currency_exchange hr_agent
do
  echo "******************************************"
  echo "Running tests for $demo ..."
  echo "****************************************"
  pushd ../$demo
  archgw up arch_config.yaml
  docker compose up -d
  popd
  TEST_DATA=../$demo/test_data.yaml poetry run pytest
  pushd ../$demo
  docker compose down -v
  archgw down
  popd
done
