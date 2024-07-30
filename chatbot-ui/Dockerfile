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

FROM python:3-slim AS output

COPY --from=builder /runtime /usr/local

COPY /app /app
WORKDIR /app

CMD ["python", "run.py"]
