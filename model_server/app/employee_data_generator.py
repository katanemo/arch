import pandas as pd
import random
import datetime


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
            salary = round(
                random.uniform(50000, 150000), 2
            )  # Salary between 50,000 and 150,000
            department = random.choice(departments)
            location = random.choice(locations)
            hire_date = random_hire_date()
            performance_score = round(
                random.uniform(1, 5), 2
            )  # Performance score between 1.0 and 5.0
            years_of_experience = random.randint(
                1, 30
            )  # Years of experience between 1 and 30

            employee = {
                "position": position,
                "name": name,
                "salary": salary,
                "department": department,
                "location": location,
                "hire_date": hire_date,
                "performance_score": performance_score,
                "years_of_experience": years_of_experience,
            }

            employees.append(employee)

        return employees

    # Generate 10 random employee records
    employee_records = generate_employee_records(200)

    # Convert the list of dictionaries to a DataFrame
    df = pd.DataFrame(employee_records)

    df.to_sql("employees", conn, index=False)

    return
