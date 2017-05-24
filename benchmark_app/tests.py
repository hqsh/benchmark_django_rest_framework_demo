# -*- coding:utf-8 -*-

from benchmark_django_rest_framework.benchmark_test import *
from benchmark_app.demo_init_data import *


'''
This script is to initate the data for test benchmark django rest framework.
In the sample, the initial data in models and their relationships are as follow:
    1. foreign key relationships:
    COMPANY         DEPARTMENT         EMPLOYEE
    CompanyA        DepartmentX        EmployeeAX1, EmployeeAX2
                    DepartmentY        EmployeeAY1, EmployeeAY2
    CompanyB        DepartmentX        EmployeeBX1, EmployeeBX2
                    DepartmentY        EmployeeBY1, EmployeeBY2

    2. many to many relationships:
    PROJECT TEAM    EMPLOYEE
    ProjectTeam1    EmployeeAX1, EmployeeAY1, EmployeeBX1
    ProjectTeam2    EmployeeAX1, EmployeeAY2, EmployeeBX2

    3. one to many relationships:
    PC              EMPLOYEE
    PC1             EmployeeAX1
    PC2             EmployeeAX2

    After run this script, we can see these data and their relationships above by http get requests:
    http://127.0.0.1:8000/company
    http://127.0.0.1:8000/department?filter_fields=company_name|department_name
    http://127.0.0.1:8000/employee?filter_fields=company_name|department_name|employee_name
    http://127.0.0.1:8000/project_team?filter_fields=project_team_name|members
    http://127.0.0.1:8000/pc
'''


def delete_all_suite(suite=unittest.TestSuite()):
    suite.addTest(CompanyTestCase('get'))
    suite.addTest(CompanyTestCase('delete', data={'delete_pk_in_res': 'company_id'}))
    suite.addTest(ProjectTeamTestCase('get'))
    suite.addTest(ProjectTeamTestCase('delete', data={'delete_pk_in_res': 'project_team_id'}))
    return suite


def company_init_suite(suite=unittest.TestSuite()):
    for data in init_companies:
        suite.addTest(CompanyTestCase('post', data=data))
    return suite


def department_init_suite(suite=unittest.TestSuite()):
    for data in init_departments:
        suite.addTest(DepartmentTestCase('post', data=data))
    return suite


def employee_init_suite(suite=unittest.TestSuite()):
    for data in init_employees:
        suite.addTest(EmployeeTestCase('post', data=data))
    return suite


def project_team_init_suite(suite=unittest.TestSuite()):
    for data in init_project_teams:
        suite.addTest(ProjectTeamTestCase('post', data=data))
    return suite


def pc_init_suite(suite=unittest.TestSuite()):
    for data in init_pcs:
        suite.addTest(PCTestCase('post', data=data))
    return suite


# def get_project_team_to_employee_init_suite(suite=unittest.TestSuite()):
#     # suite.addTest(ProjectTeamToEmployeeTestCase('post', data={'project_team': 1, 'employee': 5}))
#     return suite


def test_all():
    suite = unittest.TestSuite()
    suite = delete_all_suite(suite)
    suite = company_init_suite(suite)
    suite = department_init_suite(suite)
    suite = employee_init_suite(suite)
    suite = project_team_init_suite(suite)
    suite = pc_init_suite(suite)
    # suite = project_team_to_employee_test_suite(suite)
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest='test_all')


'''
Benchmark Django Rest Framework is framework based on Django Rest Framework (http://www.django-rest-framework.org).
The BenchmarkAPIView inherit from APIView, with BenchmarkModel, can let us develop django rest api for model data
search/add/modify/delete (by http request GET/POST/PUT/DELETE) easily. Only two line

The main ideas and features of Benchmark Django Rest Framework is:
    Firstly, if an view just do some model processes (SELECT/ADD/UPDATE/DELETE), the HTTP requests has already given
    the sufficient information to do that. So we needn't develop so much views manually.
    Secondly, based on the first idea, we can develop each view supports various input (various HTTP request parameters
    for different model processes) and various output for different SELECT model (by various HTTP GET request
    parameters). So we just need only one view for a model which has various inputs and outputs. And the view can act as
    many views which every one has a fixed and different inputs and outputs.

The main features of Benchmark Django Rest Framework are:
    One model just has only one view. In this view the model is called as "primary model". We can use the HTTP requests
    with the params and data which to control the model

(2) For http GET requests, we can use the parameters supported in django to filter models, for example:
    http://127.0.0.1:8000/employee?department__department_name=DepartmentY&department__company__company_name__endswith=B&order_by=-employee_name
    the query set is as follow:
    Employee.objects.filter(
        department__department_name=DepartmentB,
        department__company__company_name__endswith=B
    ).order_by('-employee_name')

(3) And for http GET requests, we can use the "select_related" parameter to search multiple models. The values of
    "select_related" are the fields of the ForeignKey, ManyToManyField, OneToOneField which defined in the primary
    model, or the names of other models (letters in lowercase) which defined in other models.
    For example:
    ForeignKey: http://127.0.0.1:8000/employee?select_related=department
    ManyToManyField: http://127.0.0.1:8000/project_team?select_related=members
    OneToOneField: http://127.0.0.1:8000/pc?select_related=employee
    And it also supports by related_name (reverse relation):
    reverse ForeignKey: http://127.0.0.1:8000/company?select_related=department_set
    reverse ManyToManyField: http://127.0.0.1:8000/employee?select_related=projectteam_set
    reverse OneToOneField: http://127.0.0.1:8000/employee?select_related=pc
    And it supports as many relations as you need, for example:
'''