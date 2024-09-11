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

COPY --from=builder /runtime /usr/local

COPY /app /app
WORKDIR /app

RUN apt-get update && apt-get install -y \
  curl \
  && rm -rf /var/lib/apt/lists/*

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--log-config", "logger.yaml"]
