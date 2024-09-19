# Function calling
This demo shows how you can use intelligent prompt gateway as a network copilot that could give information about correlation between packet loss with device reboots, downs, or maintainence. This demo assumes you are using ollama running natively. If you want to run ollama running inside docker then please update ollama endpoint in docker-compose file.

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
1. Download Bolt-FC model. This demo assumes we have downloaded [Bolt-Function-Calling-1B:Q4_K_M](https://huggingface.co/katanemolabs/Bolt-Function-Calling-1B.gguf/blob/main/Bolt-Function-Calling-1B-Q4_K_M.gguf) to local folder.
1. If running ollama natively run
   ```sh
   ollama serve
   ```
2. Create model file in ollama repository
   ```sh
   ollama create Bolt-Function-Calling-1B:Q4_K_M -f Bolt-FC-1B-Q4_K_M.model_file
   ```
3. Navigate to http://localhost:18080/
4. You can type in queries like "show me any packet drops due to interface failure in the past 3 days"
   - You can also ask follow up questions like "show me just the ones with maximum 200 in errors"
5. To see metrics navigate to "http://localhost:3000/" (use admin/grafana for login)
   - Open up dahsboard named "Intelligent Gateway Overview"
   - On this dashboard you can see reuqest latency and number of requests
