# -*- coding:utf-8 -*-

from __future__ import unicode_literals
from benchmark_django_rest_framework.benchmark_model import BenchmarkModel
from django.conf import settings
from django.db import models
from mongoengine import Document, StringField, ListField


class Company(BenchmarkModel, models.Model):
    company_id = models.IntegerField(primary_key=True)
    company_name = models.CharField(max_length=64)
    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)
    # delete_flag = models.BooleanField(default=0, choices=((0, 'exist'), (1, 'deleted')))


class Department(BenchmarkModel, models.Model):
    department_id = models.IntegerField(primary_key=True)
    department_name = models.CharField(max_length=64)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)
    # delete_flag = models.BooleanField(default=0, choices=((0, 'exist'), (1, 'deleted')))


class Employee(BenchmarkModel, models.Model):
    employee_id = models.IntegerField(primary_key=True)
    employee_name = models.CharField(max_length=64)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    employee_info = models.TextField(max_length=1024, null=True)
    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)
    # delete_flag = models.BooleanField(default=0, choices=((0, 'exist'), (1, 'deleted')))


class ProjectTeam(BenchmarkModel, models.Model):
    project_team_id = models.IntegerField(primary_key=True)
    project_team_name = models.CharField(max_length=64)
    members = models.ManyToManyField(Employee)
    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)
    # delete_flag = models.BooleanField(default=0, choices=((0, 'exist'), (1, 'deleted')))


class PC(BenchmarkModel, models.Model):
    pc_id = models.IntegerField(primary_key=True)
    pc_name = models.CharField(max_length=64)
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE)
    create_time = models.DateTimeField(auto_now_add=True)
    modify_time = models.DateTimeField(auto_now=True)
    # delete_flag = models.BooleanField(default=0, choices=((0, 'exist'), (1, 'deleted')))


# class ProjectTeamToEmployee(BenchmarkModel, models.Model):
#     id = models.AutoField(primary_key=True)
#     project_team = models.ForeignKey(ProjectTeam, on_delete=models.CASCADE)
#     employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
#     create_time = models.DateTimeField(auto_now_add=True)
#     modify_time = models.DateTimeField(auto_now=True)
#     # delete_flag = models.BooleanField(default=0, choices=((0, 'exist'), (1, 'deleted')))
#
#     class Meta:
#         unique_together = ('project_team', 'employee')


# mongo db
class Article(BenchmarkModel, Document):
    title = StringField()
    authors = ListField(StringField())
    context = StringField()
