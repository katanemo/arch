FROM nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu20.04 AS base

#
# builder
#
FROM base AS builder

WORKDIR /src
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1


# Create a symlink so that `python` points to `python3`

# Install Python packages if necessary
RUN pip3 install --upgrade pip

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 \
    python3-pip \
    python3-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN ln -s /usr/bin/python3 /usr/bin/python && \
    ln -s /usr/bin/pip3 /usr/bin/pip

RUN pip install --upgrade pip

# Install git (needed for cloning the repository)
RUN apt-get update && apt-get install -y git && apt-get clean

COPY requirements.txt /src/

RUN pip install --prefix=/runtime --force-reinstall -r requirements.txt
RUN if command -v nvidia-smi >/dev/null 2>&1 && command -v nvcc >/dev/null 2>&1; then \
        echo "CUDA and NVIDIA GPU detected, installing EETQ..." && \
        git clone https://github.com/NetEase-FuXi/EETQ.git && \
        cd EETQ && \
        git submodule update --init --recursive && \
        pip install .; \
    else \
        echo "CUDA or NVIDIA GPU not detected, skipping EETQ installation."; \
    fi


COPY . /src

#
# output
#

FROM nvidia/cuda:11.7.1-cudnn8-runtime-ubuntu20.04 AS output

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

# comment it out for now as we don't want to download the model every time we build the image
# we will mount host cache to docker image to avoid downloading the model every time
# see docker-compose file for more details

# RUN python install.py && \
#   find /root/.cache/torch/sentence_transformers/ -name onnx -exec rm -rf {} +

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
