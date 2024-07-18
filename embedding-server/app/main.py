from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel
from load_transformers import load_transformers

transformers = load_transformers()

app = FastAPI()

class EmbeddingRequest(BaseModel):
  input: str
  model: str

@app.get("/models")
async def models():
    models = []

    for model in transformers.keys():
        models.append({
            "id": model,
            "object": "model"
        })

    return {
        "data": models,
        "object": "list"
    }

@app.post("/embeddings")
async def embedding(req: EmbeddingRequest, res: Response):
    if not req.model in transformers:
        raise HTTPException(status_code=400, detail="unknown model: " + req.model)

    embeddings = transformers[req.model].encode([req.input])

    data = []

    for embedding in embeddings.tolist():
        data.append({
            "object": "embedding",
            "embedding": embedding,
            "index": len(data)
        })

    return {
        "data": data,
        "model": req.model,
        "object": "list"
    }
