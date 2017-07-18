# -*- coding:utf-8 -*-

from django.http import JsonResponse
import copy


# The http response json data field names, you can modify them to fit in with your web site.
CODE = 'code'      # the error code field name
SUCCESS_CODE = 0   # the only one success code value
CODE_OFFSET = 0    # the offset of error codes defined by this framework
MSG = 'msg'        # the error message field name
DATA = 'data'      # the data field name
CREATED_COUNT = 'created_count'    # the field name of batch insert success count when data of http post request is a list
DELETED_COUNT = 'deleted_count'    # the field name of batch delete success count when data of http delete request is a list
CREATED_ITEMS = 'created'    # the field name of batch insert succeeded items
DELETED_PKS = 'deleted'    # the field name of the primary keys of batch delete succeeded items
FAILED_ITEMS = 'failed'    # the field name of batch insert or delete failed items
TOTAL_COUNT = 'total_count'    # the field name of batch insert or delete total count in request

# DATA_STYLE is the style of DATA field for http get response.
# If DATA_STYLE is "list": DATA is a list including every model instances of the filter result for the models in dict format.
# If DATA_STYLE is "dict":
#     1. When the primary key of the primary_model is in the request uri parameter, DATA is a dict for the only one
#        filter result for the models. If the data with this primary key doesn't exist, DATA is null.
#     2. In the other situation, DATA a dict which has a RESULT field. The value of the RESULT field is a list including
#        every model instances of the filter result for the models in dict format, same as when DATA_STYLE is "list".
#        Additionally, the DATA include COUNT, NEXT, PREVIOUS fields. See the comments of these 3 fields for more detail
#        information.
DATA_STYLE = 'dict'
RESULT = 'result'
COUNT = 'count'    # the count of items in result list
# If OFFSET and PAGE are in request parameters, the value of NEXT is the next page url.
# Otherwise or no next page, the value is null.
NEXT = 'next'
# If OFFSET and PAGE are in request parameters, the value of PREVIOUS is the previous page url.
# Otherwise or no previous page, the value is null.
PREVIOUS = 'previous'

# The type of http json response, choices are "rest_framework.response.Response" or "django.http.JsonResponse"
JSON_RESPONSE_CLASS = 'django.http.JsonResponse'

# The http response json format
# The error codes which smaller than 200 before added by CODE_OFFSET is defined by the framework.
# It's not recommended to define the error codes by the any web site itself.
# http 响应的 json 格式配置
# 未增加 CODE_OFFSET 偏移量的小于200的错误状态码，用于该框架的保留错误码
# 不能被网站自定义
DICT_RESPONSE_BY_CODE = {
    str(SUCCESS_CODE): {CODE: SUCCESS_CODE, MSG: 'success'},
    '1': {MSG: 'raise exception'},    # the msg should be replaced by the except reason
    '2': {MSG: 'request parameters should include "pk" as the primary key for the primary model of the uri'},
    '3': {MSG: 'this api does not support this http method'},
    '4': {MSG: 'insert failed: the model has the data with the same primary key as the post data'},
    '5': {MSG: 'insert failed: one of the relationship keys is already deleted by delete flag'},    # only happend when MODEL_DELETE_FLAG is not None
    '6': {MSG: 'update or delete failed: the data does not exist'},
    '7': {MSG: 'update or delete failed: the data exist, but is already deleted by delete flag'},    # only happend when MODEL_DELETE_FLAG is not None
    '8': {MSG: 'insert failed: the foreign key (%s = %s) is already deleted by delete flag'},    # only happend when MODEL_DELETE_FLAG is not None
    '9': {MSG: 'insert failed: the foreign key (%s = %s) is not exist'},
    '10': {MSG: 'update failed: the value of the request data %s cannot be list'},
    '11': {MSG: 'deleted, but some foreign key has already deleted by delete flag'},    # only happend when MODEL_DELETE_FLAG is not None
    '12': {MSG: 'insert failed: the post request cannot contains "pk" parameter'},
    '13': {MSG: 'batch insert by values of fields in request data in list failed: the post request should has some legal request data'},
    '14': {MSG: 'invalid select_related field: '},
    '15': {MSG: 'request parameter does not exist: '},
    '16': {MSG: 'request data in body does not exist: '},
    '17': {MSG: 'the format of date time string in request parameter is not correct, it should like "2017-03-24 20:05:39"'},
    '18': {MSG: 'the format of date string in request parameter is not correct, it should like "2017-03-24"'},
    '19': {MSG: 'the format of time string in request parameter is not correct, it should like "20:05:39"'},
    '20': {MSG: 'request parameters are not valid'},
    '21': {MSG: 'anonymous user cannot access this api, should login first'},
    '22': {MSG: 'user haven\'t the right to access this api'},
    '23': {MSG: 'user is not the creator of the data with primary key: '},
    '24': {MSG: 'the name of request parameter is not correct: '},
    '25': {MSG: 'request data in http body should be dict, if http method is post, dicts in list is also applied'},
    '26': {MSG: 'batch delete failed, the reasons are: '},
    '100': {MSG: 'login failed'},
}

for _code, _res in DICT_RESPONSE_BY_CODE.items():
    if int(_code) < 200:
        _res[CODE] = int(_code) + CODE_OFFSET
    else:
        _res[CODE] = int(_code)


def GET_RESPONSE_BY_CODE(code=SUCCESS_CODE, msg=None, data=None, msg_append=None):
    if code == SUCCESS_CODE:
        res = copy.deepcopy(DICT_RESPONSE_BY_CODE[str(SUCCESS_CODE)])
    else:
        res = copy.deepcopy(DICT_RESPONSE_BY_CODE[str(code)])
    if msg:
        if isinstance(msg, str):
            res[MSG] = msg
        elif isinstance(msg, tuple) or isinstance(msg, list):
            res[MSG] = res[MSG] % msg
    if msg_append:
        res[MSG] += msg_append
    if data:
        res[DATA] = data
    else:
        res[DATA] = []
    return res


def GET_HTTP_RESPONSE_BY_CODE(code=SUCCESS_CODE, msg=None, data=None):
    return JsonResponse(GET_RESPONSE_BY_CODE(code, msg, data), json_dumps_params={"indent": 2})


# The parent class which BenchmarkAPIView extends from. Choice is "APIView", "GenericAPIView" or "ViewSet".
PARENT_VIEW = 'ViewSet'

# The params (in urls) should be exist of http requests.
DICT_CHECK_PARAMS = {
    # # The format is as follow, view names, http methods, field names, for example:
    # 'CompanyView': {
    #     'get': ('company_name', ),
    # }
}

# The data (in request bodies) should be exist of http requests.
DICT_CHECK_DATA = {
    # # The format is as follow, view names, http methods, field names, for example:
    # 'CompanyView': {
    #     'post': ('company_id', 'company_name'),
    # }
}

# The not supported methods of the APIs
DICT_VIEW_NOT_SUPPORT_METHODS = {
    # # The format is as follow, view names, http methods, for example:
    # 'CompanyView': ('delete', ),
}

# The keyword of relation field names in models for searching multiple models in http get requests.
# If one request has several related field branches, list them in a list.
SELECT_RELATED = 'select_related'

# The keyword for filter the http get response data fields. If one request has several model field names to filter,
# list them in a list. If the request need a black list for filter (default is white list), add "-" in the front of
# the value of this parameter.
VALUES = 'values'

# The keyword of the begin position of http get response data.
# It usually used with LIMIT keyword, for limit the number of the search result data.
# The minimal value of OFFSET is 1. If the value of OFFSET is not correct, set it to 1.
# If the value of OFFSET is bigger than the number of total result data, return an empty list.
OFFSET = 'offset'

# The keyword of the maximum number of http get response data.
# It usually used with OFFSET or PAGE keyword, for limit the number of the search result data.
# The minimal value of LIMIT is 1. If the value of LIMIT is not correct, return all list.
LIMIT = 'limit'

# The keyword of the page number of http get response data.
# It usually used with LIMIT keyword, for limit the number of the search result data.
# If OFFSET and PAGE keywords are both appear in the parameters, omit the OFFSET.
# The range of PAGE value is between 1 and ⌈COUNT/PAGE⌉.
# If the value of page is bigger than ⌈COUNT/PAGE⌉, the RESULT set to null.
# If the value of PAGE is not correct number, set it to 1.
PAGE = 'page'

# The keyword of http get requests for the data order.
ORDER_BY = 'order_by'

# The keyword of django Q object for http get request to filter model.
# For example, /employee?Q=[employee_name=EmployeeAX1$employee_id=1|employee_name=EmployeeAX2$employee_id=2,
# department=1$employee_id=1|department=4$employee_id=8] is same as filter model:
# Employee.objects.filter(Q(employee_name=EmployeeAX1, employee_id=1) | Q(employee_name=EmployeeAX2, employee_id=2),
# Q(department=1, employee_id=1) | Q(department=4, employee_id=8))
Q = 'Q'

# The keyword of "or" splitter for several django Q objects.
Q_OR = '|'

# The keyword of "and" splitter in one django Q object.
# You cannot use "&" because it is the splitter for several parameters in http get request.
# And you cannot use "," because it is the splitter of elements in the list in http get request by this framework.
Q_AND = '$'

# The keyword the parameter name of upload file in http request body.
FILE = 'file'

# The class variable name of sub-class of BenchmarkApiView for using django multiple databases.
# The choice of value of this variable can be the DATABASES.keys() defined in django "settings.py" file.
USING = 'using'

# The class variable name of sub-class of BenchmarkApiView for api access authorization.
# The value of this variable is a dict as follow:
# {'get': 'all', 'post': 'user', 'put': 'staff', 'delete': None}
# The choice of the keys in this dict are the 4 http methods: get, post, put and delete.
# The choice of the values of this dict are as follow:
# None: the api does not support the http method of the api.
# 'all': everyone, including without login, can access the http method of the api.
# 'user': every login users can access the http method of the api.
# 'staff': every staffs or superusers can access the http method of the api.
# 'superuser': every superusers can access the http method of the api.
# 'creator': every creators and superusers can access the http method (put or delete) of the api.
#            the creator is defined in the primary_model and set to request.user.username in post method.
#            so the post method of the same api should be 'user', 'staff' or 'superuser'.
#            and the variable name of the creator in all models is defined in MODEL_CREATOR.
# each undefined access of method
ACCESS = 'access'

# Custom function for user right authentication.
# The function should be static method, class method of a class in the file, or just a function not in any class.
# The inputs of the function are user and role. And the outputs of it are True, False or the return value from
# get_response_by_code function in BenchmarkApiView.
USER_RIGHT_AUTHENTICATE_FUNCTION = None

# The keyword of django model primary key.
MODEL_PRIMARY_KEY = 'pk'

# The configuration of whether use MODEL_PRIMARY_KEY when http post method (True),
# or use the primary key name of models.
USE_MODEL_PRIMARY_KEY = False

# When some models use delete flag, the http delete requests don't delete the items of models, but they set the
# delete flag to "True" value. And we should set the delete flag name of the fields as the value of MODEL_DELETE_FLAG.
# If we don't use the delete flag in every models, we just set the value of MODEL_DELETE_FLAG "None".
# 是否使用删除标记位(delete请求不删除数据库表中数据, 而是修改标记位字段). 若使用, 则为删除标记位字段名;
# 若不使用, 则为 None; 可以支持部分 model 使用删除标记位, 其余 model 不使用
MODEL_DELETE_FLAG = None             # 'delete flag'

# The name of the fields in models which defined as "models.DateTimeField(auto_now_add=True)"
# If haven't these fields, to set the value "None".
# model 创建字段, 若没有该字段可以为 None
MODEL_CREATE_TIME = 'create_time'

# The name of the fields in models which defined as "models.DateTimeField(auto_now=True)".
# If haven't these fields, to set the value "None".
# model 修改字段, 若没有该字段可以为 None
MODEL_MODIFY_TIME = 'modify_time'

# The name of the fields in models which define the creator of the items in models, when the views of the models should
# login first. The framework can set the creator field when the items are added by http post method.
# If the models haven't these fields, we can just set the value "None".
# model 创建者字段, 若没有该字段可以为 None
MODEL_CREATOR = 'creator'

# The name of the fields in models which define the last modifier of the items in models, when the views of the models
# should login first. The framework can reset the modifier field when the items are added by http post method or
# modified by http put method.
# If the models haven't these fields, we can just set the value "None".
# model 修改者字段, 若没有该字段可以为 None
MODEL_MODIFIER = 'modifier'

# If MODEL_DELETE_FLAG is not None, we cannot use many to many relation in model defination. We can define them
# manually, and list their names in the tuple. The framework can maintain the relations when http get/post/put/delete.
# 若 model 使用删除标记位, 多对多表不能由 django 本身维护, 该框架可以提供支持, 需要指定多对多表名
# TODO: developing
MANY_TO_MANY_RELATION_MODEL_NAMES = (
    # # For example:
    # 'ProjectTeamToEmployee',
)

# If MODEL_DELETE_FLAG is not None, we cannot use "unique_together" in models. And we should list these unique
# restrictions. The framework can maintain the unique restrictions.
# 若 model 使用删除标记位, 无法使用唯一性约束, 需要定义唯一性约束的字段
DICT_MODEL_UNIQUE_TOGETHER = {
    # # For example, model name, fields in tuples just as they defined in "unique_together":
    # 'Company': (('company_name', ), ),
}

# If we have some fields of the models store the json string, we can list in this tuple, these json can be resolved as
# the correct format in http get response.
# 若有 model 字段实际存储的是 json 串, 在此需要列出这些字段名, 以在 get 请求返回时候, 解析正确
MODEL_JSON_FIELD_NAMES = (
    # # For example:
    'employee_info',
)

# The configuration of whether omit un-editable fields from models in the http get response. The default value is False.
OMIT_UN_EDITABLE_FIELDS = False

# The configuration of whether to transform keys of the params or data of the request or response
# between the style of python and java.
# For example, convert employeeName to employee_name after BenchmarkApiView receive request.
# Conversely, convert employee_name to employeeName before BenchmarkApiView return response.
CONVERT_KEYS = True

# If DEBUG is True in settings.py, whether authentications for every APIs are needed.
NEED_AUTHENTICATION_IN_DEBUG_MODE = True

# keywords of http get request in benchmark_settings
KEYWORDS = {SELECT_RELATED, VALUES, OFFSET, LIMIT, PAGE, COUNT, ORDER_BY, Q, Q_OR, Q_AND}

# keywords of http get request in benchmark_settings which with value need to be converted
KEYWORDS_WITH_VALUE_NEED_CONVERT = {SELECT_RELATED, VALUES, ORDER_BY}
