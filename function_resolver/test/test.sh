PORT="${PORT:-8001}"

echo localhost:$PORT/v1/chat/completions

curl -H "content-type: application/json" -XPOST localhost:$PORT/v1/chat/completions -d @test_payload.json
