# Function calling
This demo shows how you can use intelligent prompt gateway to do function calling. This demo assumes you are using ollama running natively. If you want to run ollama running inside docker then please update ollama endpoint in docker-compose file.

# Starting the demo
1. Ensure that submodule is up to date
   ```sh
   git submodule sync --recursive
   ```
1. Create `.env` file and set OpenAI key using env var `OPENAI_API_KEY`
1. Start services
   ```sh
   docker compose up
   ```
1. Download Bolt-FC model. This demo assumes we have downloaded [Arch-Function-Calling-1.5B:Q4_K_M](https://huggingface.co/katanemolabs/Arch-Function-Calling-1.5B.gguf/blob/main/Arch-Function-Calling-1.5B-Q4_K_M.gguf) to local folder.
1. If running ollama natively run
   ```sh
   ollama serve
   ```
2. Create model file in ollama repository
   ```sh
   ollama create Arch-Function-Calling-1.5B:Q4_K_M -f Arch-Function-Calling-1.5B-Q4_K_M.model_file
   ```
3. Navigate to http://localhost:18080/
4. You can type in queries like "how is the weather in Seattle"
   - You can also ask follow up questions like "show me sunny days"
5. To see metrics navigate to "http://localhost:3000/" (use admin/grafana for login)
   - Open up dahsboard named "Intelligent Gateway Overview"
   - On this dashboard you can see reuqest latency and number of requests

# Observability
Arch gateway publishes stats endpoint at http://localhost:19901/stats. In this demo we are using prometheus to pull stats from envoy and we are using grafan to visalize the stats in dashboard. To see grafana dashboard follow instructions below,

1. Start grafana and prometheus using following command
   ```yaml
   docker compose --profile monitoring up
   ```
1. Navigate to http://localhost:3000/ to open grafana UI (use admin/grafana as credentials)
1. From grafana left nav click on dashboards and select "Intelligent Gateway Overview" to view arch gateway stats


Here is sample interaction,

<img width="575" alt="image" src="https://github.com/user-attachments/assets/e0929490-3eb2-4130-ae87-a732aea4d059">
