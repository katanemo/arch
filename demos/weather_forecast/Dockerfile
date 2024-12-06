# took inspiration from https://medium.com/@albertazzir/blazing-fast-python-docker-builds-with-poetry-a78a66f5aed0

# The builder image, used to build the virtual environment
FROM python:3.12 as builder

RUN pip install poetry==1.8.3

ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=1 \
    POETRY_VIRTUALENVS_CREATE=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

WORKDIR /code

COPY pyproject.toml poetry.lock ./
RUN touch README.md

RUN poetry install --no-root && rm -rf $POETRY_CACHE_DIR

# The runtime image, used to just run the code provided its virtual environment
FROM python:3.12-slim as runtime

RUN apt-get update && apt-get install -y curl

WORKDIR /code

ENV VIRTUAL_ENV=/code/.venv \
    PATH="/code/.venv/bin:$PATH"

COPY --from=builder ${VIRTUAL_ENV} ${VIRTUAL_ENV}

COPY main.py ./

HEALTHCHECK \
    --interval=5s \
    --timeout=1s \
    --start-period=1s \
    --retries=3 \
    CMD curl http://localhost:80/healthz

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80", "--log-level", "debug"]
