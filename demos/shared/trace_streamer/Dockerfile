FROM python:3.12-slim as arch

WORKDIR /app

RUN pip install requests
COPY stream_traces.py .

RUN mkdir -p /var/log
RUN touch /var/log/envoy.log

CMD ["python", "stream_traces.py"]
