#!/bin/sh

echo 'Deleting prompt_vector_store collection'
curl -X DELETE http://localhost:16333/collections/prompt_vector_store
echo
echo 'Creating prompt_vector_store collection'
curl -X PUT 'http://localhost:16333/collections/prompt_vector_store' \
  -H 'Content-Type: application/json' \
  --data-raw '{
    "vectors": {
      "size": 1024,
      "distance": "Cosine"
    }
  }'
echo
echo 'Created prompt_vector_store collection'
