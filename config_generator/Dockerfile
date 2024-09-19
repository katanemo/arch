FROM python:3-slim as config-generator
WORKDIR /usr/src/app
COPY config_generator/requirements.txt .
RUN pip install -r requirements.txt
COPY config_generator/config_generator.py .
COPY envoyfilter/envoy.template.yaml .
COPY envoyfilter/katanemo-config.yaml .

CMD ["python", "config_generator.py"]
