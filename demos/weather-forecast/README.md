# Weather forecasting
This demo shows how you can use intelligent prompt gateway to provide realtime weather forecast.

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
1. Navigate to http://localhost:18080/
1. You can type in queries like "how is the weather in Seattle"
   1. You can also ask follow up questions like "show me sunny days"
1. To see metrics navigate to "http://localhost:3000/" (use admin/grafana for login)
   1. Open up dahsboard named "Intelligent Gateway Overview"
   2. On this dashboard you can see reuqest latency and number of requests
