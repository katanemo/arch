PORT="${PORT:-8001}"

echo localhost:$PORT/katanemo_kfc_1b/v1/chat/completions

curl -v -H "content-type: application/json" -XPOST localhost:$PORT/katanemo_kfc_1b/v1/chat/completions -d @test_payload.json
