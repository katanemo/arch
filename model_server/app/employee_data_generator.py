import pandas as pd
import random
import datetime

# Function to generate random employee data with `eid` as the primary key
def generate_employee_data(conn):
    # List of possible names, positions, departments, and locations
    names = [
        "Alice",
        "Bob",
        "Charlie",
        "David",
        "Eve",
        "Frank",
        "Grace",
        "Hank",
        "Ivy",
        "Jack",
    ]
    positions = [
        "Manager",
        "Engineer",
        "Salesperson",
        "HR Specialist",
        "Marketing Analyst",
    ]
    # List of possible names, positions, departments, locations, and certifications
    names = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Hank", "Ivy", "Jack"]
    positions = ["Manager", "Engineer", "Salesperson", "HR Specialist", "Marketing Analyst"]
    departments = ["Engineering", "Marketing", "HR", "Sales", "Finance"]
    locations = ["New York", "San Francisco", "Austin", "Boston", "Chicago"]
    certifications = ["AWS Certified", "Google Cloud Certified", "PMP", "Scrum Master", "Cisco Certified"]

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
    for eid in range(1, 101):  # 100 employees with `eid` starting from 1
        name = random.choice(names)
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
    df_employees.to_sql('employees', conn, index=False, if_exists='replace')

# Function to generate random project data with `eid`
def generate_project_data(conn):
    employees = pd.read_sql_query("SELECT eid FROM employees", conn)
    projects = []

    for _ in range(500):  # 500 projects
        eid = random.choice(employees['eid'])
        project_name = f"Project_{random.randint(1, 100)}"
        start_date = datetime.date(2020, 1, 1) + datetime.timedelta(days=random.randint(0, 365 * 3))  # Within the last 3 years
        performance_score = round(random.uniform(1, 5), 2)  # Performance score for the project between 1.0 and 5.0

        project = {
            "eid": eid,  # Foreign key from employees table
            "project_name": project_name,
            "start_date": start_date,
            "performance_score": performance_score
        }

        projects.append(project)

    # Convert the list of dictionaries to a DataFrame and save to DB
    df_projects = pd.DataFrame(projects)
    df_projects.to_sql('projects', conn, index=False, if_exists='replace')

# Function to generate random salary history data with `eid`
def generate_salary_history(conn):
    employees = pd.read_sql_query("SELECT eid FROM employees", conn)
    salary_history = []

    for _ in range(300):  # 300 salary records
        eid = random.choice(employees['eid'])
        salary_increase_percentage = round(random.uniform(5, 30), 2)  # Salary increase between 5% and 30%
        promotion_date = datetime.date(2018, 1, 1) + datetime.timedelta(days=random.randint(0, 365 * 5))  # Promotions in the last 5 years

        salary_record = {
            "eid": eid,  # Foreign key from employees table
            "salary_increase_percentage": salary_increase_percentage,
            "promotion_date": promotion_date
        }

        salary_history.append(salary_record)

    # Convert the list of dictionaries to a DataFrame and save to DB
    df_salary_history = pd.DataFrame(salary_history)
    df_salary_history.to_sql('salary_history', conn, index=False, if_exists='replace')

# Function to generate random certifications data with `eid`
def generate_certifications(conn):
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
    df_certifications.to_sql('certifications', conn, index=False, if_exists='replace')
