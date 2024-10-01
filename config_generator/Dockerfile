FROM python:3-slim as config-generator
WORKDIR /usr/src/app
COPY config_generator/requirements.txt .
RUN pip install -r requirements.txt
COPY config_generator/config_generator.py .
COPY arch/envoy.template.yaml .
COPY config_generator/arch_config_schema.yaml .
CMD ["python", "config_generator.py"]
