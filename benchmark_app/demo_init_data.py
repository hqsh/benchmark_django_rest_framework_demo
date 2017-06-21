init_companies = [
    {"company_id": 1, "company_name": "CompanyA"},
    {"company_id": 2, "company_name": "CompanyB"},
]

init_departments = [
    {"department_id": 1, "department_name": "DepartmentX", "company": 1},
    {"department_id": 2, "department_name": "DepartmentY", "company": 1},
    {"department_id": 3, "department_name": "DepartmentX", "company": 2},
    {"department_id": 4, "department_name": "DepartmentY", "company": 2},
]

init_employees = [
    {"employee_id": 1, "employee_name": "EmployeeAX1", "department": 1, "employee_info": {"sex": "male", "age": 40}},
    {"employee_id": 2, "employee_name": "EmployeeAX2", "department": 1, "employee_info": {"sex": "female", "new_employee": True}},
    {"employee_id": 3, "employee_name": "EmployeeAY1", "department": 2},
    {"employee_id": 4, "employee_name": "EmployeeAY2", "department": 2},
    {"employee_id": 5, "employee_name": "EmployeeBX1", "department": 3},
    {"employee_id": 6, "employee_name": "EmployeeBX2", "department": 3},
    {"employee_id": 7, "employee_name": "EmployeeBY1", "department": 4},
    {"employee_id": 8, "employee_name": "EmployeeBY2", "department": 4},
]

init_project_teams = [
    {"project_team_id": 1, "project_team_name": "ProjectTeam1", "members": [1, 3, 5]},
    {"project_team_id": 2, "project_team_name": "ProjectTeam2", "members": [1, 4, 6]},
]

init_pcs = [
    {"pc_id": 1, "pc_name": "PC1", "employee": 1},
    {"pc_id": 2, "pc_name": "PC2", "employee": 2},
]

