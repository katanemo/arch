FROM python:3.10 AS base

FROM base AS builder

WORKDIR /src

COPY requirements.txt /src/

# RUN apt-get update

# RUN apt-get install -y \
#     build-essential \
#     curl

# RUN curl https://sh.rustup.rs -sSf | bash -s -- -y

RUN pip install --prefix=/runtime --force-reinstall -r requirements.txt

COPY . /src

FROM python:3.10-slim AS output

COPY --from=builder /runtime /usr/local

COPY /app /app
WORKDIR /app

CMD ["python", "run.py"]
