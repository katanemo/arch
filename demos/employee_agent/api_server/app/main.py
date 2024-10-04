from typing import List, Tuple, Dict
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
    SELECT e.name, e.department, e.years_of_experience, e.performance_score, COUNT(pp.project_name) as project_count
    FROM employees e
    LEFT JOIN project_performance pp ON e.eid = pp.eid
    WHERE e.performance_score >= {req.min_performance_score}
      AND e.years_of_experience >= {req.min_years_experience}
      AND e.department = '{req.department}'
    GROUP BY e.name, e.department, e.years_of_experience, e.performance_score
    """

    # Add HAVING clause for project count, if provided
    having_clause = ""
    if req.min_project_count:
        having_clause = f"HAVING COUNT(pp.project_name) >= {req.min_project_count}"

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

class MentorshipImpactRequest(BaseModel):
    mentor_id: int
    performance_range: Tuple[int, int]
    departments: List[str]
    min_projects: int = 2
    productivity_metrics: Dict[str, float]

@app.post("/mentorship_impact")
async def mentorship_impact(req: MentorshipImpactRequest, res: Response):
    try:
        logger.info(f"{'=' * 50}\n\n Request: {req.dict()} \n\n{'=' * 50}")
        filters = [f"m.mentor_id = {req.mentor_id}"]
        # Unpack performance range
        if len(req.performance_range) == 1:
            performance_min = req.performance_range[0]
            filters.append(f"mp.mentee_performance_improvement > {performance_min}")
        elif len(req.performance_range) == 2:
            performance_min, performance_max = req.performance_range
            filters.append(f"mp.mentee_performance_improvement BETWEEN {performance_min} AND {performance_max}")

        departments_filter = None
        if req.departments:
            departments_filter = "', '".join(req.departments) if req.departments else None

        default_weights = {
            'tasks_completed': 0.5,
            'meeting_attendance': 0.2,
            'peer_feedback': 0.3
        }
        combined_weights = {**default_weights, **req.productivity_metrics}
        # Dynamically calculate the weighted productivity score
        weighted_score_expr = " + ".join([f"{weight} * p.{metric}" for metric, weight in combined_weights.items()])

        if departments_filter:
            filters.append(f"e.department IN ('{departments_filter}')")
        filters.append(f"mp.projects_participated >= {req.min_projects}")
        where_clause = " AND ".join(filters)

        query = f"""
        SELECT m.mentor_id, mp.mentee_id, e.name  as mentee_name, e.department as mentee_dept, mp.mentee_performance_improvement, mp.projects_participated,
            ({weighted_score_expr}) as productivity_score
        FROM employees e
        JOIN mentorship m ON e.eid = m.mentee_id
        JOIN mentee_performance mp ON mp.mentee_id = m.mentee_id
        JOIN productivity p ON p.eid = mp.mentee_id
        WHERE {where_clause}
        ORDER BY productivity_score DESC;
        """
        logger.info(f"{'*' * 50}\n\n Query: {query} \n\n{'*' * 50}")

        result_df = pd.read_sql_query(query, conn)
        return (result_df.to_dict(orient='records') if not result_df.empty else {"result": "No results found for the combination of inputs. Try another combination."})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e) + " Something wrong in the function implementation.")

class ProjectSuccessPredictorsRequest(BaseModel):
    project_name: str
    scope: str  # Options: "small", "medium", "large"
    timeline: int
    resources_allocated: float
    past_performance: float = 0.75
    productivity_metrics: Dict[str, float]
    # = {'leadership': 0.4, 'communication': 0.3, 'problem_solving': 0.3}

@app.post("/project_success_predictors")
async def project_success_predictors(req: ProjectSuccessPredictorsRequest, res: Response):
    try:
        logger.info(f"{'*' * 50}\n\n Request: {req.dict()} \n\n{'*' * 50}")
        default_weights = {
            'leadership': 0.4,
            'communication': 0.3,
            'problem_solving': 0.3
        }

        # Merge user-provided metrics with default ones, preferring user input
        combined_weights = {**default_weights, **req.productivity_metrics}

        # Dynamically calculate the weighted productivity score
        weighted_score_expr = " + ".join([f"{weight} * pd.{metric}" for metric, weight in combined_weights.items()])

        # Calculate success likelihood based on project characteristics and employee performance
        query = f"""
        SELECT pr.project_name, pr.scope, pr.timeline, pr.resources_allocated, pp.success_rate,
            ({weighted_score_expr}) as productivity_score,
            (pp.success_rate * {req.past_performance} * ({weighted_score_expr}) * 1000 / pr.resources_allocated) as success_likelihood
        FROM projects pr
        JOIN project_performance pp ON pp.project_name = pr.project_name
        JOIN productivity pd ON pd.eid = pp.eid
        WHERE pr.project_name = '{req.project_name}' AND pr.scope = '{req.scope}' AND pr.timeline <= {req.timeline}
        ORDER BY success_likelihood DESC LIMIT 10;
        """

        logger.info(f"{'*' * 50}\n\n Query: {query} \n\n{'*' * 50}")

        result_df = pd.read_sql_query(query, conn)

        logger.info(f"{'=' * 50}\n\n Result: {result_df.to_dict(orient='records')} \n\n{'=' * 50}")
        return result_df.to_dict(orient='records') if not result_df.empty else {"result": "No results found for the combination of inputs. Try another combination."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e) + " Something wrong in the function implementation.")

class RemoteWorkEfficiencyRequest(BaseModel):
    departments: List[str]
    track_hours: bool = True
    min_projects_completed: int = 3
    productivity_metrics: Dict[str, float]

@app.post("/remote_work_efficiency")
async def remote_work_efficiency(req: RemoteWorkEfficiencyRequest, res: Response):
    try:
        default_weights = {
            'tasks_completed': 0.5,
            'meeting_attendance': 0.2,
            'peer_feedback': 0.3
        }
        combined_weights = {**default_weights, **req.productivity_metrics}
        # Dynamically calculate the weighted productivity score
        weighted_score_expr = " + ".join([f"{weight} * p.{metric}" for metric, weight in combined_weights.items()])

        # Build filters for departments and project completion
        departments_filter = "', '".join(req.departments)
        filters = [f"e.department IN ('{departments_filter}')"]
        filters.append(f"rw.projects_completed >= {req.min_projects_completed}")

        # Optionally track hours worked
        if req.track_hours:
            filters.append("rw.hours_worked IS NOT NULL")

        where_clause = " AND ".join(filters)

        query = f"""
        SELECT e.name, e.department, rw.hours_worked, rw.projects_completed,
            ({weighted_score_expr}) as productivity_score,
            (rw.projects_completed * ({weighted_score_expr})) as efficiency_score
        FROM employees e
        JOIN remote_work rw ON e.eid = rw.eid
        JOIN productivity p ON p.eid = rw.eid
        WHERE {where_clause}
        ORDER BY efficiency_score DESC;
        """

        result_df = pd.read_sql_query(query, conn)
        return result_df.to_dict(orient='records') if not result_df.empty else {"result": "No results found for the combination of inputs. Try another combination."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e) + " Something wrong in the function implementation.")
