# -*- coding:utf-8 -*-

import json
import requests
import unittest
from benchmark_django_rest_framework_demo.benchmark_settings import *


SERVER_URL = 'http://127.0.0.1:8000/'


class BenchmarkTestCase(unittest.TestCase):
    server_url = SERVER_URL
    uri = 'need to be defined in child class'
    uri_with_params = 'need to be defined in child class'
    res = None    # last response in dict

    def __init__(self, method, uri_params=None, params={}, data={}):
        self.method = method
        self.uri_params = uri_params
        self.params = params
        self.data = data
        super(BenchmarkTestCase, self).__init__('test_http')

    def get_url(self):
        if self.uri_params is None:
            url = self.server_url + self.uri
        else:
            uri = self.uri_with_params
            for key, value in self.uri_params.items():
                replace_key = '{{' + key + '}}'
                uri = uri.replace(replace_key, str(value))
            url = self.server_url + uri
        return url

    def test_http(self):
        if self.method == 'delete':
            if 'delete_pk_in_res' in self.data.keys():
                delete_pk_in_res = self.data['delete_pk_in_res']
            else:
                delete_pk_in_res = None
            if delete_pk_in_res is not None:
                pks = []
                for data in self.__class__.res[DATA]:
                    pks.append(data[delete_pk_in_res])
                if len(pks) == 0:
                    return
                self.data = {'pk': pks}
        req = getattr(requests, self.method)
        url = self.get_url()
        print('[%s %s request] url = %s, params = %s, data = %s' % (self.uri, self.method, url, self.params, self.data))
        res = req(url, params=self.params, data=self.data)
        test_fail = False
        json_load_fail = False
        try:
            dict_res = json.loads(res.text)
        except:
            test_fail = True
            json_load_fail = True
        try:
            assert res.status_code == 200
            assert dict_res[CODE] == 0
        except:
            test_fail = True
        if test_fail:
            print('[test fail] method = %s, uri_params = %s, params = %s, data = %s' %
                  (self.method, self.uri_params, self.params, self.data))
            if not json_load_fail:
                print('[%s %s response] %s' % (self.uri, self.method, res.text))
            raise Exception('test fail')
        self.__class__.res = copy.deepcopy(dict_res)


class CompanyTestCase(BenchmarkTestCase):
    uri = 'company'
    uri_with_params = uri + '/{{pk}}'


class DepartmentTestCase(BenchmarkTestCase):
    uri = 'department'
    uri_with_params = uri + '/{{pk}}'


class EmployeeTestCase(BenchmarkTestCase):
    uri = 'employee'
    uri_with_params = uri + '/{{pk}}'


class ProjectTeamTestCase(BenchmarkTestCase):
    uri = 'project_team'
    uri_with_params = uri + '/{{pk}}'


class PCTestCase(BenchmarkTestCase):
    uri = 'pc'
    uri_with_params = uri + '/{{pk}}'


# class ProjectTeamToEmployeeTestCase(BenchmarkTestCase):
#     uri = 'project_team_to_employee'
#     uri_with_params = uri + '/{{pk}}'
