from typing import List
from fastapi import FastAPI, HTTPException, Response
import logging
from pydantic import BaseModel
from utils import load_sql
import pandas as pd


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/healthz")
async def healthz():
    return {
        "status": "ok"
    }

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

# 1. Top Employees by Performance, Projects, and Timeframe
class TopEmployeesProjects(BaseModel):
    min_performance_score: float
    min_years_experience: int
    department: str
    min_project_count: int = None  # Optional
    months_range: int = None  # Optional (for filtering recent projects)


@app.post("/employees_projects")
async def employees_projects(req: TopEmployeesProjects, res: Response):
    params, filters = {}, []

    # Add optional months_range filter
    if req.months_range:
        params['months_range'] = req.months_range
        filters.append(f"p.start_date >= DATE('now', '-{req.months_range} months')")

    # Prepare the base query
    query = f"""
    SELECT e.name, e.department, e.years_of_experience, e.performance_score, COUNT(p.project_name) as project_count
    FROM employees e
    LEFT JOIN projects p ON e.eid = p.eid
    WHERE e.performance_score >= {req.min_performance_score}
      AND e.years_of_experience >= {req.min_years_experience}
      AND e.department = '{req.department}'
    GROUP BY e.name, e.department, e.years_of_experience, e.performance_score
    """

    # Add HAVING clause for project count, if provided
    having_clause = ""
    if req.min_project_count:
        having_clause = f"HAVING COUNT(p.project_name) >= {req.min_project_count}"

    # Add ORDER BY clause
    order_by_clause = "ORDER BY e.performance_score DESC"

    # Combine all parts of the query
    query = f"{query} {having_clause} {order_by_clause};"

    # Execute the query and return the result
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

    filters.append("s.salary_increase_percentage >= :min_salary_increase_percentage")
    params['min_salary_increase_percentage'] = req.min_salary_increase_percentage

    where_clause = " AND ".join(filters)

    query = f"""
    SELECT e.name, e.department, s.salary_increase_percentage
    FROM employees e
    JOIN salary_history s ON e.eid = s.eid
    WHERE s.promotion_date IS NOT NULL
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

    params['year'] = str(req.year)

    if req.min_salary_increase_percentage:
        filters.append(f"s.salary_increase_percentage >= :min_salary_increase_percentage")
        params['min_salary_increase_percentage'] = req.min_salary_increase_percentage

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
    WHERE strftime('%Y', s.promotion_date) = :year
      {where_clause}
    ORDER BY s.salary_increase_percentage DESC;
    """

    result_df = pd.read_sql_query(query, conn, params=params)
    return result_df.to_dict(orient='records')


# 6. Employees by Certification and Years of Experience
class CertificationsExperienceRequest(BaseModel):
    certifications: List[str]
    min_years_experience: int
    department: str = None  # Optional

@app.post("/certifications_experience")
async def certifications_experience(req: CertificationsExperienceRequest, res: Response):
    params, filters = {}, []

    if req.department:
        filters.append("e.department = :department")
        params['department'] = req.department

    filters.append("e.years_of_experience >= :min_years_experience")
    params['min_years_experience'] = req.min_years_experience

    where_clause = " AND ".join(filters)

    # Build the placeholders for the certifications list
    certs_placeholders = ", ".join([f":cert_{i}" for i in range(len(req.certifications))])
    for i, cert in enumerate(req.certifications):
        params[f"cert_{i}"] = cert

    query = f"""
    SELECT e.name, e.department, e.years_of_experience, COUNT(c.certification_name) as cert_count
    FROM employees e
    JOIN certifications c ON e.eid = c.eid
    WHERE c.certification_name IN ({certs_placeholders})
      AND {where_clause}
    GROUP BY e.eid, e.name, e.department, e.years_of_experience
    HAVING COUNT(c.certification_name) = {len(req.certifications)}
    ORDER BY e.years_of_experience DESC;
    """

    result_df = pd.read_sql_query(query, conn, params=params)
    return result_df.to_dict(orient='records')
