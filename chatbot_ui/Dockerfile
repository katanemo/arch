FROM python:3.10 AS base

FROM base AS builder

WORKDIR /src

COPY requirements.txt /src/

RUN pip install --prefix=/runtime --force-reinstall -r requirements.txt

COPY . /src

FROM python:3.10-slim AS output

COPY --from=builder /runtime /usr/local

COPY /app /app
WORKDIR /app

CMD ["python", "run_stream.py"]
