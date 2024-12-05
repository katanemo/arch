import os

from app.commons.globals import handler_map
from app.model_handler.function_calling import ChatMessage
from app.model_handler.guardrails import GuardRequest

from fastapi import FastAPI, Response, Request
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
async def function_calling(req: ChatMessage, res: Response, request: Request):
    try:
        intent_result = await handler_map["Arch-Intent"].chat_completion(req)

        if intent_result.choices[0].message.content == "Yes":
            try:
                function_result = await handler_map["Arch-Function"].chat_completion(
                    req
                )
                return function_result
            except Exception as e:
                # [TODO]
                # logger.error(f"Error in chat_completion from `Arch-Function`: {e}")
                res.status_code = 500
                return {"error": f"[Arch-Function] - {e}"}

    except Exception as e:
        # [TODO]
        # logger.error(f"Error in chat_completion from `Arch-Intent`: {e}")
        res.status_code = 500
        return {"error": f"[Arch-Intent] - {e}"}


@app.post("/guardrails")
async def guardrails(req: GuardRequest, res: Response, max_num_words=300):
    try:
        guard_result = handler_map["Arch-Guard"].predict(req)
        return guard_result
    except Exception as e:
        # [TODO]
        res.status_code = 500
        return {"error": f"[Arch-Guard] - {e}"}
