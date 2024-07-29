# Weather forecasting
This demo shows how you can use intelligent prompt gateway to provide realtime weather forecast.

# Startig the demo
1. Create `.env` file and set OpenAI key using env var `OPENAI_API_KEY`
2. Ensure that envoy filter binary is built
   ```sh
   $ bash -c "cd ../../envoyfilter && sh build_filter.sh"
   ```
3. Build docker compose images
   ```sh
   $ docker compose build
   ```
4. Start qdrant service and initialize collection
  ```sh
  $ docker compose up qdrant
  $ sh init_vector_store.sh
  ```
1. Start services
  ```sh
  $ docker compose up
  ```
1. Navigate to http://localhost:18080/
