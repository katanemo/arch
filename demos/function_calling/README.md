# Function calling
This demo shows how you can use Arch's function calling capabilites.

# Starting the demo
1. Create `.env` file and set OpenAI key using env var `OPENAI_API_KEY`
2. Start Arch
   ```sh
   archgw up arch_config.yaml
   ```
3. Start Network Agent
    ```sh
    docker compose up
   ```
4. Navigate to http://localhost:18080/
4. You can type in queries like "how is the weather in Seattle"
   - You can also ask follow up questions like "show me sunny days"
6. To see metrics navigate to "http://localhost:3000/" (use admin/grafana for login)
   - Open up dahsboard named "Intelligent Gateway Overview"
   - On this dashboard you can see reuqest latency and number of requests

# Observability
Arch gateway publishes stats endpoint at http://localhost:19901/stats. In this demo we are using prometheus to pull stats from arch and we are using grafana to visalize the stats in dashboard. To see grafana dashboard follow instructions below,

1. Start grafana and prometheus using following command
   ```yaml
   docker compose --profile monitoring up
   ```
1. Navigate to http://localhost:3000/ to open grafana UI (use admin/grafana as credentials)
1. From grafana left nav click on dashboards and select "Intelligent Gateway Overview" to view arch gateway stats


Here is a sample interaction,
<img width="575" alt="image" src="https://github.com/user-attachments/assets/e0929490-3eb2-4130-ae87-a732aea4d059">
