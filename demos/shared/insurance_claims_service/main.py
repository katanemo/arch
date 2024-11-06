import json
import os
import random
from fastapi import FastAPI, Response
from datetime import datetime, date, timedelta, timezone
import logging
from pydantic import BaseModel
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource


resource = Resource.create(
    {
        "service.name": "insurance-claims-service",
    }
)

# Initialize the tracer provider
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)

logger = logging.getLogger("uvicorn.error")
logger.setLevel(logging.INFO)

app = FastAPI()
FastAPIInstrumentor().instrument_app(app)

# Configure the OTLP exporter (Jaeger, Zipkin, etc.)
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OLTP_HOST", "http://localhost:4317")
)
trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


class InsuranceClaimDetailsRequest(BaseModel):
    policy_number: str


@app.post("/insurance_claim_details")
async def insurance_claim_details(req: InsuranceClaimDetailsRequest, res: Response):
    claim_details = {
        "policy_number": req.policy_number,
        "claim_status": "Approved",
        "claim_amount": random.randrange(1000, 10000),
        "claim_date": str(date.today() - timedelta(days=random.randrange(1, 30))),
        "claim_reason": "Car Accident",
    }

    return claim_details


class DefaultTargetRequest(BaseModel):
    messages: list


@app.post("/default_target")
async def default_target(req: DefaultTargetRequest, res: Response):
    logger.info(f"Received messages: {req.messages}")
    resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "I can help you with insurance claim details",
                },
                "finish_reason": "completed",
                "index": 0,
            }
        ],
        "model": "api_server",
        "usage": {"completion_tokens": 0},
    }
    logger.info(f"sending response: {json.dumps(resp)}")
    return resp
