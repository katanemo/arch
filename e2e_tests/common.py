import os


PROMPT_GATEWAY_ENDPOINT = os.getenv(
    "PROMPT_GATEWAY_ENDPOINT", "http://localhost:10000/v1/chat/completions"
)
LLM_GATEWAY_ENDPOINT = os.getenv(
    "LLM_GATEWAY_ENDPOINT", "http://localhost:12000/v1/chat/completions"
)


def get_data_chunks(stream, n=1):
    chunks = []
    for chunk in stream.iter_lines():
        if chunk:
            chunk = chunk.decode("utf-8")
            chunk_data_id = chunk[0:6]
            assert chunk_data_id == "data: "
            chunk_data = chunk[6:]
            chunk_data = chunk_data.strip()
            # chunk_data = chunk_data.replace("null", "None")
            chunks.append(chunk_data)
            if len(chunks) >= n:
                break
    return chunks
