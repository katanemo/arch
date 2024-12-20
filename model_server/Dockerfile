FROM python:3.12 AS builder

COPY requirements.txt .
RUN pip install --prefix=/runtime -r requirements.txt

FROM python:3.12-slim AS output

# curl is needed for health check in docker-compose
RUN apt-get update && apt-get install -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=builder /runtime /usr/local

WORKDIR /src

# specify list of models that will go into the image as a comma separated list
# following models have been tested to work with this image
# "sentence-transformers/all-MiniLM-L6-v2,sentence-transformers/all-mpnet-base-v2,thenlper/gte-base,thenlper/gte-large,thenlper/gte-small"
ENV MODELS=""

COPY ./app ./app
COPY ./app/guard_model_config.yaml .
COPY ./app/openai_params.yaml .

# comment it out for now as we don't want to download the model every time we build the image
# we will mount host cache to docker image to avoid downloading the model every time
# see docker-compose file for more details

# RUN python install.py && \
#   find /root/.cache/torch/sentence_transformers/ -name onnx -exec rm -rf {} +

CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "80"]
