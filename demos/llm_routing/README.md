# LLM Routing
This demo shows how you can arch gateway to manage keys and route to appropricate LLM.

# Starting the demo
1. Please make sure the [pre-requisites](https://github.com/katanemo/arch/?tab=readme-ov-file#prerequisites) are installed correctly
1. Start Arch
   ```sh
   sh run_demo.sh
   ```
1. Navigate to http://localhost:18080/

# Observability
Arch gateway publishes stats endpoint at http://localhost:19901/stats. In this demo we are using prometheus to pull stats from arch and we are using grafana to visalize the stats in dashboard. To see grafana dashboard follow instructions below,

1. Navigate to http://localhost:3000/ to open grafana UI (use admin/grafana as credentials)
1. From grafana left nav click on dashboards and select "Intelligent Gateway Overview" to view arch gateway stats

# Selecting different LLM
You can pick different LLM based on header `x-arch-llm-provider-hint` to override default LLM.
