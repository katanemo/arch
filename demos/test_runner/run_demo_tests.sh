#!/bin/bash
set -eu

# for demo in currency_exchange hr_agent
for demo in currency_exchange
do
  echo "******************************************"
  echo "Running tests for $demo ..."
  echo "****************************************"
  cd ../$demo
  archgw up arch_config.yaml
  docker compose up -d
  cd ../test_runner
  TEST_DATA=../$demo/test_data.yaml poetry run pytest
  cd ../$demo
  archgw down
  docker compose down -v
  cd ../test_runner
done
