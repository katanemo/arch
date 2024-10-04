import pandas as pd
import random
import datetime
import sqlite3
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

data_path = "/app/data"
def load_sql():
    # Example Usage
    conn = sqlite3.connect(":memory:")

    # create and load all tables

    generate_employee_data(conn)
    generate_projects(conn)
    generate_salary_history(conn)
    generate_certifications(conn)
    generate_mentorship(conn)
    generate_remote_work(conn)
    generate_productivity(conn)
    generate_project_performance(conn)
    generate_mentee_performance(conn)

    return conn

# Function to generate random employee data with `eid` as the primary key
def generate_employee_data(conn=None):
    # List of possible names, positions, departments, and locations
    if not os.path.exists(f'{data_path}/employees.csv'):
        # List of possible names, positions, departments, locations, and certifications
        names = [f"{name}_{i}" for i in range(1, 11) for name in ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Hank", "Ivy", "Jack"]]
        positions = ["Manager", "Engineer", "Salesperson", "HR Specialist", "Marketing Analyst"]
        departments = ["Engineering", "Marketing", "HR", "Sales", "Finance"]
        locations = ["New York", "San Francisco", "Austin", "Boston", "Chicago"]

        # Generate random hire dates
        def random_hire_date():
            start_date = datetime.date(2000, 1, 1)
            end_date = datetime.date(2023, 12, 31)
            time_between_dates = end_date - start_date
            days_between_dates = time_between_dates.days
            random_number_of_days = random.randrange(days_between_dates)
            return start_date + datetime.timedelta(days=random_number_of_days)

        # Generate random employee records with an employee ID (eid)
        employees = []
        for eid, name in zip(range(1, 101), names):  # 100 employees with `eid` starting from 1
            position = random.choice(positions)
            salary = round(random.uniform(50000, 150000), 2)  # Salary between 50,000 and 150,000
            department = random.choice(departments)
            location = random.choice(locations)
            hire_date = random_hire_date()
            performance_score = round(random.uniform(1, 5), 2)  # Performance score between 1.0 and 5.0
            years_of_experience = random.randint(1, 30)  # Years of experience between 1 and 30

            employee = {
                "eid": eid,  # Employee ID
                "name": name,
                "position": position,
                "salary": salary,
                "department": department,
                "location": location,
                "hire_date": hire_date,
                "performance_score": performance_score,
                "years_of_experience": years_of_experience
            }

            employees.append(employee)

        # Convert the list of dictionaries to a DataFrame and save to DB
        df_employees = pd.DataFrame(employees)
        df_employees.to_csv(f'{data_path}/employees.csv', index=False)
    else:
        logger.info(f"{'* ' * 50}\n\nLoading data from CSV File\n\n{'* ' * 50}")
        df_employees = pd.read_csv(f'{data_path}/employees.csv')

    df_employees.to_sql('employees', conn, index=False, if_exists='replace')


# Function to generate random project data with `eid` and project attributes
def generate_projects(conn=None):
    if not os.path.exists(f'{data_path}/projects.csv'):
        employees = pd.read_sql_query("SELECT eid FROM employees", conn)
        project_names = [f"{p} {i}" for i in range(20) for p in ["Project Alpha", "Project Beta", "Project Gamma", "Project Delta", "Project Omega"]]
        scopes = ["small", "medium", "large"]
        projects = []

        for project_name in project_names:  # 200 project records
            # eid = random.choice(employees['eid'])
            # project_name = random.choice(project_names)
            scope = random.choice(scopes)
            timeline = random.randint(1, 12)  # Duration in months
            resources_allocated = round(random.uniform(50000, 200000), 2)  # Budget in dollars

            project_record = {
                "project_name": project_name,
                "scope": scope,
                "timeline": timeline,
                "resources_allocated": resources_allocated
            }
            projects.append(project_record)

        # Convert the list of dictionaries to a DataFrame and save to DB
        df_projects = pd.DataFrame(projects)
        df_projects.to_csv(f'{data_path}/projects.csv', index=False)
    else:
        logger.info(f"{'* ' * 50}\n\nLoading projects data from CSV file\n\n{'* ' * 50}")
        df_projects = pd.read_csv(f'{data_path}/projects.csv')

    df_projects.to_sql('projects', conn, index=False, if_exists='replace')



# Function to generate random salary history data with `eid` and salary increase details
def generate_salary_history(conn=None):
    if not os.path.exists(f'{data_path}/salary_history.csv'):
        employees = pd.read_sql_query("SELECT eid FROM employees", conn)
        salary_history_records = []

        for eid in employees["eid"]:  # 400 salary history records
            # eid = random.choice(employees['eid'])
            salary_increase_percentage = round(random.uniform(5, 20), 2)  # Salary increase in percentage
            promotion_date = f"20{random.randint(10, 23)}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"  # Random date from 2010 to 2023

            salary_history_record = {
                "eid": eid,
                "salary_increase_percentage": salary_increase_percentage,
                "promotion_date": promotion_date
            }
            salary_history_records.append(salary_history_record)

        # Convert the list of dictionaries to a DataFrame and save to DB
        df_salary_history = pd.DataFrame(salary_history_records)
        df_salary_history.to_csv(f'{data_path}/salary_history.csv', index=False)
    else:
        logger.info(f"{'* ' * 50}\n\nLoading salary history data from CSV file\n\n{'* ' * 50}")
        df_salary_history = pd.read_csv(f'{data_path}/salary_history.csv')

    df_salary_history.to_sql('salary_history', conn, index=False, if_exists='replace')



# Function to generate random certifications data with `eid`
def generate_certifications(conn=None):
    if not os.path.exists(f'{data_path}/certifications.csv'):
        employees = pd.read_sql_query("SELECT eid FROM employees", conn)
        certifications_list = ["AWS Certified", "Google Cloud Certified", "PMP", "Scrum Master", "Cisco Certified"]
        employee_certifications = []

        for _ in range(300):  # 300 certification records
            eid = random.choice(employees['eid'])
            certification = random.choice(certifications_list)

            cert_record = {
                "eid": eid,  # Foreign key from employees table
                "certification_name": certification
            }

            employee_certifications.append(cert_record)

        # Convert the list of dictionaries to a DataFrame and save to DB
        df_certifications = pd.DataFrame(employee_certifications)
        df_certifications.to_csv(f'{data_path}/certifications.csv', index=False)
    else:
        logger.info(f"{'* ' * 50}\n\nLoading data from CSV File\n\n{'* ' * 50}")
        df_certifications = pd.read_csv(f'{data_path}/certifications.csv')

    df_certifications.to_sql('certifications', conn, index=False, if_exists='replace')


# Function to generate random mentorship data with `mentor_id` and `mentee_id`
def generate_mentorship(conn=None):
    if not os.path.exists(f'{data_path}/mentorship.csv'):
        employees = pd.read_sql_query("SELECT eid FROM employees", conn)
        mentorship_records = []

        for _ in range(500):  # 200 mentorship records
            mentor_id = random.choice(employees['eid'])
            mentee_id = random.choice(employees['eid'])

            if mentor_id != mentee_id:  # Avoid self-mentorship
                mentorship_record = {
                    "mentor_id": mentor_id,
                    "mentee_id": mentee_id
                }
                mentorship_records.append(mentorship_record)

        # Convert the list of dictionaries to a DataFrame and save to DB
        df_mentorship = pd.DataFrame(mentorship_records)
        df_mentorship.to_csv(f'{data_path}/mentorship.csv', index=False)
    else:
        logger.info(f"{'* ' * 50}\n\nLoading mentorship data from CSV file\n\n{'* ' * 50}")
        df_mentorship = pd.read_csv(f'{data_path}/mentorship.csv')

    df_mentorship.to_sql('mentorship', conn, index=False, if_exists='replace')


# Function to generate random remote work data with `eid` and remote work hours
def generate_remote_work(conn=None):
    if not os.path.exists(f'{data_path}/remote_work.csv'):
        employees = pd.read_sql_query("SELECT eid FROM employees", conn)["eid"].tolist()
        remote_work_records = []

        for _ in range(80):  # 50 remote work records
            eid = random.choice(employees)
            hours_worked = random.randint(20, 40)  # Weekly remote hours worked
            projets_completed = random.randint(1, 5)  # Number of projects completed

            remote_work_record = {
                "eid": eid,
                "hours_worked": hours_worked,
                "projects_completed": projets_completed,  # Number of projects completed
            }
            remote_work_records.append(remote_work_record)
            employees.remove(eid)

        # Convert the list of dictionaries to a DataFrame and save to DB
        df_remote_work = pd.DataFrame(remote_work_records)
        df_remote_work.to_csv(f'{data_path}/remote_work.csv', index=False)
    else:
        logger.info(f"{'* ' * 50}\n\nLoading remote work data from CSV file\n\n{'* ' * 50}")
        df_remote_work = pd.read_csv(f'{data_path}/remote_work.csv')

    df_remote_work.to_sql('remote_work', conn, index=False, if_exists='replace')


# Function to generate random productivity data with `eid` and various productivity metrics
def generate_productivity(conn=None):
    if not os.path.exists(f'{data_path}/productivity.csv'):
        employees = pd.read_sql_query("SELECT eid FROM employees", conn)
        productivity_metrics = []

        for eid in employees["eid"]:  # 500 productivity records
            # eid = random.choice(employees['eid'])
            tasks_completed = random.randint(50, 150)
            meeting_attendance = random.randint(70, 100)  # Percentage of meetings attended
            peer_feedback = round(random.uniform(3.0, 5.0), 2)  # Rating between 3 and 5
            leadership = round(random.uniform(2.0, 5.0), 2)  # Rating between 3 and 5
            communication = round(random.uniform(1.0, 5.0), 2)  # Rating between 3 and 5
            problem_solving = round(random.uniform(2.0, 5.0), 2)  # Rating between 3 and 5

            productivity_record = {
                "eid": eid,
                "tasks_completed": tasks_completed,
                "meeting_attendance": meeting_attendance,
                "peer_feedback": peer_feedback,
                "leadership": leadership,
                "communication": communication,
                "problem_solving": problem_solving,
            }
            productivity_metrics.append(productivity_record)

        # Convert the list of dictionaries to a DataFrame and save to DB
        df_productivity = pd.DataFrame(productivity_metrics)
        df_productivity.to_csv(f'{data_path}/productivity.csv', index=False)
    else:
        logger.info(f"{'* ' * 50}\n\nLoading productivity data from CSV file\n\n{'* ' * 50}")
        df_productivity = pd.read_csv(f'{data_path}/productivity.csv')

    df_productivity.to_sql('productivity', conn, index=False, if_exists='replace')


def generate_project_performance(conn=None):
    if not os.path.exists(f'{data_path}/project_performance.csv'):
        employees = pd.read_sql_query("SELECT eid FROM employees", conn)
        projects = pd.read_sql_query("SELECT DISTINCT project_name as project_name FROM projects", conn)
        project_performance_records = []

        for _ in range(500):  # 500 project performance records
            eid = random.choice(employees['eid'])
            project_name = random.choice(projects['project_name'])
            success_rate = round(random.uniform(1, 11), 2)  # Success rate between 0 and 1
            performance_score = round(random.uniform(50, 100), 2)  # Performance score between 50 and 100

            project_performance_record = {
                "project_name": project_name,
                "eid": eid,
                "success_rate": success_rate,
                "performance_score": performance_score
            }

            project_performance_records.append(project_performance_record)

        # Convert the list of dictionaries to a DataFrame and save to DB
        df_project_performance = pd.DataFrame(project_performance_records)
        df_project_performance.to_csv(f'{data_path}/project_performance.csv', index=False)
    else:
        logger.info(f"{'* ' * 50}\n\nLoading project performance data from CSV file\n\n{'* ' * 50}")
        df_project_performance = pd.read_csv(f'{data_path}/project_performance.csv')

    df_project_performance.to_sql('project_performance', conn, index=False, if_exists='replace')


def generate_mentee_performance(conn=None):
    if not os.path.exists(f'{data_path}/mentee_performance.csv'):
        # employees = pd.read_sql_query("SELECT eid FROM employees", conn)
        employees = pd.read_sql_query("SELECT DISTINCT mentee_id as mentee_id FROM mentorship", conn)
        mentee_performance_records = []

        for mentee_id in employees["mentee_id"]:  # 300 mentee performance records
            # mentee_id = random.choice(employees['eid'])
            mentee_performance_improvement = round(random.uniform(5, 30), 2)  # Improvement percentage between 5 and 30
            projects_participated = random.randint(1, 5)  # Number of projects participated in

            mentee_performance_record = {
                "mentee_id": mentee_id,
                "mentee_performance_improvement": mentee_performance_improvement,
                "projects_participated": projects_participated
            }

            mentee_performance_records.append(mentee_performance_record)

        # Convert the list of dictionaries to a DataFrame and save to DB
        df_mentee_performance = pd.DataFrame(mentee_performance_records)
        df_mentee_performance.to_csv(f'{data_path}/mentee_performance.csv', index=False)
    else:
        logger.info(f"{'* ' * 50}\n\nLoading mentee performance data from CSV file\n\n{'* ' * 50}")
        df_mentee_performance = pd.read_csv(f'{data_path}/mentee_performance.csv')

    df_mentee_performance.to_sql('mentee_performance', conn, index=False, if_exists='replace')
