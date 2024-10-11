# Function calling
This demo shows how you can use Arch's core function calling capabilites.

# Starting the demo
1. Please make sure the [pre-requisites](https://github.com/katanemo/arch/?tab=readme-ov-file#prerequisites) are installed correctly
2. Start Arch

3. 
   ```sh
   sh run_demo.sh
   ```
4. Navigate to http://localhost:18080/
5. You can type in queries like "how is the weather?"

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
