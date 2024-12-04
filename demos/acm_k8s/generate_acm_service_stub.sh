docker run --rm -v "${PWD}:/local" openapitools/openapi-generator-cli:latest generate \
  --skip-validate-spec \
  -i /local/acm_api.yaml \
  -g python-flask \
  -o /local/acm_server \
  # --additional-properties=defaultController=your.package.YourController \
