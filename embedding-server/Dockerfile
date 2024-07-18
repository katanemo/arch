# copied from https://github.com/bergos/embedding-server

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

COPY --from=builder /runtime /usr/local

COPY /app /app
WORKDIR /app

RUN apt-get update && apt-get install -y \
  curl \
  && rm -rf /var/lib/apt/lists/*

RUN python install.py
# RUN python install.py && \
#   find /root/.cache/torch/sentence_transformers/ -name onnx -exec rm -rf {} +


CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
