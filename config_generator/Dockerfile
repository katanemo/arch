FROM python:3-slim as config-generator
WORKDIR /usr/src/app
RUN pip install jinja2
COPY config_generator/config_generator.py .
COPY envoyfilter/envoy.template.yaml .
COPY envoyfilter/katanemo-config.yaml .
# RUN python config_generator.py > envoy.yaml

CMD ["python", "config_generator.py"]
