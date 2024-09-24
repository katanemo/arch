import random
from fastapi import FastAPI, Response, HTTPException
from pydantic import BaseModel
from load_models import (
    load_ner_models,
    load_transformers,
    load_guard_model,
    load_zero_shot_models,
)
from utils import GuardHandler, split_text_into_chunks
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
from typing import List

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

transformers = load_transformers()
ner_models = load_ner_models()
zero_shot_models = load_zero_shot_models()

with open("/root/bolt_config.yaml", "r") as file:
    config = yaml.safe_load(file)
with open("guard_model_config.json") as f:
    guard_model_config = json.load(f)

if "prompt_guards" in config.keys():
    if len(config["prompt_guards"]["input_guards"]) == 2:
        task = "both"
        jailbreak_hardware = "gpu" if torch.cuda.is_available() else "cpu"
        toxic_hardware = "gpu" if torch.cuda.is_available() else "cpu"
        toxic_model = load_guard_model(
            guard_model_config["toxic"][jailbreak_hardware], toxic_hardware
        )
        jailbreak_model = load_guard_model(
            guard_model_config["jailbreak"][toxic_hardware], jailbreak_hardware
        )

    else:
        task = list(config["prompt_guards"]["input_guards"].keys())[0]

        hardware = "gpu" if torch.cuda.is_available() else "cpu"
        if task == "toxic":
            toxic_model = load_guard_model(
                guard_model_config["toxic"][hardware], hardware
            )
            jailbreak_model = None
        elif task == "jailbreak":
            jailbreak_model = load_guard_model(
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
    if req.task in ["both", "toxic", "jailbreak"]:
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


'''
*****
Adding new functions to test the usecases - Sampreeth
*****
"""

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
    logger.info(
        f"{'* ' * 50}\n\nCaptured Ranking Criteria: {req.ranking_criteria}\n\n{'* ' * 50}"
    )

    if req.ranking_criteria == "yoe":
        req.ranking_criteria = "years_of_experience"
    elif req.ranking_criteria == "rating":
        req.ranking_criteria = "performance_score"

    logger.info(
        f"{'* ' * 50}\n\nFinal Ranking Criteria: {req.ranking_criteria}\n\n{'* ' * 50}"
    )

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
    result = result_df.to_dict(orient="records")
    return result


class AggregateStats(BaseModel):
    grouping: str
    aggregate_criteria: str
    aggregate_type: str


@app.post("/aggregate_stats")
async def aggregate_stats(req: AggregateStats, res: Response):
    logger.info(
        f"{'* ' * 50}\n\nCaptured Aggregate Criteria: {req.aggregate_criteria}\n\n{'* ' * 50}"
    )

    if req.aggregate_criteria == "yoe":
        req.aggregate_criteria = "years_of_experience"

    logger.info(
        f"{'* ' * 50}\n\nFinal Aggregate Criteria: {req.aggregate_criteria}\n\n{'* ' * 50}"
    )

    logger.info(
        f"{'* ' * 50}\n\nCaptured Aggregate Type: {req.aggregate_type}\n\n{'* ' * 50}"
    )
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

    logger.info(
        f"{'* ' * 50}\n\nFinal Aggregate Type: {req.aggregate_type}\n\n{'* ' * 50}"
    )

    query = f"""
    SELECT {req.grouping}, {req.aggregate_type}({req.aggregate_criteria}) as {req.aggregate_type}_{req.aggregate_criteria}
    FROM employees
    GROUP BY {req.grouping};
    """
    result_df = pd.read_sql_query(query, conn)
    result = result_df.to_dict(orient="records")
    return result


class PacketDropCorrelationRequest(BaseModel):
    from_time: str = None  # Optional natural language timeframe
    ifname: str = None  # Optional interface name filter
    region: str = None  # Optional region filter
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
            "ifname": req.ifname
            or "unknown",  # Placeholder or interface provided in the request
            "src_addr": "0.0.0.0",  # Placeholder source IP
            "dst_addr": "0.0.0.0",  # Placeholder destination IP
            "flow_time": str(
                datetime.now(timezone.utc)
            ),  # Current timestamp or placeholder
            "interface_time": str(
                datetime.now(timezone.utc)
            ),  # Current timestamp or placeholder
        }
        return [default_response]

    logger.info(f"Correlated Packet Drop Data: {correlated_data}")

    return correlated_data.to_dict(orient='records')


class FlowPacketErrorCorrelationRequest(BaseModel):
    from_time: str = None  # Optional natural language timeframe
    ifname: str = None  # Optional interface name filter
    region: str = None  # Optional region filter
    min_in_errors: int = None
    max_in_errors: int = None
    min_out_errors: int = None
    max_out_errors: int = None
    min_in_discards: int = None
    max_in_discards: int = None
    min_out_discards: int = None
    max_out_discards: int = None


@app.post("/packet_errors_impact_flow")
async def packet_errors_impact_flow(
    req: FlowPacketErrorCorrelationRequest, res: Response
):
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
            "ifname": req.ifname
            or "unknown",  # Placeholder or interface provided in the request
            "src_addr": "0.0.0.0",  # Placeholder source IP
            "dst_addr": "0.0.0.0",  # Placeholder destination IP
            "src_port": 0,
            "dst_port": 0,
            "packets": 0,
            "flow_time": str(
                datetime.now(timezone.utc)
            ),  # Current timestamp or placeholder
            "error_time": str(
                datetime.now(timezone.utc)
            ),  # Current timestamp or placeholder
        }
        return [default_response]

    # Return the correlated data if found
    return correlated_data.to_dict(orient='records')

# 1. Top Employees by Performance, Projects, and Timeframe
class TopEmployeesProjects(BaseModel):
    min_performance_score: float
    min_years_experience: int
    department: str
    min_project_count: int = None  # Optional
    months_range: int = None  # Optional (for filtering recent projects)


@app.post("/top_employees_projects")
async def employees_projects(req: TopEmployeesProjects, res: Response):
    params, filters = {}, []

    # Add optional months_range filter
    if req.months_range:
        params['months_range'] = req.months_range
        filters.append(f"p.start_date >= DATE('now', '-{req.months_range} months')")

    # Add project count filter if provided
    if req.min_project_count:
        filters.append(f"COUNT(p.project_id) >= {req.min_project_count}")

    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "AND " + where_clause

    query = f"""
    SELECT e.name, e.department, e.years_of_experience, e.performance_score, COUNT(p.project_id) as project_count
    FROM employees e
    LEFT JOIN projects p ON e.eid = p.eid
    WHERE e.performance_score >= {req.min_performance_score}
      AND e.years_of_experience >= {req.min_years_experience}
      AND e.department = '{req.department}'
      {where_clause}
    GROUP BY e.eid, e.name, e.department, e.years_of_experience, e.performance_score
    ORDER BY e.performance_score DESC;
    """

    result_df = pd.read_sql_query(query, conn, params=params)
    return result_df.to_dict(orient='records')


# 2. Employees with Salary Growth Since Last Promotion
class SalaryGrowthRequest(BaseModel):
    min_salary_increase_percentage: float
    department: str = None  # Optional


@app.post("/salary_growth")
async def salary_growth(req: SalaryGrowthRequest, res: Response):
    params, filters = {}, []

    if req.department:
        filters.append("e.department = :department")
        params['department'] = req.department

    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "AND " + where_clause

    query = f"""
    SELECT e.name, e.department, s.salary_increase_percentage
    FROM employees e
    JOIN salary_history s ON e.eid = s.eid
    WHERE s.salary_increase_percentage >= {req.min_salary_increase_percentage}
      AND s.promotion_date IS NOT NULL
      {where_clause}
    ORDER BY s.salary_increase_percentage DESC;
    """

    result_df = pd.read_sql_query(query, conn, params=params)
    return result_df.to_dict(orient='records')


# 4. Employees with Promotions and Salary Increases
class PromotionsIncreasesRequest(BaseModel):
    year: int
    min_salary_increase_percentage: float = None  # Optional
    department: str = None  # Optional


@app.post("/promotions_increases")
async def promotions_increases(req: PromotionsIncreasesRequest, res: Response):
    params, filters = {}, []

    if req.min_salary_increase_percentage:
        filters.append(f"s.salary_increase_percentage >= {req.min_salary_increase_percentage}")

    if req.department:
        filters.append("e.department = :department")
        params['department'] = req.department

    where_clause = " AND ".join(filters)
    if where_clause:
        where_clause = "AND " + where_clause

    query = f"""
    SELECT e.name, e.department, s.salary_increase_percentage, s.promotion_date
    FROM employees e
    JOIN salary_history s ON e.eid = s.eid
    WHERE strftime('%Y', s.promotion_date) = '{req.year}'
      {where_clause}
    ORDER BY s.salary_increase_percentage DESC;
    """

    result_df = pd.read_sql_query(query, conn, params=params)
    return result_df.to_dict(orient='records')


# 5. Employees with Highest Average Project Performance
class AvgProjPerformanceRequest(BaseModel):
    min_project_count: int
    min_performance_score: float
    department: str = None  # Optional


@app.post("/avg_project_performance")
async def avg_project_performance(req: AvgProjPerformanceRequest, res: Response):
    params, filters = {}, []

    if req.department:
        filters.append("e.department = :department")
        params['department'] = req.department

    filters.append(f"p.performance_score >= {req.min_performance_score}")

    where_clause = " AND ".join(filters)

    query = f"""
    SELECT e.name, e.department, AVG(p.performance_score) as avg_performance_score, COUNT(p.project_id) as project_count
    FROM employees e
    JOIN projects p ON e.eid = p.eid
    WHERE {where_clause}
    GROUP BY e.eid, e.name, e.department
    HAVING COUNT(p.project_id) >= {req.min_project_count}
    ORDER BY avg_performance_score DESC;
    """

    result_df = pd.read_sql_query(query, conn, params=params)
    return result_df.to_dict(orient='records')


# 6. Employees by Certification and Years of Experience
class CertificationsExperienceRequest(BaseModel):
    certifications: List[str]
    min_years_experience: int
    department: str = None  # Optional

@app.post("/employees_certifications_experience")
async def certifications_experience(req: CertificationsExperienceRequest, res: Response):
    # Convert the list of certifications into a format for SQL query
    certs_filter = ', '.join([f"'{cert}'" for cert in req.certifications])

    params, filters = {}, []

    # Add department filter if provided
    if req.department:
        filters.append("e.department = :department")
        params['department'] = req.department

    filters.append("e.years_of_experience >= :min_years_experience")
    params['min_years_experience'] = req.min_years_experience

    where_clause = " AND ".join(filters)

    query = f"""
    SELECT e.name, e.department, e.years_of_experience, COUNT(c.certification_name) as cert_count
    FROM employees e
    JOIN certifications c ON e.eid = c.eid
    WHERE c.certification_name IN ({certs_filter})
      AND {where_clause}
    GROUP BY e.eid, e.name, e.department, e.years_of_experience
    HAVING COUNT(c.certification_name) = {len(req.certifications)}
    ORDER BY e.years_of_experience DESC;
    """

    result_df = pd.read_sql_query(query, conn, params=params)
    return result_df.to_dict(orient='records')
'''
