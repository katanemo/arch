import random
from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel
from load_models import (
    load_ner_models,
    load_transformers,
    load_toxic_model,
    load_jailbreak_model,
    load_zero_shot_models,
)
from utils import is_intel_cpu, GuardHandler, split_text_into_chunks
import json
import string
import torch
import yaml
from datetime import datetime, date, timedelta, timezone
import string
import pandas as pd
from load_models import load_sql
import logging
from dateparser import parse
from network_data_generator import convert_to_ago_format, load_params

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

transformers = load_transformers()
ner_models = load_ner_models()
zero_shot_models = load_zero_shot_models()

with open('/root/bolt_config.yaml', 'r') as file:
    config = yaml.safe_load(file)
if is_intel_cpu():
    cpu = "cpu"
with open("guard_model_config.json") as f:
    guard_model_config = json.load(f)

if 'prompt_guards' in config.keys():
    if len(config['prompt_guards']['input_guards']) == 2:
        task = 'both'
        jailbreak_hardware = [item for item in config['model_host_preferences'] if item['name'] == 'jailbreak'][0]['host_preference'][0]
        toxic_hardware = [item for item in config['model_host_preferences'] if item['name'] == 'toxic'][0]['host_preference'][0]
        if jailbreak_hardware == 'cpu' or torch.cuda.is_available() == False:
            jailbreak_hardware = cpu
        if toxic_hardware == 'cpu' or torch.cuda.is_available() == False:
            toxic_hardware = cpu


        toxic_model = load_toxic_model(
            guard_model_config["toxic"][jailbreak_hardware], toxic_hardware
        )
        jailbreak_model = load_jailbreak_model(
            guard_model_config["jailbreak"][toxic_hardware], jailbreak_hardware
        )

    else:
        task = list(config['prompt_guards']['input_guards'].keys())[0]

        hardware = [item for item in config['model_host_preferences'] if item['name'] == task][0]['host_preference'][0]
        if hardware == 'cpu' or torch.cuda.is_available() == False:
            hardware = cpu
        if task == 'toxic':
            toxic_model = load_toxic_model(
                guard_model_config["toxic"][hardware], hardware
            )
            jailbreak_model = None
        elif task == 'jailbreak':
            jailbreak_model = load_jailbreak_model(
                guard_model_config["jailbreak"][hardware], hardware
            )
            toxic_model = None
    

guard_handler = GuardHandler(toxic_model, jailbreak_model)

app = FastAPI()


class EmbeddingRequest(BaseModel):
    input: str
    model: str


@app.get("/healthz")
async def healthz():
    import os

    print(os.getcwd())
    return {"status": "ok"}


@app.get("/models")
async def models():
    models = []

    for model in transformers.keys():
        models.append({"id": model, "object": "model"})

    return {"data": models, "object": "list"}


@app.post("/embeddings")
async def embedding(req: EmbeddingRequest, res: Response):
    if req.model not in transformers:
        raise HTTPException(status_code=400, detail="unknown model: " + req.model)

    embeddings = transformers[req.model].encode([req.input])

    data = []

    for embedding in embeddings.tolist():
        data.append({"object": "embedding", "embedding": embedding, "index": len(data)})

    usage = {
        "prompt_tokens": 0,
        "total_tokens": 0,
    }
    return {"data": data, "model": req.model, "object": "list", "usage": usage}


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


class GuardRequest(BaseModel):
    input: str
    task: str


@app.post("/guard")
async def guard(req: GuardRequest, res: Response):
    """
    Guard API, take input as text and return the prediction of toxic and jailbreak
    result format: dictionary
            "toxic_prob": toxic_prob,
            "jailbreak_prob": jailbreak_prob,
            "time": end - start,
            "toxic_verdict": toxic_verdict,
            "jailbreak_verdict": jailbreak_verdict,
    """
    max_words = 300
    if req.task in ['both', 'toxic', 'jailbreak']:
        guard_handler.task = req.task
    if len(req.input.split()) < max_words:
        final_result = guard_handler.guard_predict(req.input)
    else:
        # text is long, split into chunks
        chunks = split_text_into_chunks(req.input)
        final_result = {
            "toxic_prob": [],
            "jailbreak_prob": [],
            "time": 0,
            "toxic_verdict": False,
            "jailbreak_verdict": False,
            "toxic_sentence": [],
            "jailbreak_sentence": [],
        }
        if guard_handler.task == "both":

            for chunk in chunks:
                result_chunk = guard_handler.guard_predict(chunk)
                final_result["time"] += result_chunk["time"]
                if result_chunk["toxic_verdict"]:
                    final_result["toxic_verdict"] = True
                    final_result["toxic_sentence"].append(
                        result_chunk["toxic_sentence"]
                    )
                    final_result["toxic_prob"].append(result_chunk["toxic_prob"].item())
                if result_chunk["jailbreak_verdict"]:
                    final_result["jailbreak_verdict"] = True
                    final_result["jailbreak_sentence"].append(
                        result_chunk["jailbreak_sentence"]
                    )
                    final_result["jailbreak_prob"].append(
                        result_chunk["jailbreak_prob"]
                    )
        else:
            task = guard_handler.task
            for chunk in chunks:
                result_chunk = guard_handler.guard_predict(chunk)
                final_result["time"] += result_chunk["time"]
                if result_chunk[f"{task}_verdict"]:
                    final_result[f"{task}_verdict"] = True
                    final_result[f"{task}_sentence"].append(
                        result_chunk[f"{task}_sentence"]
                    )
                    final_result[f"{task}_prob"].append(
                        result_chunk[f"{task}_prob"].item()
                    )
    return final_result


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
    predicted_classes = classifier(
        req.input, candidate_labels=labels_without_punctuations, multi_label=True
    )
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
        min_temp = random.randrange(50, 90)
        max_temp = random.randrange(min_temp + 5, min_temp + 20)
        weather_forecast["temperature"].append(
            {
                "date": str(date.today() + timedelta(days=i)),
                "temperature": {"min": min_temp, "max": max_temp},
            }
        )

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

class PacketDropCorrelationRequest(BaseModel):
    from_time: str = None  # Optional natural language timeframe
    ifname: str = None     # Optional interface name filter
    region: str = None     # Optional region filter
    min_in_errors: int = None
    max_in_errors: int = None
    min_out_errors: int = None
    max_out_errors: int = None
    min_in_discards: int = None
    max_in_discards: int = None
    min_out_discards: int = None
    max_out_discards: int = None


@app.post("/interface_down_pkt_drop")
async def interface_down_packet_drop(req: PacketDropCorrelationRequest, res: Response):

    params, filters = load_params(req)

    # Join the filters using AND
    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "AND " + where_clause

    # Step 3: Query packet errors and flows from interfacestats and ts_flow
    query = f"""
    SELECT
      d.switchip AS device_ip_address,
      i.in_errors,
      i.in_discards,
      i.out_errors,
      i.out_discards,
      i.ifname,
      t.src_addr,
      t.dst_addr,
      t.time AS flow_time,
      i.time AS interface_time
    FROM
      device d
    INNER JOIN
      interfacestats i
      ON d.device_mac_address = i.device_mac_address
    INNER JOIN
      ts_flow t
      ON d.switchip = t.sampler_address
    WHERE
      i.time >= :from_time  -- Using the converted timestamp
      {where_clause}
    ORDER BY
      i.time;
    """

    correlated_data = pd.read_sql_query(query, conn, params=params)

    if correlated_data.empty:
        default_response = {
            "device_ip_address": "0.0.0.0",  # Placeholder IP
            "in_errors": 0,
            "in_discards": 0,
            "out_errors": 0,
            "out_discards": 0,
            "ifname": req.ifname or "unknown",  # Placeholder or interface provided in the request
            "src_addr": "0.0.0.0",  # Placeholder source IP
            "dst_addr": "0.0.0.0",  # Placeholder destination IP
            "flow_time": str(datetime.now(timezone.utc)),  # Current timestamp or placeholder
            "interface_time": str(datetime.now(timezone.utc))  # Current timestamp or placeholder
        }
        return [default_response]


    logger.info(f"Correlated Packet Drop Data: {correlated_data}")

    return correlated_data.to_dict(orient='records')
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


class FlowPacketErrorCorrelationRequest(BaseModel):
    from_time: str = None  # Optional natural language timeframe
    ifname: str = None     # Optional interface name filter
    region: str = None     # Optional region filter
    min_in_errors: int = None
    max_in_errors: int = None
    min_out_errors: int = None
    max_out_errors: int = None
    min_in_discards: int = None
    max_in_discards: int = None
    min_out_discards: int = None
    max_out_discards: int = None

@app.post("/packet_errors_impact_flow")
async def packet_errors_impact_flow(req: FlowPacketErrorCorrelationRequest, res: Response):

    params, filters = load_params(req)

    # Join the filters using AND
    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "AND " + where_clause

    # Step 3: Query the packet errors and flows, correlating by timestamps
    query = f"""
    SELECT
      d.switchip AS device_ip_address,
      i.in_errors,
      i.in_discards,
      i.out_errors,
      i.out_discards,
      i.ifname,
      t.src_addr,
      t.dst_addr,
      t.src_port,
      t.dst_port,
      t.packets,
      t.time AS flow_time,
      i.time AS error_time
    FROM
      device d
    INNER JOIN
      interfacestats i
      ON d.device_mac_address = i.device_mac_address
    INNER JOIN
      ts_flow t
      ON d.switchip = t.sampler_address
    WHERE
      i.time >= :from_time
      AND ABS(strftime('%s', t.time) - strftime('%s', i.time)) <= 300  -- Correlate within 5 minutes
      {where_clause}
    ORDER BY
      i.time;
    """

    correlated_data = pd.read_sql_query(query, conn, params=params)

    if correlated_data.empty:
        default_response = {
            "device_ip_address": "0.0.0.0",  # Placeholder IP
            "in_errors": 0,
            "in_discards": 0,
            "out_errors": 0,
            "out_discards": 0,
            "ifname": req.ifname or "unknown",  # Placeholder or interface provided in the request
            "src_addr": "0.0.0.0",  # Placeholder source IP
            "dst_addr": "0.0.0.0",  # Placeholder destination IP
            "src_port": 0,
            "dst_port": 0,
            "packets": 0,
            "flow_time": str(datetime.now(timezone.utc)),  # Current timestamp or placeholder
            "error_time": str(datetime.now(timezone.utc))  # Current timestamp or placeholder
        }
        return [default_response]

    # Return the correlated data if found
    return correlated_data.to_dict(orient='records')
