# Function calling
This demo shows how you can use intelligent prompt gateway to do function calling. This demo assumes you are using ollama running natively. If you want to run ollama running inside docker then please update ollama endpoint in docker-compose file.

# Startig the demo
1. Ensure that submodule is up to date
   ```sh
   git submodule sync --recursive
   ```
1. Create `.env` file and set OpenAI key using env var `OPENAI_API_KEY`
1. Start services
   ```sh
   docker compose up
   ```
1. Download Bolt-FC model. This demo assumes we have downloaded `Bolt-Function-Calling-1B:Q4_K_M` to local folder
2. Create model file in ollama repository
   ```sh
   ollama create Bolt-Function-Calling-1B:Q4_K_M -f Bolt-FC-1B-Q4_K_M.model_file
   ```
3. Navigate to http://localhost:18080/
4. You can type in queries like "how is the weather in Seattle"
   1. You can also ask follow up questions like "show me sunny days"
5. To see metrics navigate to "http://localhost:3000/" (use admin/grafana for login)
   1. Open up dahsboard named "Intelligent Gateway Overview"
   2. On this dashboard you can see reuqest latency and number of requests
