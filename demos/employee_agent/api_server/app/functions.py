from typing import List, Optional

# Function for top_employees
def top_employees(grouping: str, ranking_criteria: str, top_n: int):
    pass

# Function for aggregate_stats
def aggregate_stats(grouping: str, aggregate_criteria: str, aggregate_type: str):
    pass

# Function for employees_projects
def employees_projects(min_performance_score: float, min_years_experience: int, department: str, min_project_count: int = None, months_range: int = None):
    pass

# Function for salary_growth
def salary_growth(min_salary_increase_percentage: float, department: str = None):
    pass

# Function for promotions_increases
def promotions_increases(year: int, min_salary_increase_percentage: float = None, department: str = None):
    pass

# Function for avg_project_performance
def project_performance(min_project_count: int, min_performance_score: float, department: str = None):
    pass

# Function for certifications_experience
def certifications_experience(certifications: list, min_years_experience: int, department: str = None):
    pass


class EmployeeAnalysis:
    """
    A class to analyze employee data, including finding top employees, calculating aggregate statistics,
    filtering by projects and performance, tracking salary growth, promotions, and more.
    """

    @staticmethod
    def top_employees(grouping: str, ranking_criteria: str, top_n: int = 3) -> list:
        """
        Allows you to find the top employees in different groups, such as departments, locations, or position.
        You can rank the employees by different criteria, like salary, years of experience, or performance score.
        Returns the best-ranked employees for each group.

        Parameters:
        - grouping (str): Select how you'd like to group the employees. Options include 'department', 'location', or 'position'.
        - ranking_criteria (str): Choose how to rank employees. Options include 'salary', 'years_of_experience', or 'performance_score'.
        - top_n (int, optional): The number of top employees to return for each group. Default is 3.

        Returns:
        - list: A list of top-ranked employees for each group.
        """
        # Implementation goes here
        pass

    @staticmethod
    def aggregate_stats(grouping: str, aggregate_criteria: str, aggregate_type: str) -> dict:
        """
        Calculate summary statistics for groups of employees, such as totals, averages, or other statistics.

        Parameters:
        - grouping (str): How to group employees, such as 'department', 'location', or 'position'.
        - aggregate_criteria (str): The attribute to analyze, such as 'salary', 'years_of_experience', or 'performance_score'.
        - aggregate_type (str): The type of statistic to calculate. Options include 'SUM', 'AVG', 'MIN', or 'MAX'.

        Returns:
        - dict: A dictionary containing the calculated summary statistics for each group.
        """
        # Implementation goes here
        pass

    @staticmethod
    def employees_projects(min_years_experience: int, department: str, min_performance_score: float = 4.0,
                           min_project_count: int = 3, months_range: int = None) -> list:
        """
        Fetch employees with the highest performance scores, filtered by project participation, years of experience,
        department, and optionally by recent projects.

        Parameters:
        - min_years_experience (int): Minimum years of experience to filter employees.
        - department (str): Department to filter employees by.
        - min_performance_score (float, optional): Minimum performance score to filter employees. Default is 4.0.
        - min_project_count (int, optional): Minimum number of projects employees participated in. Default is 3.
        - months_range (int, optional): Timeframe in months to filter recent project participation.

        Returns:
        - list: A list of employees matching the criteria.
        """
        # Implementation goes here
        pass

    @staticmethod
    def salary_growth(min_salary_increase_percentage: float, department: str = "Sales") -> list:
        """
        Fetch employees with the highest salary growth since their last promotion, grouped by department.

        Parameters:
        - min_salary_increase_percentage (float): Minimum percentage increase in salary since the last promotion.
        - department (str, optional): Department to filter employees by. Default is 'Sales'.

        Returns:
        - list: A list of employees matching the salary growth criteria.
        """
        # Implementation goes here
        pass

    @staticmethod
    def promotions_increases(year: int, min_salary_increase_percentage: float = 10.0, department: str = "Engineering") -> list:
        """
        Fetch employees who were promoted and received a salary increase in a specific year, grouped by department.

        Parameters:
        - year (int): The year in which the promotion and salary increase occurred.
        - min_salary_increase_percentage (float, optional): Minimum percentage salary increase to filter employees. Default is 10.0.
        - department (str, optional): Department to filter by. Default is 'Engineering'.

        Returns:
        - list: A list of employees who meet the promotion and salary increase criteria.
        """
        # Implementation goes here
        pass

    @staticmethod
    def certifications_experience(certifications: list, min_years_experience: int, department: str = None) -> list:
        """
        Fetch employees who have the required certifications and meet the minimum years of experience.

        Parameters:
        - certifications (list): List of required certifications.
        - min_years_experience (int): Minimum years of experience.
        - department (str, optional): Department to filter employees by.

        Returns:
        - list: A list of employees who meet the certification and experience criteria.
        """
        # Implementation goes here
        pass
