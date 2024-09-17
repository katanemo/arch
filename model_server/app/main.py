import random
from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel
from load_models import load_ner_models, load_transformers, load_zero_shot_models
from datetime import date, timedelta
import string
import pandas as pd
from load_models import load_sql
import logging


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

transformers = load_transformers()
ner_models = load_ner_models()
zero_shot_models = load_zero_shot_models()

app = FastAPI()

class EmbeddingRequest(BaseModel):
  input: str
  model: str

@app.get("/healthz")
async def healthz():
    return {
        "status": "ok"
    }

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
    if req.model not in transformers:
        raise HTTPException(status_code=400, detail="unknown model: " + req.model)

    embeddings = transformers[req.model].encode([req.input])

    data = []

    for embedding in embeddings.tolist():
        data.append({
            "object": "embedding",
            "embedding": embedding,
            "index": len(data)
        })

    usage = {
        "prompt_tokens": 0,
        "total_tokens": 0,
    }
    return {
        "data": data,
        "model": req.model,
        "object": "list",
        "usage": usage
    }

class NERRequest(BaseModel):
  input: str
  labels: list[str]
  model: str


@app.post("/ner")
async def ner(req: NERRequest, res: Response):
    if req.model not in ner_models:
        raise HTTPException(status_code=400, detail="unknown model: " + req.model)

    model = ner_models[req.model]
    entities = model.predict_entities(req.input, req.labels)

    return {
        "data": entities,
        "model": req.model,
        "object": "list",
    }

class ZeroShotRequest(BaseModel):
  input: str
  labels: list[str]
  model: str


def remove_punctuations(s, lower=True):
    s = s.translate(str.maketrans(string.punctuation, " " * len(string.punctuation)))
    s = " ".join(s.split())
    if lower:
        s = s.lower()
    return s


@app.post("/zeroshot")
async def zeroshot(req: ZeroShotRequest, res: Response):
    if req.model not in zero_shot_models:
        raise HTTPException(status_code=400, detail="unknown model: " + req.model)

    classifier = zero_shot_models[req.model]
    labels_without_punctuations = [remove_punctuations(label) for label in req.labels]
    predicted_classes = classifier(req.input, candidate_labels=labels_without_punctuations, multi_label=True)
    label_map = dict(zip(labels_without_punctuations, req.labels))

    orig_map = [label_map[label] for label in predicted_classes["labels"]]
    final_scores = dict(zip(orig_map, predicted_classes["scores"]))
    predicted_class = label_map[predicted_classes["labels"][0]]

    return {
        "predicted_class": predicted_class,
        "predicted_class_score": final_scores[predicted_class],
        "scores": final_scores,
        "model": req.model,
    }


class WeatherRequest(BaseModel):
  city: str


@app.post("/weather")
async def weather(req: WeatherRequest, res: Response):

    weather_forecast = {
        "city": req.city,
        "temperature": [],
        "unit": "F",
    }
    for i in range(7):
       min_temp = random.randrange(50,90)
       max_temp = random.randrange(min_temp+5, min_temp+20)
       weather_forecast["temperature"].append({
           "date": str(date.today() + timedelta(days=i)),
           "temperature": {
              "min": min_temp,
              "max": max_temp
           }
       })

    return weather_forecast


'''
*****
Adding new functions to test the usecases - Sampreeth
*****
'''

conn = load_sql()
name_col = "name"

class TopEmployees(BaseModel):
    grouping: str
    ranking_criteria: str
    top_n: int


@app.post("/top_employees")
async def top_employees(req: TopEmployees, res: Response):
    name_col = "name"
    # Check if `req.ranking_criteria` is a Text object and extract its value accordingly
    logger.info(f"{'* ' * 50}\n\nCaptured Ranking Criteria: {req.ranking_criteria}\n\n{'* ' * 50}")

    if req.ranking_criteria == "yoe":
        req.ranking_criteria = "years_of_experience"
    elif req.ranking_criteria == "rating":
        req.ranking_criteria = "performance_score"
    
    logger.info(f"{'* ' * 50}\n\nFinal Ranking Criteria: {req.ranking_criteria}\n\n{'* ' * 50}")


    query = f"""
    SELECT {req.grouping}, {name_col}, {req.ranking_criteria}
    FROM (
        SELECT {req.grouping}, {name_col}, {req.ranking_criteria},
               DENSE_RANK() OVER (PARTITION BY {req.grouping} ORDER BY {req.ranking_criteria} DESC) as emp_rank
        FROM employees
    ) ranked_employees
    WHERE emp_rank <= {req.top_n};
    """
    result_df = pd.read_sql_query(query, conn)
    result = result_df.to_dict(orient='records')
    return result


class AggregateStats(BaseModel):
    grouping: str
    aggregate_criteria: str
    aggregate_type: str

@app.post("/aggregate_stats")
async def aggregate_stats(req: AggregateStats, res: Response):
    logger.info(f"{'* ' * 50}\n\nCaptured Aggregate Criteria: {req.aggregate_criteria}\n\n{'* ' * 50}")

    if req.aggregate_criteria == "yoe":
        req.aggregate_criteria = "years_of_experience"

    logger.info(f"{'* ' * 50}\n\nFinal Aggregate Criteria: {req.aggregate_criteria}\n\n{'* ' * 50}")

    logger.info(f"{'* ' * 50}\n\nCaptured Aggregate Type: {req.aggregate_type}\n\n{'* ' * 50}")
    if req.aggregate_type.lower() not in ["sum", "avg", "min", "max"]:
        if req.aggregate_type.lower() == "count":
            req.aggregate_type = "COUNT"
        elif req.aggregate_type.lower() == "total":
            req.aggregate_type = "SUM"
        elif req.aggregate_type.lower() == "average":
            req.aggregate_type = "AVG"
        elif req.aggregate_type.lower() == "minimum":
            req.aggregate_type = "MIN"
        elif req.aggregate_type.lower() == "maximum":
            req.aggregate_type = "MAX"
        else:
            raise HTTPException(status_code=400, detail="Invalid aggregate type")
    
    logger.info(f"{'* ' * 50}\n\nFinal Aggregate Type: {req.aggregate_type}\n\n{'* ' * 50}")

    query = f"""
    SELECT {req.grouping}, {req.aggregate_type}({req.aggregate_criteria}) as {req.aggregate_type}_{req.aggregate_criteria}
    FROM employees
    GROUP BY {req.grouping};
    """
    result_df = pd.read_sql_query(query, conn)
    result = result_df.to_dict(orient='records')
    return result