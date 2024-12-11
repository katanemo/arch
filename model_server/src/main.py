import os
import time

from src.commons.globals import handler_map
from src.core.model_utils import ChatMessage, GuardRequest

from fastapi import FastAPI, Response
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource


resource = Resource.create(
    {
        "service.name": "model-server",
    }
)

# Initialize the tracer provider
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)


app = FastAPI()

FastAPIInstrumentor().instrument_app(app)

# DEFAULT_OTLP_HOST = "http://localhost:4317"
DEFAULT_OTLP_HOST = "none"

# Configure the OTLP exporter (Jaeger, Zipkin, etc.)
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTLP_HOST", DEFAULT_OTLP_HOST)  # noqa: F821
)

trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(otlp_exporter))


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/models")
async def models():
    return {
        "object": "list",
        "data": [{"id": model_name, "object": "model"} for model_name in handler_map],
    }


@app.post("/function_calling")
async def function_calling(req: ChatMessage, res: Response):
    try:
        intent_start_time = time.perf_counter()
        intent_response = await handler_map["Arch-Intent"].chat_completion(req)
        intent_latency = time.perf_counter() - intent_start_time

        if handler_map["Arch-Intent"].detect_intent(intent_response):
            # [TODO] measure agreement between intent detection and function calling
            try:
                function_start_time = time.perf_counter()
                function_calling_response = await handler_map[
                    "Arch-Function"
                ].chat_completion(req)
                function_latency = time.perf_counter() - function_start_time
                function_calling_response.metadata = {
                    "intent_latency": str(round(intent_latency * 1000, 3)),
                    "function_latency": str(round(function_latency * 1000, 3)),
                }

                return function_calling_response
            except Exception as e:
                # [TODO] Review: update how to collect debugging outputs
                # logger.error(f"Error in chat_completion from `Arch-Function`: {e}")
                res.status_code = 500
                return {"error": f"[Arch-Function] - {e}"}
        # [TODO] Review: define the behavior if `Arch-Intent` doesn't detect an intent
        else:
            return {
                "result": "No intent matched",
                "intent_latency": round(intent_latency * 1000, 3),
            }

    except Exception as e:
        # [TODO] Review: update how to collect debugging outputs
        # logger.error(f"Error in chat_completion from `Arch-Intent`: {e}")
        res.status_code = 500
        return {"error": f"[Arch-Intent] - {e}"}


@app.post("/guardrails")
async def guardrails(req: GuardRequest, res: Response, max_num_words=300):
    try:
        guard_start_time = time.perf_counter()
        guard_result = handler_map["Arch-Guard"].predict(req)
        guard_latency = time.perf_counter() - guard_start_time
        return {
            "response": guard_result,
            "guard_latency": round(guard_latency * 1000, 3),
        }
    except Exception as e:
        # [TODO] Review: update how to collect debugging outputs
        res.status_code = 500
        return {"error": f"[Arch-Guard] - {e}"}
