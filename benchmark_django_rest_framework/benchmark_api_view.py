# -*- coding:utf-8 -*-

from collections import OrderedDict
from django.db.models import Model
from django.http import JsonResponse, StreamingHttpResponse
from django.utils.decorators import classonlymethod
from django_filters import rest_framework as filters
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer, Serializer
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet, ModelViewSet
import copy
import django
import json
import math
import logging
import redis
import rest_framework
import sys
import time


SETTINGS = getattr(django.conf.settings, 'BENCHMARK_SETTINGS', None)
if SETTINGS is None:
    raise Exception('BENCHMARK_SETTINGS should be defined in django settings.py file, which is the path of '
                    'benchmark_settings file. For example "BENCHMARK_SETTINGS = your_site_app_dir.benchmark_settings"')
try:
    SETTINGS = sys.modules[SETTINGS]
except KeyError:
    raise Exception('BENCHMARK_SETTINGS defined in django settings.py file is not correct. The benchmark_settings file '
                    'does not exist.')


class Logger:
    def __init__(self):
        log_str = '\r[%(asctime)s] %(levelname)s: %(message)s'
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.INFO)
        self.stream_handler = logging.StreamHandler(sys.stdout)
        self.stream_handler.setFormatter(logging.Formatter(log_str))

    def log(self, msg, level='info'):
        self.logger.addHandler(self.stream_handler)
        getattr(self.logger, level)(msg)
        self.logger.removeHandler(self.stream_handler)


PARENT_VIEW_CHOICES = (APIView.__name__, GenericAPIView.__name__, ViewSet.__name__, ModelViewSet.__name__)
if SETTINGS.PARENT_VIEW in PARENT_VIEW_CHOICES:
    PARENT_VIEW = eval(SETTINGS.PARENT_VIEW)
else:
    raise Exception('SETTINGS.PARENT_VIEW should be %s, %s, %s or %s.' % PARENT_VIEW_CHOICES)


class BenchmarkAPIView(PARENT_VIEW):

    @classonlymethod
    def init(cls):
        # Each value of settings as follow is got from class variable (in lowercase) in each view firstly. If it is not
        # defined in class variable, then it is got from the global variable (in uppercase) in benchmark_settings.py
        # secondly. If it is not defined in benchmark_settings.py, then set it as default value.
        # The descriptions of these settings are in benchmark_settings.py.
        for setting, default_value in (
            ('data_style', 'dict'),
            ('omit_underlines', True),
            ('rename_params', {}),
            ('rename_uri_params', {}),
            ('rename_data', {}),
            ('rename_fields', {}),
            ('http_get_check_params', False),   # whether check params in http get request by serializer
            ('serializer_use_benchmark_code', True),    # whether serializer use benchmark code and return the error response
            ('enable_select_related_in_params', False),
            ('only_enable_select_related_for_get_one', False),
            ('redis_ip', 'localhost'),
            ('redis_port', 6379),
            ('redis_db', 0),
        ):
            if not hasattr(cls, setting):
                setattr(cls, setting, getattr(SETTINGS, setting.upper(), default_value))
        cls.queryset = None if cls.primary_model is None else cls.primary_model.objects.all()
        # Each value of settings as follow is got from class variable (in lowercase) in each view firstly. If it is not
        # defined in class variable, then set it as default value.
        for setting, default_value in (
            ('primary_model', None),       # primary model
            ('using', 'default'),          # the database name of primary model
            ('access', {'get': 'all', 'post': 'all', 'put': 'all', 'delete': 'all'}),    # access right for api
            ('select_related', None),      # http get request search data in multiple models
            ('values', None),              # This setting filter for response data fields, similar to django model
                                           # "values" function. It supports only the first level fields, and it
                                           # supports to set in http get request params.
            ('values_fields', {}),         # This setting filter for response data fields, similar to django model
                                           # "values" function. It supports multiple level fields.
            ('values_white_list', True),   # whether the field names in values_fields is in white list
            ('get_one', None),             # When "pk" is not in uri, data field in response is a list by default.
                                           # If set "get_one" to "True", data field in response is a dict as the first
                                           # item in the list if the request has search results.
                                           # When "pk" is in uri, data field in response is a list by dict. If set
                                           # "get_one" to "False", data field in response are several dicts within a
                                           # list.
            ('methods_not_need_convert_keys_for_request', None),
            ('methods_not_need_convert_keys_for_response', None),
            ('check_params', {'get': (), 'post': (), 'put': (), 'delete': ()}),    # check params exist in request
            ('check_data', {'get': (), 'post': (), 'put': (), 'delete': ()}),      # check data exist in request
            ('enabled_select_related_in_params', []),       # If enable_select_related_in_params is True, this variable
                                                            # defines which select_related strings can be accepted.
            ('bool_params', []),           # bool params defined here will be translate to boolean type from string
        ):
            if not hasattr(cls, setting):
                setattr(cls, setting, default_value)
        # more steps for initiate some settings
        for method in {'get', 'post', 'put', 'delete'} - set(cls.access.keys()):
            cls.access[method] = None
        for check in (cls.check_params, cls.check_data):
            for method in ('get', 'post', 'put', 'delete'):
                if method not in check.keys():
                    check[method] = ()
        cls.values_fields_in_data = {}
        cls.values_fields_in_data_results = {}
        for key, value in cls.values_fields.items():
            cls.values_fields_in_data['/' + SETTINGS.DATA + key] = value
            cls.values_fields_in_data_results['/' + SETTINGS.DATA + '/' + SETTINGS.RESULT + key] = value
        cls.rename_fields_in_data = {}
        cls.rename_fields_in_data_results = {}
        for key, value in cls.rename_fields.items():
            cls.rename_fields_in_data['/' + SETTINGS.DATA + key] = value
            cls.rename_fields_in_data_results['/' + SETTINGS.DATA + '/' + SETTINGS.RESULT + key] = value
        # initiate redis
        if hasattr(cls, 'get_redis'):
            cls.redis = redis.StrictRedis(host=cls.redis_ip, port=cls.redis_port, db=cls.redis_db)
        # other initial steps
        cls.logger = Logger()
        cls.init_serializer()

    def __init__(self):
        super(BenchmarkAPIView, self).__init__()
        self.request = None
        self.params = {}
        self.uri_params = {}
        self.data = {}
        self.host = None
        self.path = ''
        self.method = ''
        self.offset = None
        self.limit = None
        self.page = None
        self.file = None
        self.user = None
        self.select_related = getattr(self, 'select_related', None)
        self.values = getattr(self, 'values', None)
        self.values_white_list = getattr(self, 'values_white_list', True)
        self.Qs = getattr(self, 'Qs', None)
        self.pk = None

    @classmethod
    def init_serializer(cls):
        if not hasattr(cls, 'serializer_class') or cls.serializer_class is None:
            if getattr(cls, 'primary_model', None) is None:
                cls.serializer_class = Serializer
            else:
                field_names = []
                for field in cls.primary_model._meta.get_fields():
                    if field.many_to_one or isinstance(field, (
                            django.db.models.fields.related.OneToOneField,
                            django.db.models.fields.related.ManyToManyField)):
                        field_name = getattr(field, 'name')
                    elif not field.is_relation:
                        field_name = getattr(field, 'attname')
                    else:
                        continue
                    if field_name not in (SETTINGS.MODEL_CREATOR, SETTINGS.MODEL_MODIFIER):
                        field_names.append(field_name)

                class BenchmarkSerializer(ModelSerializer):
                    class Meta:
                        model = cls.primary_model
                        fields = field_names
                cls.serializer_class = BenchmarkSerializer
            cls.serializer_is_custom = False
        else:
            cls.serializer_is_custom = True

    @classmethod
    def get_serializer(cls, *args, **kwargs):
        if not hasattr(cls, 'serializer_class') or cls.serializer_class is None:
            cls.init_serializer()
        return cls.serializer_class(*args, **kwargs)

    @classmethod
    def init_access(cls):
        cls.access = getattr(cls, 'access', {'get': 'all', 'post': 'all', 'put': 'all', 'delete': 'all'})
        for method in {'get', 'post', 'put', 'delete'} - set(cls.access.keys()):
            cls.access[method] = 'all'

    @classonlymethod
    def as_view(cls, actions=None, **initkwargs):
        cls.init()
        cls.list = cls.get
        cls.create = cls.post
        cls.retrieve = cls.get
        cls.update = cls.put
        cls.destroy = cls.delete
        if SETTINGS.PARENT_VIEW in ('ViewSet', 'ModelViewSet'):
            cls.init_serializer()
            if actions is None:
                has_pk = initkwargs.get('has_pk', False)
                actions = dict()
                if cls.access['get'] is not None:
                    if has_pk:
                        actions['get'] = 'retrieve'
                    else:
                        actions['get'] = 'list'
                if not has_pk and cls.access['post'] is not None:
                    actions['post'] = 'create'
                if has_pk and cls.access['put'] is not None:
                    actions['put'] = 'update'
                if has_pk and cls.access['delete'] is not None:
                    actions['delete'] = 'destroy'
            if not hasattr(cls, 'filter_class'):
                primary_model = getattr(cls, 'primary_model', None)
                if primary_model is not None:
                    class BenchmarkFilter(filters.FilterSet):
                        class Meta:
                            model = primary_model
                            fields = '__all__'
                    if cls.need_convert('request', 'get'):
                        for field in BenchmarkFilter.get_fields():
                            BenchmarkFilter.base_filters[cls.python_to_java(field, getattr(SETTINGS, 'OMIT_UNDERLINES', True))] \
                                = BenchmarkFilter.base_filters.pop(field)
                    cls.filter_class = BenchmarkFilter
            return super(BenchmarkAPIView, cls).as_view(actions=actions)
        else:
            return super(BenchmarkAPIView, cls).as_view(initkwargs=initkwargs)

    @staticmethod
    def get_response_by_code(code=SETTINGS.SUCCESS_CODE, msg=None, data=None, msg_append=None):
        return SETTINGS.GET_RESPONSE_BY_CODE(code, msg, data, msg_append)

    @staticmethod
    def get_http_response_by_code(code=SETTINGS.SUCCESS_CODE, msg=None, data=None):
        return SETTINGS.GET_HTTP_RESPONSE_BY_CODE(code, msg, data)

    # 检查请求字段是否存在
    def check_request_param_data(self):
        is_check_params = True
        for param_data, keys in zip((self.params, self.data), (self.check_params[self.method], self.check_data[self.method])):
            for key in keys:    # 必须存在的参数
                if isinstance(key, str):
                    if key not in param_data.keys():
                        return self.get_response_by_code(15 if is_check_params else 16 + SETTINGS.CODE_OFFSET, msg_append=key)
                else:    # 只需存在其中一个的参数组
                    found = False
                    for _key in key:
                        if _key in param_data.keys():
                            found = True
                            break
                    if not found:
                        return self.get_response_by_code(15 if is_check_params else 16 + SETTINGS.CODE_OFFSET, msg_append=key)
            is_check_params = False
        return self.get_response_by_code()

    # 提取请求 body 中的 data 或 json
    def get_request_data_json(self, request):
        if not hasattr(request, 'body'):
            return {}
        post_data = copy.deepcopy(self.data)
        try:
            res = json.loads(str(request.body, encoding='utf-8'))
        except json.decoder.JSONDecodeError:
            res = {key: value for key, value in post_data.items()}
        return res

    @staticmethod
    def get_uri_params(uri_params):
        if len(uri_params) == 0:
            return {}
        if len(uri_params) == 1:
            return {SETTINGS.MODEL_PRIMARY_KEY: uri_params[0]}
        raise Exception('too many uri params')

    # when using delete flag, you cannot define "unique_together" in models.
    # "unique_together" should be define in config.py.
    # "unique_together" function (detect for unique constraint) is processed here.
    @classmethod
    def check_unique_together(cls, data, pk=None):
        for field_names in cls.unique_together:
            unique_post_data = {}
            for field_name in field_names:
                has_unique_together_fields = False
                if field_name in data.keys():
                    has_unique_together_fields = True
                    unique_post_data[field_name] = data[field_name]
                else:
                    unique_together_field = getattr(cls.primary_model, field_name)
                    if hasattr(unique_together_field, 'field'):
                        unique_together_field = unique_together_field.field
                    unique_post_data[field_name] = unique_together_field.get_default()
                if hasattr(cls.primary_model, SETTINGS.MODEL_DELETE_FLAG):
                    unique_post_data[SETTINGS.MODEL_DELETE_FLAG] = 0
                if has_unique_together_fields:
                    query_set = cls.primary_model.objects.filter(**unique_post_data).using(cls.using)
                    if query_set.exists():
                        if pk is None:
                            return cls.get_response_by_code(5 + SETTINGS.CODE_OFFSET)
                        else:
                            for item in query_set:
                                if pk != item.pk:
                                    return cls.get_response_by_code(5 + SETTINGS.CODE_OFFSET)
        return cls.get_response_by_code()

    @classmethod
    def check_primary_model(cls, function_name):
        if cls.primary_model is None:
            raise ValueError('primary_model is None, you cannot use this default framework function: %s' % function_name)

    # get 请求对应的 model 操作，对请求 uri 对应的所有 model（支持所有字段）进行过滤操作后对 query set 按 get_data_method 函数进行取值
    def get_model(self):
        try:
            self.check_primary_model('get_model')
        except ValueError:
            return
        params = self.params
        params.update(self.uri_params)
        if self.only_enable_select_related_for_get_one and len(self.uri_params) == 0:
            select_related = None
        else:
            select_related = self.select_related
        res, self.count = self.primary_model.get_model(
            params=params, select_related=select_related, values=self.values,
            values_white_list=self.values_white_list, Qs=self.Qs, using=self.using,
            limit=self.limit, page=self.page, offset=self.offset, return_with_count=True
        )
        return res

    def get_redis_value(self, key, data_type='json', return_with_success_status=False):
        '''
        :param key: the key of redis data
        :param data_type: the values' type of redis data, choices are 'json', 'str', 'int', 'float', 'bool' or 'bytes'
        :param return_with_success_status: whether return the result of read redis success or not, True of False
        :return: the variable of redis data or the benchmark error json. if return_with_success_status is True, the
                 extra second returned variable show the whether the first returned variable is redis data.
        '''
        try:
            value = self.redis.get(key)
        except redis.exceptions.ConnectionError:
            if return_with_success_status:
                return self.get_response_by_code(28), False
            return self.get_response_by_code(28)
        if value is None:
            if return_with_success_status:
                return self.get_response_by_code(29), False
            return self.get_response_by_code(29)
        if data_type in ('json', 'str', 'int', 'float', 'bool'):
            try:
                value = bytes.decode(value)
                if data_type == 'json':
                    value = json.loads(value)
                elif data_type == 'int':
                    value = int(value)
                elif data_type == 'float':
                    value = float(value)
                elif data_type == 'bool':
                    if value.lower() == 'true':
                        value = True
                    elif value.lower() == 'false':
                        value = False
            except:
                if return_with_success_status:
                    return self.get_response_by_code(30), False
                return self.get_response_by_code(30)
        elif data_type != 'bytes':
            raise ValueError('the value of "data_type" is unknown, choices are "json", "str", "int", "float", "bool"" or "bytes"')
        if return_with_success_status:
            return value, True
        return value

    def set_redis_value(self, key, value, data_type='json', need_retry=False):
        '''
        :param key: the key of redis data
        :param key: the value of redis data
        :param data_type: the values' type of redis data, choices are 'json', 'str', 'int', 'float', 'bool' or 'bytes'
        :return: success or not.
        '''
        while True:
            try:
                self.redis.set(key, value)
            except Exception as e:
                if not need_retry:
                    return self.get_response_by_code(32, msg_append=str(e))
                print('set redis value failed, retrying...')
                time.sleep(5)
        return self.get_response_by_code()

    def serializer_check(self, data):
        if isinstance(data, dict):
            list_data = [data]
        elif isinstance(data, (list, tuple)):
            list_data = data
        else:
            raise Exception('data should be dict, list or tuple')
        self.data = []
        for data in list_data:
            if self.method in ('get', 'put'):
                partial = True
            else:
                partial = False
            if self.primary_model:
                serializer = self.get_serializer(self.primary_model.objects.filter(pk=self.pk).using(self.using).first(),
                                                 data=data, partial=partial)
            else:
                serializer = self.get_serializer(data=data, partial=partial)
            try:
                serializer.is_valid(raise_exception=True)
                self_data = OrderedDict()
                for key, value in serializer.validated_data.items():
                    if isinstance(value, Model):
                        self_data[key] = value.pk
                    else:
                        self_data[key] = value
                self.data.append(self_data)
            except rest_framework.exceptions.ValidationError as e:
                if self.serializer_use_benchmark_code:
                    dict_codes = e.get_codes()
                    if len(dict_codes) > 0:
                        _, codes = dict_codes.popitem()
                        if isinstance(codes, list) and len(codes) > 0:
                            code = codes[0]
                            if isinstance(code, int):
                                res = self.get_response_by_code(code)
                                if isinstance(res[SETTINGS.MSG], dict) and 'detail' not in res[SETTINGS.MSG]:
                                    res[SETTINGS.MSG]['detail'] = 'request parameters are not valid'
                                return res
                exception_detail = {}
                for key, errors in e.detail.items():
                    # partial 为 True 时, 令 required=True 不检查, 但对 get 和 pk 不存在的 put 请求无效, 暂时只能对捕获后的异常处理
                    if self.method in ('get', 'put'):
                        for error in errors:
                            if error == 'This field is required.':
                                errors.remove(error)
                    if len(errors) != 0:
                        exception_detail[key] = errors
                if len(exception_detail) > 0:
                    return self.get_response_by_code(20 + SETTINGS.CODE_OFFSET, data=exception_detail)
            except Exception as e:
                return self.get_response_by_code(1 + SETTINGS.CODE_OFFSET, msg=str(e))
        if len(self.data) == 1:
            self.data = self.data[0]
        return None

    # post 请求对应的 model 操作
    def post_model(self, data=None, return_with_inserted_data=False):
        try:
            self.check_primary_model('post_model')
        except ValueError:
            return
        post_data = copy.deepcopy(self.data)
        if data:
            if isinstance(post_data, dict):
                post_data.update(data)
            elif isinstance(post_data, (list, tuple)):
                for pd in post_data:
                    pd.update(data)
            else:
                raise Exception('data should be dict, list or tuple')
        if isinstance(post_data, dict):
            if SETTINGS.MODEL_PRIMARY_KEY in post_data.keys():
                if return_with_inserted_data:
                    return self.get_response_by_code(12 + SETTINGS.CODE_OFFSET), None
                return self.get_response_by_code(12 + SETTINGS.CODE_OFFSET)
        elif isinstance(post_data, (list, tuple)):
            for pd in post_data:
                if SETTINGS.MODEL_PRIMARY_KEY in pd.keys():
                    if return_with_inserted_data:
                        return self.get_response_by_code(12 + SETTINGS.CODE_OFFSET), None
                    return self.get_response_by_code(12 + SETTINGS.CODE_OFFSET)
        else:
            raise Exception('data should be dict, list or tuple')
        return self.primary_model.post_model(post_data, user=self.user.get_username(), using=self.using,
                                             serializer_is_custom=self.serializer_is_custom,
                                             return_with_inserted_data=return_with_inserted_data)

    def get_uri_params_data(self, data=None):
        post_data = copy.deepcopy(self.data)
        if data:
            post_data.update(data)
        post_data.update(self.uri_params)
        return post_data

    # put 请求对应的 model 操作，仅可对 primary_model 进行操作
    def put_model(self, data=None):
        try:
            self.check_primary_model('put_model')
        except ValueError:
            return
        post_data = self.get_uri_params_data(data)
        return self.primary_model.put_model(post_data, user=self.user.get_username(), using=self.using)

    # delete 请求对应的 model 操作
    def delete_model(self):
        try:
            self.check_primary_model('delete_model')
        except ValueError:
            return
        data = copy.deepcopy(self.data)
        data.update(self.uri_params)
        return self.primary_model.delete_model(data, user=self.user.get_username(), using=self.using)

    def check_access(self, pk=None):
        role = self.access[self.method]
        if role is None:    # no one can access
            return self.get_response_by_code(3 + SETTINGS.CODE_OFFSET)
        if getattr(django.conf.settings, 'DEBUG', False) and not SETTINGS.NEED_AUTHENTICATION_IN_DEBUG_MODE:
            return self.get_response_by_code()
        if not isinstance(role, (str, tuple, list)):
            raise Exception('The values of access items should be None, str, list or tuple')
        if isinstance(role, str):
            roles = [role]
        else:
            roles = role
        if 'all' in roles:    # every one can access
            return self.get_response_by_code()
        if not self.user.is_authenticated():
            return self.get_response_by_code(21 + SETTINGS.CODE_OFFSET)
        res = None
        if 'user' in roles and (res is None or res[SETTINGS.CODE] != SETTINGS.SUCCESS_CODE):    # login user can access
            res = self.get_response_by_code()
        if 'staff' in roles and (res is None or res[SETTINGS.CODE] != SETTINGS.SUCCESS_CODE):    # staff can access
            res = self.get_response_by_code() if self.user.is_staff else self.get_response_by_code(22 + SETTINGS.CODE_OFFSET)
        if 'superuser' in roles and (res is None or res[SETTINGS.CODE] != SETTINGS.SUCCESS_CODE):    # superuser can access
            res = self.get_response_by_code() if self.user.is_superuser else self.get_response_by_code(22 + SETTINGS.CODE_OFFSET)
        if 'right_authenticate' in roles and (res is None or res[SETTINGS.CODE] != SETTINGS.SUCCESS_CODE):
            res = self.get_response_by_code() if self.right_authenticate() else self.get_response_by_code(22 + SETTINGS.CODE_OFFSET)
        if 'creator' in roles and (res is None or res[SETTINGS.CODE] != SETTINGS.SUCCESS_CODE):    # creator or admin can access put or delete method
            if SETTINGS.MODEL_CREATOR not in self.primary_model._meta.get_fields():
                raise Exception('primary model %s has no field %s' % (self.primary_model.__name__, SETTINGS.MODEL_CREATOR))
            if pk is None:
                res = self.get_response_by_code(2 + SETTINGS.CODE_OFFSET)
            if not isinstance(pk, (list, tuple)):
                pk = [pk]
            if SETTINGS.MODEL_DELETE_FLAG is None:
                query_set = self.primary_model.objects.filter(pk__in=pk).using(self.using)
                if query_set.count == 0:
                    res = self.get_response_by_code(6 + SETTINGS.CODE_OFFSET)
            else:
                query_set = self.primary_model.objects.filter(**{'pk__in': pk, SETTINGS.MODEL_DELETE_FLAG: 0}).using(self.using)
                if query_set.count == 0:
                    res = self.get_response_by_code(7 + SETTINGS.CODE_OFFSET)
            not_creator_pks = []
            for item in query_set:
                creator = getattr(item, SETTINGS.MODEL_CREATOR, None)
                if not isinstance(creator, str):
                    creator = getattr(creator, 'username', None)
                if creator != self.user.username:
                    not_creator_pks.append(item.pk)
            if len(not_creator_pks) > 0:
                res = self.get_response_by_code(23 + SETTINGS.CODE_OFFSET, msg_append=', '.join(not_creator_pks))
        if res is not None and res[SETTINGS.CODE] == SETTINGS.SUCCESS_CODE:
            return res
        auth_func = getattr(SETTINGS, 'USER_RIGHT_AUTHENTICATE_FUNCTION', None)
        if not hasattr(auth_func, '__call__'):
            raise Exception('Unknown access type %s, choices are None, "all", "user", "staff", "superuser", "creator", '
                            '"right_authenticate" or the values of USER_RIGHT_AUTHENTICATE_FUNCTION_PATH, '
                            'USER_RIGHT_AUTHENTICATE_FUNCTION is wrong.' % role)
        res = auth_func(self, roles)
        if res is True:
            return self.get_response_by_code()
        if res is False:
            return self.get_response_by_code(22)
        return res

    @staticmethod
    def string_to_bool(string):
        try:
            int_str = int(string)
            if int_str == 0:
                return False
            return True
        except:
            if string.lower() == 'true':
                return True
            if string.lower() == 'false':
                return False
            return None

    @staticmethod
    def java_to_python(string):
        new_string = ''
        for alphabet in string:
            if alphabet.isupper():
                new_string = new_string + '_' + alphabet.lower()
            else:
                new_string = new_string + alphabet
        return new_string

    def java_to_python_keys(self):
        if SETTINGS.CONVERT_KEYS and self.need_convert('request', self.method):
            for param_data in (self.uri_params, self.params, self.data):
                if isinstance(param_data, dict):
                    list_param_data = [param_data]
                elif isinstance(param_data, (tuple, list)):
                    list_param_data = param_data
                else:
                    raise Exception('data should be dict, list or tuple')
                for pd in list_param_data:
                    keys = list(pd.keys())
                    for key in keys:
                        if key in SETTINGS.KEYWORDS_WITH_VALUE_NEED_CONVERT:
                            value = pd[key]
                            if isinstance(value, list):
                                for i, v in enumerate(value):
                                    value[i] = self.java_to_python(v)
                            else:
                                pd[key] = self.java_to_python(value)
                        else:
                            pd[self.java_to_python(key)] = pd.pop(key)
            if self.method == 'get' and SETTINGS.ORDER_BY in self.params:
                self.params[SETTINGS.ORDER_BY] = self.java_to_python(self.params[SETTINGS.ORDER_BY])

    # rename input keys in http request
    def rename_input_keys(self):
        for str_input in ('uri_params', 'params', 'data'):
            input = getattr(self, str_input)
            if isinstance(input, dict):
                list_input = [input]
            else:
                list_input = input
            for _input in list_input:
                rename_dict = getattr(self, 'rename_' + str_input)
                for key, new_key in rename_dict.items():
                    _input[new_key] = _input.pop(key)

    # If the view define the filed names of request or response need not convert between styles of java and python by
    # the class variables that methods_not_need_convert_keys_for_request or methods_not_need_convert_keys_for_response,
    # it return False. And the view will not convert the field names, although SETTINGS.CONVERT_KEYS is True.
    @classmethod
    def need_convert(cls, request_response, method):
        str_not_convert = 'methods_not_need_convert_keys_for_' + request_response
        not_convert = getattr(cls, str_not_convert, None)
        if not_convert is None:
            return True
        if isinstance(not_convert, str):
            not_convert = [not_convert]
        elif not isinstance(not_convert, (tuple, list)):
            raise Exception('the value of ' + str_not_convert + 'should be list or tuple or str')
        return method not in not_convert

    @staticmethod
    def python_to_java(string, omit_underlines=True):
        new_string = ''
        to_upper = False
        for i, alphabet in enumerate(string):
            if to_upper:
                if omit_underlines and alphabet == '_':
                    continue
                if alphabet.islower():
                    new_string = new_string + alphabet.upper()
                else:
                    new_string = new_string + alphabet
                to_upper = False
            elif alphabet == '_':
                if i + 1 < len(string):
                    if string[i + 1] == '_':
                        if omit_underlines:
                            to_upper = True
                        else:
                            new_string = new_string + alphabet
                        continue
                if i - 1 > 0:
                    if string[i - 1] == '_':
                        if omit_underlines:
                            to_upper = True
                        else:
                            new_string = new_string + alphabet
                        continue
                to_upper = True
            else:
                new_string = new_string + alphabet
        return new_string

    @staticmethod
    def python_to_java_keys(res, omit_underlines):
        stack = [res]
        while len(stack) > 0:
            data = stack.pop()
            if isinstance(data, dict):
                keys = list(data.keys())
                for key in keys:
                    if isinstance(data[key], (dict, list)):
                        stack.append(data[key])
                    new_key = BenchmarkAPIView.python_to_java(key, omit_underlines)
                    if key != new_key:
                        data[new_key] = data.pop(key)
            elif isinstance(data, list):
                for item in data:
                    stack.append(item)

    def json_to_string_keys(self):
        if isinstance(self.data, dict):
            post_data = [self.data]
        elif isinstance(self.data, (list, tuple)):
            post_data = self.data
        else:
            raise Exception('data should be dict, list or tuple')
        for data in post_data:
            keys = list(data.keys())
            for key in keys:
                if key in SETTINGS.MODEL_JSON_FIELD_NAMES:
                    data[key] = json.dumps(data[key])

    def process_keys(self, res, path=None, has_result_field=False):
        if has_result_field:
            values_fields = self.values_fields_in_data_results
            rename_fields = self.rename_fields_in_data_results
        else:
            values_fields = self.values_fields_in_data
            rename_fields = self.rename_fields_in_data
        if SETTINGS.CONVERT_KEYS and self.need_convert('response', self.method):
            need_python_to_java = True
        else:
            need_python_to_java = False
        stack = [(res, path)]
        while len(stack) > 0:
            node, node_path = stack.pop()
            if isinstance(node, list):
                for item in node:
                    stack.append((item, node_path))
            elif isinstance(node, dict):
                keys = list(node.keys())
                for key in keys:
                    if isinstance(node[key], (dict, list)):
                        if node_path is None:
                            stack.append((node[key], None))
                        else:
                            stack.append((node[key], node_path + key + '/'))
                    if node_path in values_fields and (
                            (self.values_white_list and key not in values_fields[node_path]) or
                            (not self.values_white_list and key in values_fields[node_path])
                    ):
                        del node[key]
                    else:
                        if node_path in rename_fields and key in rename_fields[node_path]:
                            new_key = rename_fields[node_path][key]
                            node[new_key] = node.pop(key)
                            key = new_key
                        if need_python_to_java:
                            new_key = self.python_to_java(key, self.omit_underlines)
                            if key != new_key:
                                node[new_key] = node.pop(key)

    # 处理各种请求的入口，解析各字段并进行处理
    def begin(self, request, uri_params={}):
        self.request = request
        self.user = request.user
        self.host = request.get_host()
        self.path = request.path
        self.method = request.method.lower()
        self.file = request.FILES.get(SETTINGS.FILE, None)
        self.params = {}
        for key, value in request.GET.items():
            len_value = len(value)
            if len_value >= 2 and value[0] == '[' and value[len_value - 1] == ']':
                value = value[1:-1].split(',')
            elif key == SETTINGS.VALUES and len_value > 3 and value[:2] == '-[' and value[len_value - 1] == ']':
                self.values_white_list = False
                value = value[2:-1].split(',')
            elif key == SETTINGS.VALUES and len_value > 2 and value[0] == '-':
                self.values_white_list = False
                value = value[1:].split(',')
            if key == SETTINGS.VALUES:
                if isinstance(value, str):
                    value = [value]
                self.values = value
            elif key == SETTINGS.Q:
                if not isinstance(value, list):
                    value = [value]
                self.Qs = []
                for several_q in value:
                    list_q = several_q.split(SETTINGS.Q_OR)
                    _several_q = []
                    for q in list_q:
                        _q = {}
                        list_param_value = q.split(SETTINGS.Q_AND)
                        for param_value in list_param_value:
                            param_name, param_value = param_value.split('=')
                            _q[param_name] = param_value
                        _several_q.append(_q)
                    self.Qs.append(_several_q)
            else:
                if key in self.bool_params:
                    value = self.string_to_bool(value)
                    if value is None:
                        return self.get_response_by_code(27 + SETTINGS.CODE_OFFSET)
                self.params[key] = value
        self.uri_params = uri_params
        if self.method == 'get':
            self.limit = self.params.pop(SETTINGS.LIMIT, None)
            self.page = self.params.pop(SETTINGS.PAGE, None)
            self.offset = self.params.pop(SETTINGS.OFFSET, None)
            try:
                self.limit = int(self.limit)
            except:
                self.limit = 0
            if self.limit < 0:
                self.limit = 0
            try:
                self.page = int(self.page)
            except:
                self.page = 1
            if self.page < 1:
                self.page = 1
            try:
                self.offset = int(self.offset)
            except:
                self.offset = 0
            if self.offset < 0:
                self.offset = 0
        elif self.method in ('post', 'put', 'delete'):
            request_data = copy.deepcopy(request.data)
            if isinstance(request_data, dict):
                self.data = {}
                try:
                    for key, value in request_data.lists():
                        if len(value) == 1:
                            self.data[key] = value[0]
                        else:
                            self.data[key] = value
                except:
                    for key, value in request_data.items():
                        self.data[key] = value
            elif self.method == 'post' and isinstance(request_data, (list, tuple)):
                self.data = []
                for one_request_data in request_data:
                    one_data = {}
                    try:
                        for key, value in one_request_data.lists():
                            if len(value) == 1:
                                one_data[key] = value[0]
                            else:
                                one_data[key] = value
                    except:
                        for key, value in one_request_data.items():
                            one_data[key] = value
                    self.data.append(one_data)
            elif self.method == 'delete' and isinstance(request_data, (list, tuple)):
                self.data = {'pk': request_data}
            else:
                self.get_response_by_code(25 + SETTINGS.CODE_OFFSET)
        res = self.check_request_param_data()
        if res[SETTINGS.CODE] != SETTINGS.SUCCESS_CODE:
            return res
        pk = None
        if self.method in ('get', 'put', 'delete'):
            pk = self.uri_params.get('pk')
            if pk is None and isinstance(self.data, dict):
                pk = self.data.get('pk')
            if self.method in ('put', 'delete') and pk is None:
                return self.get_response_by_code(2 + SETTINGS.CODE_OFFSET)
            self.pk = pk
        res = self.check_access(pk=pk)
        if res[SETTINGS.CODE] != SETTINGS.SUCCESS_CODE:
            return res
        self.java_to_python_keys()
        self.rename_input_keys()
        self.json_to_string_keys()
        if self.method in ('post', 'put') or (self.method == 'get' and self.http_get_check_params):
            if self.method == 'get':
                data = self.params
            else:
                data = self.data
            res = self.serializer_check(data)
            if res is not None:
                return res
        if self.params.get(SETTINGS.SELECT_RELATED):
            select_related = self.params.pop(SETTINGS.SELECT_RELATED)
            if self.enable_select_related_in_params:
                if isinstance(select_related, str):
                    select_related = [select_related]
                if self.enabled_select_related_in_params == '__all__':
                    self.select_related = select_related
                else:
                    self.select_related = list(
                        set(self.enabled_select_related_in_params) & set(getattr(self.params, SETTINGS.SELECT_RELATED, []))
                    )
        return self.get_response_by_code()

    # 处理各种类型的返回
    def process_response(self, res):
        data = res.get(SETTINGS.DATA, None)
        if isinstance(res, dict):    # dict 转 json 返回
            if SETTINGS.DATA_STYLE == 'dict':
                if data is not None:
                    if isinstance(res[SETTINGS.DATA], (list, dict)) and len(res[SETTINGS.DATA]) == 0:
                        res[SETTINGS.DATA] = None
                    elif isinstance(res[SETTINGS.DATA], list):
                        res[SETTINGS.DATA] = {
                            SETTINGS.RESULT: res[SETTINGS.DATA],
                            SETTINGS.COUNT: len(res[SETTINGS.DATA])
                        }
                    elif isinstance(res[SETTINGS.DATA].get(SETTINGS.RESULT, None), (list, dict)) and len(res[SETTINGS.DATA][SETTINGS.RESULT]) == 0:
                        res[SETTINGS.DATA][SETTINGS.RESULT] = None
            if data is not None and len(data) > 0:
                if self.method == 'get':
                    path = '/'
                    if SETTINGS.RESULT in res[SETTINGS.DATA]:
                        has_result_field = True
                    else:
                        has_result_field = False
                else:
                    path = None
                    has_result_field = None
                self.process_keys(res, path, has_result_field)

            # additional data
            additional_data = getattr(self, 'additional_data', None)
            if isinstance(additional_data, dict):
                for key, value in additional_data.items():
                    res[SETTINGS.DATA][self.python_to_java(key, self.omit_underlines)] = value

            # process json response class
            json_response_class = getattr(SETTINGS, 'JSON_RESPONSE_CLASS', None)
            if json_response_class == 'rest_framework.response.Response':
                res = Response(res)
            elif json_response_class == 'django.http.JsonResponse':
                res = JsonResponse(res, json_dumps_params={"indent": 2})
            else:
                raise Exception('JSON_RESPONSE_CLASS in the benchmark_settings is not defined or not correct. The value of it should be "rest_framework.response.Response", or "django.http.JsonResponse"')
        if isinstance(res, (StreamingHttpResponse, django.http.response.HttpResponse)):    # 流文件, 或已处理好的 http 响应
            return res
        raise Exception('unknown response type: %s' % type(res))

    # 处理 style 2 的 get 请求分页
    def paginate(self, res):
        if res[SETTINGS.CODE] == SETTINGS.SUCCESS_CODE and SETTINGS.DATA_STYLE == 'dict':
            if isinstance(res[SETTINGS.DATA], dict):
                res[SETTINGS.DATA] = [res[SETTINGS.DATA]]
            # get one
            if self.get_one is None and 'pk' in self.uri_params.keys() or self.get_one:
                if len(res[SETTINGS.DATA]) == 0:
                    res[SETTINGS.DATA] = None
                else:
                    res[SETTINGS.DATA] = res[SETTINGS.DATA][0]
            # get many in pages
            elif self.page is not None:
                if self.limit == 0:
                    page_count = 0 if self.count == 0 else 1
                else:
                    page_count = math.ceil(self.count / self.limit)
                if 1 <= self.page <= page_count:
                    result = res[SETTINGS.DATA]
                else:
                    result = None
                if self.page < 1:
                    self.page = 0
                elif self.page > page_count:
                    self.page = page_count + 1
                basic_url = 'http://' + self.host + self.path
                previous_param_url = None
                next_param_url = None
                params = copy.deepcopy(self.params)
                params[SETTINGS.LIMIT] = self.limit
                params[SETTINGS.PAGE] = self.page
                if self.page <= 1:
                    previous_url = None
                else:
                    for key, value in params.items():
                        if key == 'page':
                            value = str(self.page - 1)
                        if previous_param_url is None:
                            previous_param_url = '?' + key + '=' + str(value)
                        else:
                            previous_param_url += '&' + key + '=' + str(value)
                    previous_url = basic_url + previous_param_url
                if self.page >= page_count:
                    next_url = None
                else:
                    for key, value in params.items():
                        if key == 'page':
                            value = str(self.page + 1)
                        if next_param_url is None:
                            next_param_url = '?' + key + '=' + str(value)
                        else:
                            next_param_url += '&' + key + '=' + str(value)
                    next_url = basic_url + next_param_url
                res[SETTINGS.DATA] = {SETTINGS.RESULT: result, SETTINGS.COUNT: self.count,
                                      SETTINGS.NEXT: next_url, SETTINGS.PREVIOUS: previous_url}
            # get many not in pages
            else:
                res[SETTINGS.DATA] = {SETTINGS.RESULT: res[SETTINGS.DATA], SETTINGS.COUNT: len(res[SETTINGS.DATA])}

    # 处理 get 请求
    def get(self, request, **uri_params):
        res = self.begin(request, uri_params)
        if res[SETTINGS.CODE] == SETTINGS.SUCCESS_CODE:
            if hasattr(self, 'get_redis'):
                res = self.get_redis()
                if not isinstance(res, dict):
                    res = self.get_response_by_code(31)
            else:
                res = self.get_model()
        if res is None:    # when haven't any difinitions (get_model() or primary_model) for benchmark view, use the process in drf view.
            if SETTINGS.PARENT_VIEW == 'ApiView':
                return super(BenchmarkAPIView, self).get(request)
            if self.pk is None:
                return super(BenchmarkAPIView, self).list(request)
            return super(BenchmarkAPIView, self).retrieve(request, pk=self.pk)
        if isinstance(res, dict) and SETTINGS.CODE in res.keys() and res[SETTINGS.CODE] == SETTINGS.SUCCESS_CODE:
            self.paginate(res)
        return self.process_response(res)

    # 处理 post 请求
    def post(self, request, **uri_params):
        res = self.begin(request, uri_params)
        if res[SETTINGS.CODE] == SETTINGS.SUCCESS_CODE:
            res = self.post_model()
        if res is None:    # when haven't any difinitions (post_model() or primary_model) for benchmark view, use the process in drf view.
            if SETTINGS.PARENT_VIEW == 'ApiView':
                return super(BenchmarkAPIView, self).post(request)
            return super(BenchmarkAPIView, self).create(request)
        return self.process_response(res)

    # 处理 put 请求
    def put(self, request, **uri_params):
        res = self.begin(request, uri_params)
        if res[SETTINGS.CODE] == SETTINGS.SUCCESS_CODE:
            res = self.put_model()
        if res is None:    # when haven't any difinitions (put_model() or primary_model) for benchmark view, use the process in drf view.
            if SETTINGS.PARENT_VIEW == 'ApiView':
                return super(BenchmarkAPIView, self).put(request)
            return super(BenchmarkAPIView, self).update(request)
        return self.process_response(res)

    # 处理 delete 请求
    def delete(self, request, **uri_params):
        res = self.begin(request, uri_params)
        if res[SETTINGS.CODE] == SETTINGS.SUCCESS_CODE:
            res = self.delete_model()
        if res is None:    # when haven't any difinitions (delete_model() or primary_model) for benchmark view, use the process in drf view.
            if SETTINGS.PARENT_VIEW == 'ApiView':
                return super(BenchmarkAPIView, self).delete(request)
            return super(BenchmarkAPIView, self).destroy(request)
        return self.process_response(res)
