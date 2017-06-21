# -*- coding:utf-8 -*-

from benchmark_django_rest_framework.benchmark_api_view import BenchmarkAPIView, SETTINGS
from benchmark_app.models import *
from benchmark_app.demo_init_data import *
import json


class CompanyView(BenchmarkAPIView):
    primary_model = Company


class DepartmentView(BenchmarkAPIView):
    primary_model = Department


class EmployeeView(BenchmarkAPIView):
    primary_model = Employee


class ProjectTeamView(BenchmarkAPIView):
    primary_model = ProjectTeam


class PCView(BenchmarkAPIView):
    primary_model = PC


# # If the MODEL_DELETE_FLAG is not None, we should define the many to many relation models manually, as follow:
# class ProjectTeamToEmployeeView(BenchmarkAPIView):
#     primary_model = ProjectTeamToEmployee


class InitDataView(BenchmarkAPIView):
    primary_model = None
    view_not_support_methods = ('get', 'put', 'delete')
    need_login = False    # Whether this api needs login first. If we haven't defined this variable, the default value is False.

    def post_model(self, data=None):
        Company.objects.all().delete()
        ProjectTeam.objects.all().delete()
        tuple_model = (Company, Department, Employee, ProjectTeam, PC)
        tuple_init_data = (init_companies, init_departments, init_employees, init_project_teams, init_pcs)
        for model, init_data in zip(tuple_model, tuple_init_data):
            for data in init_data:
                field_names = tuple(data.keys())
                many_to_many_relations = {}
                for field_name in field_names:
                    field = getattr(model, field_name)
                    if hasattr(field, 'field'):
                        if field.field.many_to_many:
                            related_model = field.field.related_model
                            related_ms = []
                            for pk in data[field_name]:
                                related_m = related_model.objects.filter(pk=pk).first()
                                if related_m is not None:
                                    related_ms.append(related_m)
                            many_to_many_relations[field_name] = related_ms
                            del data[field_name]
                        else:
                            data[field.field.attname] = data[field_name]
                            del data[field_name]
                for key, value in data.items():
                    if key in SETTINGS.MODEL_JSON_FIELD_NAMES:
                        data[key] = json.dumps(value)
                m = model(**data)
                m.save()
                for field_name, related_ms in many_to_many_relations.items():
                    for related_m in related_ms:
                        getattr(m, field_name).add(related_m)
        return self.get_response_by_code()
