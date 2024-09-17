FROM python:3 AS base

#
# builder
#
FROM base AS builder

WORKDIR /src

COPY requirements.txt /src/
RUN pip install --prefix=/runtime --force-reinstall -r requirements.txt

COPY . /src

#
# output
#

FROM python:3-slim AS output

# specify list of models that will go into the image as a comma separated list
# following models have been tested to work with this image
# "sentence-transformers/all-MiniLM-L6-v2,sentence-transformers/all-mpnet-base-v2,thenlper/gte-base,thenlper/gte-large,thenlper/gte-small"
ENV MODELS="BAAI/bge-large-en-v1.5"
ENV NER_MODELS="urchade/gliner_large-v2.1"

COPY --from=builder /runtime /usr/local

COPY /app /app
WORKDIR /app

RUN apt-get update && apt-get install -y \
  curl \
  && rm -rf /var/lib/apt/lists/*

RUN huggingface-cli download katanemolabs/toxic-onnx-quantized --local-dir /app/model/toxic
RUN huggingface-cli download katanemolabs/jailbreak_onnx_quantized_v2 --local-dir /app/model/jailbreak

# comment it out for now as we don't want to download the model every time we build the image
# we will mount host cache to docker image to avoid downloading the model every time
# see docker-compose file for more details

# RUN python install.py && \
#   find /root/.cache/torch/sentence_transformers/ -name onnx -exec rm -rf {} +

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
