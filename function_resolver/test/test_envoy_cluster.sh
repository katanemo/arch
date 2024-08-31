PORT="${PORT:-8001}"

echo localhost:$PORT/bolt_fc_1b/v1/chat/completions

curl -v -H "content-type: application/json" -XPOST localhost:$PORT/bolt_fc_1b/v1/chat/completions -d @test_payload.json
