import os
import sentence_transformers
from gliner import GLiNER
from transformers import pipeline
import sqlite3
import pandas as pd
import random
import datetime

def load_transformers(models = os.getenv("MODELS", "BAAI/bge-large-en-v1.5")):
    transformers = {}

    for model in models.split(','):
        transformers[model] = sentence_transformers.SentenceTransformer(model)

    return transformers

def load_ner_models(models = os.getenv("NER_MODELS", "urchade/gliner_large-v2.1")):
    ner_models = {}

    for model in models.split(','):
        ner_models[model] = GLiNER.from_pretrained(model)

    return ner_models

def load_zero_shot_models(models = os.getenv("ZERO_SHOT_MODELS", "tasksource/deberta-base-long-nli")):
    zero_shot_models = {}

    for model in models.split(','):
        zero_shot_models[model] = pipeline("zero-shot-classification",model=model)

    return zero_shot_models

def load_sql():
    # Example Usage
    data = generate_employee_data()
    conn = sqlite3.connect(':memory:')
    data.to_sql('employees', conn, index=False)
    return conn

def generate_employee_data():
    # List of possible names, positions, departments, and locations
    names = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Hank", "Ivy", "Jack"]
    positions = ["Manager", "Engineer", "Salesperson", "HR Specialist", "Marketing Analyst"]
    departments = ["Engineering", "Marketing", "HR", "Sales", "Finance"]
    locations = ["New York", "San Francisco", "Austin", "Boston", "Chicago"]

    # Function to generate random hire date
    def random_hire_date():
        start_date = datetime.date(2000, 1, 1)
        end_date = datetime.date(2023, 12, 31)
        time_between_dates = end_date - start_date
        days_between_dates = time_between_dates.days
        random_number_of_days = random.randrange(days_between_dates)
        hire_date = start_date + datetime.timedelta(days=random_number_of_days)
        return hire_date

    # Function to generate random employee data
    def generate_employee_records(count):
        employees = []
        
        for _ in range(count):
            name = random.choice(names)
            position = random.choice(positions)
            salary = round(random.uniform(50000, 150000), 2)  # Salary between 50,000 and 150,000
            department = random.choice(departments)
            location = random.choice(locations)
            hire_date = random_hire_date()
            performance_score = round(random.uniform(1, 5), 2)  # Performance score between 1.0 and 5.0
            years_of_experience = random.randint(1, 30)  # Years of experience between 1 and 30
            
            employee = {
                "position": position,
                "name": name,
                "salary": salary,
                "department": department,
                "location": location,
                "hire_date": hire_date,
                "performance_score": performance_score,
                "years_of_experience": years_of_experience
            }
            
            employees.append(employee)
        
        return employees

    # Generate 10 random employee records
    employee_records = generate_employee_records(200)

    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(employee_records)

    return df