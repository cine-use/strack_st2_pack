# coding=utf8
# Copyright (c) 2018 CineUse
import copy
import json
import logging
import urlparse
import requests

log = logging.getLogger("strack_api")

OPERATORS = {
                ">": "-gt",
                ">=": "-egt",
                "<": "-lt",
                "<=": "-elt",
                "=": "-eq",
                "==": "-eq",
                "!=": "-neq",
                "in": "-in",
                "not in": "-not-in",
                "like": "-lk",
                "not like": "-not-lk",
                "between": "-bw",
                "not between": "-not-bw"
            }


class Command(object):
    """
    command base class
    """
    cmd = None

    def __init__(self, server_object, module):
        """It's a Command...'"""
        self.__server = server_object
        self.__module = module
        self.__request = []

    @property
    def headers(self):
        return {'token': self.server.token, 'Content-Type': 'application/json'}

    @property
    def url(self):
        module_uri = self.module.get('code')
        if self.module.get('type') == 'entity':
            module_uri = 'entity'
        if '_' in module_uri:
            new_module_uri = ''
            for i, uri_part in enumerate(module_uri.split('_')):
                if i > 0:
                    uri_part = uri_part.capitalize()
                new_module_uri += uri_part
        else:
            new_module_uri = module_uri
        module_cmd = "%s/%s" % (new_module_uri, self.cmd)
        return self.__server.cmd_to_url(module_cmd)

    @property
    def server(self):
        return self.__server

    @property
    def module(self):
        return self.__module

    @property
    def request(self):
        return self.__request

    @property
    def parameters(self):
        # 命令所需的参数(参数名, 参数类型, 是否必填, 默认值)
        # should be [{'name': '', 'type': '', 'required': True, ''defaultValue'': '')]
        return []

    def __call__(self, *args, **kwargs):
        # 调用命令
        self.__request = (args, kwargs)
        payload = self._init_payload(args, kwargs)
        response = self._execute(payload)
        return self.__handle_response(response)

    def _init_payload(self, args, kwargs):
        # 初始化默认参数的值
        param_dict = copy.deepcopy(kwargs)
        param_dict.update({self.parameters[i].get('name'): v for i, v in enumerate(args)})
        param_dict = self._setup_params(param_dict)
        param_dict = self._format_params(param_dict)
        # self._validate_param(param_dict)
        return param_dict

    def _setup_params(self, param_dict):
        # 将参数组装成需要的格式
        param_dict = copy.deepcopy(param_dict)
        for parameter in self.parameters:
            name = parameter.get('name')
            if param_dict.get(name) is None:
                default_value = parameter.get('defaultValue')
                param_dict.update({name: default_value})
        param_dict.setdefault('module', {'code': self.module.get('code', ''), 'id': self.module.get('id', 0)})
        return param_dict

    def _format_params(self, param_dict):
        # 格式化参数
        result = copy.deepcopy(param_dict)
        return result

    def _validate_param(self, param_dict):
        # TODO: 验证参数是否正确
        type_map = {
            "list": list,
            "dict": dict,
            "str": basestring,
            "int": int,
            "float": float
        }
        for param_name, param_value in param_dict.items():
            if param_name not in self.parameters:
                raise ValueError("%s is not a validate argument." % param_name)
            param_type = filter(lambda x: x[0] == param_name, self.parameters)[0][1]
            if not isinstance(param_value, type_map.get(param_type)):
                raise ValueError(
                    "Argument '%s' must be a '%s' type object, not '%s'" % (param_name, param_type, type(param_value)))
        return True

    def _execute(self, payload):
        # 发送请求
        result = self.server.session.post(self.url, headers=self.headers, data=json.dumps(payload))
        return result

    def __handle_response(self, response):
        # 处理response
        if response.status_code == 200 and response.json().get('status') == 200:
            return self._success(response)
        else:
            return self.__failed(response)

    def _success(self, response):
        # 成功的结果
        res = response.json()
        result = res.get("data")
        format_result = self._format_result(result)
        return format_result

    def __failed(self, response):
        # 失败的结果
        if response.status_code == 500:
            error_info = "%s: %s" % (response.status_code, response.text)
        elif response.status_code not in [200, 500]:
            error_info = "%s: %s" % (response.status_code, response.json().get("message"))
        elif response.status_code == 200:
            error_info = "%s: %s" % (response.json().get('status'), response.json().get("message"))
        else:
            error_info = response.json()
        log.error(error_info)
        raise RuntimeError(error_info)

    def _format_result(self, result):
        # 格式化结果
        if not result:
            return {}
        new_result = copy.deepcopy(result)
        # add type
        new_result.update({"module": self.module})
        return new_result


class QueryCommand(Command):

    def _format_params(self, param_dict):
        result = super(QueryCommand, self)._format_params(param_dict)
        builtin_fields = self.server.fields(self.module.get('code'))
        # 格式化filter
        filter_param = result.get('filter')
        new_filter_param = {}
        for filter_item in filter_param:
            field = filter_item[0]
            module = self.module.get('code')
            if '.' in field:
                module = field.split('.')[0]
                field = field.split('.')[-1]
            operator = OPERATORS.get(filter_item[1], filter_item[1])
            values = filter_item[2]
            new_filter_param.setdefault(module, dict()).setdefault(field, [operator, values])
        result.update({'filter': new_filter_param})
        # 格式化fields
        fields_param = result.get('fields')
        new_fields_param = {}
        for field_item in fields_param:
            field = field_item
            module = self.module.get('code')
            if '.' in field:
                module = field.split('.')[0]
                field = field.split('.')[-1]
                new_fields_param.setdefault(module, list()).append(field)
            elif '.' not in field and field not in builtin_fields.keys():
                module = field
                new_fields_param.setdefault(module, [])
            else:
                new_fields_param.setdefault(module, list()).append(field)
        result.update({'fields': new_fields_param})
        # 格式化order
        order_param = result.get('order')
        new_order_param = {}
        for order_key, order_value in order_param.items():
            module = self.module.get('code')
            if '.' not in order_key:
                new_order_key = '%s.%s' % (module, order_key)
            else:
                new_order_key = order_key
            new_order_param.setdefault(new_order_key, order_value)
        result.update({'order': new_order_param})
        return result


class FindCommand(QueryCommand):

    cmd = 'find'

    @property
    def parameters(self):
        return [{'name': 'filter',
                 'type': 'list',
                 'required': True,
                 'defaultValue': []},
                {'name': 'fields',
                 'type': 'list',
                 'required': False,
                 'defaultValue': []},
                {'name': 'order',
                 'type': 'dict',
                 'required': False,
                 'defaultValue': {}},
                {'name': 'page',
                 'type': 'dict',
                 'required': False,
                 'defaultValue': {"page_number": 0,
                                  "page_size": 0}}
                ]

    def _format_result(self, result):
        if not result:
            return {}
        new_result = copy.deepcopy(result[0])
        # add type
        new_result.update({"module": self.module})
        return new_result


class SelectCommand(QueryCommand):

    cmd = 'select'

    @property
    def parameters(self):
        return [{'name': 'filter',
                 'type': 'list',
                 'required': True,
                 'defaultValue': []},
                {'name': 'fields',
                 'type': 'list',
                 'required': False,
                 'defaultValue': []},
                {'name': 'order',
                 'type': 'dict',
                 'required': False,
                 'defaultValue': {}},
                {'name': 'page',
                 'type': 'dict',
                 'required': False,
                 'defaultValue': {"page_number": 0,
                                  "page_size": 0}}
                ]

    def _format_result(self, result):
        def add_module(data):
            new_data = copy.deepcopy(data)
            new_data.setdefault('module', self.module)
            return new_data
        # add type
        new_result = map(lambda x: add_module(x), result.get('rows'))
        return new_result


class SummaryCommand(QueryCommand):

    cmd = 'select'

    @property
    def parameters(self):
        return [{'name': 'filter',
                 'type': 'list',
                 'required': True,
                 'defaultValue': []},
                {'name': 'fields',
                 'type': 'list',
                 'required': False,
                 'defaultValue': []},
                {'name': 'order',
                 'type': 'dict',
                 'required': False,
                 'defaultValue': {}},
                {'name': 'page',
                 'type': 'dict',
                 'required': False,
                 'defaultValue': {"page_number": 0,
                                  "page_size": 0}}
                ]

    def _format_result(self, result):
        new_result = result.get('total')
        return new_result


class CreateCommand(Command):

    cmd = 'create'

    @property
    def parameters(self):
        return [{'name': 'data',
                 'type': 'dict',
                 'required': True,
                 'defaultValue': None}
                ]

    def _format_params(self, param_dict):
        result = param_dict.get('data')
        result.setdefault('module', param_dict.get('module'))
        return result


class UpdateCommand(Command):

    cmd = 'update'

    @property
    def parameters(self):
        return [{'name': 'id',
                 'type': 'int',
                 'required': True,
                 'defaultValue': None},
                {'name': 'data',
                 'type': 'dict',
                 'required': True,
                 'defaultValue': None}
                ]

    def _format_params(self, param_dict):
        result = param_dict.get('data')
        result.setdefault('module', param_dict.get('module'))
        id_param = param_dict.get('id')
        result.update({'id': id_param})
        return result


class DeleteCommand(Command):

    cmd = 'delete'

    @property
    def parameters(self):
        return [{'name': 'id',
                 'type': 'int',
                 'required': True,
                 'defaultValue': None}
                ]

    def _format_result(self, result):
        return result


class UploadCommand(Command):

    cmd = 'upload'

    @property
    def parameters(self):
        return [{'name': 'file_path',
                 'type': 'str',
                 'required': True,
                 'defaultValue': None},
                {'name': 'server',
                 'type': 'dict',
                 'required': False,
                 'defaultValue': self.server.get_best_media_server()},
                ]

    def _execute(self, payload):
        media_server = payload.get('server')
        media_server_url = media_server.get('upload_url')
        media_server_token = media_server.get('token')
        upload_file = payload.get('file_path')
        if not upload_file:
            return None
        with open(upload_file, 'rb') as f:
            file_data = {'Filedata': f}
            result = requests.post(media_server_url, data={'token': media_server_token}, files=file_data)
            return result

    def _format_result(self, result):
        return result


class FieldsCommand(Command):

    cmd = 'fields'

    def _format_result(self, result):
        new_result = {}
        new_result.update(result.get("fixed_field"))
        new_result.update(result.get("custom_field"))
        return new_result


class RelationFieldsCommand(Command):

    cmd = 'fields'

    def _format_result(self, result):
        new_result = {}
        if result.get('relation'):
            new_result.update(result.get('relation'))
        return new_result


class RequireFeildsCommand(Command):

    cmd = 'fields'

    def _format_result(self, result):
        return result.get('require_field')


class TagCommand(Command):
    cmd = 'tag'

    @property
    def parameters(self):
        return [{'name': 'id',
                 'type': 'int',
                 'required': True,
                 'defaultValue': None},
                {'name': 'tag_id',
                 'type': 'int',
                 'required': True,
                 'defaultValue': None}
                ]

    def _format_params(self, param_dict):
        link_id = param_dict.get('id')
        tag_id = param_dict.get('tag_id')
        result = {'link_id': link_id, 'tag_id': tag_id, 'module': self.module}
        return result


class GetMemberDataCommand(Command):
    cmd = 'getMemberData'

    @property
    def parameters(self):
        return [{'name': 'user_id',
                 'type': 'int',
                 'required': True,
                 'defaultValue': None},
                {'name': 'module_id',
                 'type': 'int',
                 'required': True,
                 'defaultValue': None}
                ]

    def _format_params(self, param_dict):
        link_module_id = param_dict.get('module_id')
        user_id = param_dict.get('user_id')
        new_param = {'link_module_id': link_module_id, 'user_id': user_id}
        return new_param

    def _format_result(self, result):
        return result


class GetBrothersDirCommand(Command):
    cmd = 'getBrotherDirs'

    @property
    def parameters(self):
        return [{'name': 'id',
                 'type': 'int',
                 'required': True,
                 'defaultValue': None}
                ]

    def _format_result(self, result):
        return result


class GetChildrenDirCommand(Command):
    cmd = 'getChildren'

    @property
    def parameters(self):
        return [{'name': 'id',
                 'type': 'int',
                 'required': True,
                 'defaultValue': None}
                ]

    def _format_result(self, result):
        return result


class GetParentDirCommand(Command):
    cmd = 'getParentDir'

    @property
    def parameters(self):
        return [{'name': 'id',
                 'type': 'int',
                 'required': True,
                 'defaultValue': None}
                ]

    def _format_result(self, result):
        return result


class GetTemplatePathCommand(Command):
    cmd = 'getTemplatePath'

    @property
    def parameters(self):
        return [{'name': 'module',
                 'type': 'str',
                 'required': True,
                 'defaultValue': None},
                {'name': 'id',
                 'type': 'int',
                 'required': True,
                 'defaultValue': None},
                {'name': 'template_code',
                 'type': 'string',
                 'required': False,
                 'defaultValue': ""
                 }]

    def _format_params(self, param_dict):
        module_name = param_dict.get('module')
        module_info = filter(lambda x: x.get('code') == module_name, self.server.modules)[0]
        link_id = param_dict.get('id')
        code = param_dict.get('template_code')
        result = {'link_module_id': module_info.get('id'), 'link_id': link_id, 'code': code}
        return result

    def _format_result(self, result):
        return result


class GetItemPathCommand(Command):
    cmd = 'getItemPath'

    @property
    def parameters(self):
        return [{'name': 'module',
                 'type': 'str',
                 'required': True,
                 'defaultValue': None},
                {'name': 'id',
                 'type': 'int',
                 'required': True,
                 'defaultValue': None},
                {'name': 'template_code',
                 'type': 'string',
                 'required': False,
                 'defaultValue': ""
                }]

    def _format_params(self, param_dict):
        module_name = param_dict.get('module')
        module_info = filter(lambda x: x.get('code') == module_name, self.server.modules)[0]
        link_id = param_dict.get('id')
        code = param_dict.get('template_code')
        result = {'link_module_id': module_info.get('id'), 'link_id': link_id, 'code': code}
        return result

    def _format_result(self, result):
        return result


class GetMediaDataCommand(Command):
    cmd = 'getMediaData'

    @property
    def parameters(self):
        return [{'name': 'filter',
                 'type': 'list',
                 'required': True,
                 'defaultValue': None}
                ]

    def _format_params(self, param_dict):
        result = super(GetMediaDataCommand, self)._format_params(param_dict)
        # 格式化filter
        filter_param = result.get('filter')
        new_filter_param = {}
        for filter_item in filter_param:
            field = filter_item[0]
            if '.' in field:
                field = field.split('.')[-1]
            operator = OPERATORS.get(filter_item[1], filter_item[1])
            values = filter_item[2]
            new_filter_param.setdefault(field, [operator, values])
        result.update({'filter': new_filter_param})
        result.pop('module')
        return result

    def _format_result(self, result):
        new_result = result.get('param')
        return new_result


class GetMediaServerCommand(Command):
    cmd = 'getMediaServerItem'

    @property
    def parameters(self):
        return [{'name': 'server_id',
                 'type': 'int',
                 'required': True,
                 'defaultValue': None}
                ]


class GetBestMediaServerCommand(Command):
    cmd = 'getMediaUploadServer'


class SaveMediaCommand(Command):

    @property
    def parameters(self):
        return [{'name': 'module',
                 'type': 'string',
                 'required': True,
                 'defaultValue': None},
                {'name': 'id',
                 'type': 'int',
                 'required': True,
                 'defaultValue': None},
                {'name': 'media_data',
                 'type': 'dict',
                 'required': True,
                 'defaultValue': None},
                {'name': 'media_server',
                 'type': 'dict',
                 'required': False,
                 'defaultValue': self.server.get_best_media_server()},
                ]

    def _format_params(self, param_dict):
        format_param = {}
        module_name = param_dict.get('module')
        module_info = filter(lambda x: x.get('code') == module_name, self.server.modules)[0]
        link_id = param_dict.get('id')
        media_data = param_dict.get('media_data')
        media_server = param_dict.get('media_server')
        format_param.update({'link_module_id': module_info.get('id'), 'link_id': link_id})
        format_param.update({'media_data': media_data})
        format_param.update({'media_server': media_server})
        return format_param


class CreateMediaCommand(SaveMediaCommand):
    cmd = 'createMedia'


class UpdateMediaCommand(SaveMediaCommand):
    cmd = 'updateMedia'


class ClearMediaThumbnailCommand(Command):
    cmd = 'clearMediaThumbnail'

    @property
    def parameters(self):
        return [{'name': 'filter',
                 'type': 'list',
                 'required': True,
                 'defaultValue': None}]

    def _format_params(self, param_dict):
        result = super(ClearMediaThumbnailCommand, self)._format_params(param_dict)
        # 格式化filter
        filter_param = result.get('filter')
        new_filter_param = {}
        for filter_item in filter_param:
            field = filter_item[0]
            if '.' in field:
                field = field.split('.')[-1]
            operator = OPERATORS.get(filter_item[1], filter_item[1])
            values = filter_item[2]
            new_filter_param.setdefault(field, [operator, values])
        result.update({'filter': new_filter_param})
        result.pop('module')
        return result


class GetMediaServerStatusCommand(Command):
    cmd = 'getMediaServerStatus'

    def _format_result(self, result):
        return result


class DeleteMediaServerCommand(Command):
    cmd = 'deleteMediaServer'


class AddMediaServerCommand(Command):
    cmd = 'addMediaServer'


class GetMediaFullPathCommand(Command):
    cmd = 'getSpecifySizeThumbPath'

    @property
    def parameters(self):
        return [{'name': 'filter',
                 'type': 'list',
                 'required': True,
                 'defaultValue': None},
                {'name': 'size',
                 'type': 'string',
                 'required': False,
                 'defaultValue': 'origin'}]

    def _format_params(self, param_dict):
        result = super(GetMediaFullPathCommand, self)._format_params(param_dict)
        # 格式化filter
        filter_param = result.get('filter')
        new_filter_param = {}
        for filter_item in filter_param:
            field = filter_item[0]
            if '.' in field:
                field = field.split('.')[-1]
            operator = OPERATORS.get(filter_item[1], filter_item[1])
            values = filter_item[2]
            new_filter_param.setdefault(field, [operator, values])
        result.update({'filter': new_filter_param})
        result.pop('module')
        return result

    def _format_result(self, result):
        # 格式化结果
        return result


class SelectMediaDataCommand(Command):
    cmd = 'selectMediaData'

    @property
    def parameters(self):
        return [{'name': 'server_id',
                 'type': 'int',
                 'required': True,
                 'defaultValue': None},
                {'name': 'md5_name_list',
                 'type': 'string',
                 'required': True,
                 'defaultValue': None}]

    def _format_result(self, result):
        # 格式化结果
        new_result = result.get('param')
        return new_result


class EventCommand(Command):

    @property
    def url(self):
        module_uri = 'event'
        module_cmd = "%s/%s" % (module_uri, self.cmd)
        return self.server.cmd_to_url(module_cmd)

    def _init_payload(self, args, kwargs):
        # 初始化默认参数的值
        param_dict = copy.deepcopy(kwargs)
        param_dict.update({self.parameters[i].get('name'): v for i, v in enumerate(args)})
        param_dict = self._setup_params(param_dict)
        param_dict = self._format_params(param_dict)
        # self._validate_param(param_dict)
        return param_dict

    def _setup_params(self, param_dict):
        # 将参数组装成需要的格式
        param_dict = copy.deepcopy(param_dict)
        for parameter in self.parameters:
            name = parameter.get('name')
            if param_dict.get(name) is None:
                default_value = parameter.get('defaultValue')
                param_dict.update({name: default_value})
        return param_dict

    def _format_result(self, result):
        return result


class GetEventServerCommand(EventCommand):
    cmd = 'getEventLogServer'

    def _format_result(self, result):
        return result


class CreateEventCommand(EventCommand):

    cmd = 'add'

    @property
    def parameters(self):
        return [{'name': 'data',
                 'type': 'dict',
                 'required': True,
                 'defaultValue': None}
                ]

    @property
    def headers(self):
        return {'Content-Type': 'application/json'}


    def _format_params(self, param_dict):
        param_dict.update({'type': 'custom'})
        return param_dict

    def _execute(self, payload):
        event_server = self.server.get_event_server()
        add_request_url = event_server.get('add_url')
        data = payload.get('data')
        result = requests.post(add_request_url, headers=self.headers, data=data)
        return result


class FindEventCommand(EventCommand):

    cmd = 'find'

    @property
    def parameters(self):
        return [{'name': 'filter',
                 'type': 'list',
                 'required': True,
                 'defaultValue': []},
                {'name': 'fields',
                 'type': 'list',
                 'required': False,
                 'defaultValue': []},
                {'name': 'order',
                 'type': 'dict',
                 'required': False,
                 'defaultValue': {}},
                {'name': 'page',
                 'type': 'dict',
                 'required': False,
                 'defaultValue': {"page_number": 0,
                                  "page_size": 0}}
                ]

    @property
    def headers(self):
        return {'Content-Type': 'application/json'}

    def _execute(self, payload):
        event_server = self.server.get_event_server()
        find_request_url = event_server.get('find_url')
        result = requests.post(find_request_url, headers=self.headers, data=json.dumps(payload))
        return result

    def _format_result(self, result):
        if result:
            return result[0]


class SelectEventCommand(EventCommand):

    cmd = 'select'

    @property
    def parameters(self):
        return [{'name': 'filter',
                 'type': 'list',
                 'required': True,
                 'defaultValue': []},
                {'name': 'fields',
                 'type': 'list',
                 'required': False,
                 'defaultValue': []},
                {'name': 'order',
                 'type': 'dict',
                 'required': False,
                 'defaultValue': {}},
                {'name': 'page',
                 'type': 'dict',
                 'required': False,
                 'defaultValue': {"page_number": 0,
                                  "page_size": 0}}
                ]

    @property
    def headers(self):
        return {'Content-Type': 'application/json'}

    def _execute(self, payload):
        event_server = self.server.get_event_server()
        select_request_url = event_server.get('select_url')
        result = requests.post(select_request_url, headers=self.headers, data=json.dumps(payload))
        return result


class EventFieldsCommand(EventCommand):

    cmd = 'fields'

    @property
    def headers(self):
        return {'Content-Type': 'application/json'}

    def _execute(self, payload):
        event_server = self.server.get_event_server()
        fields_request_url = event_server.get('fields_url')
        result = requests.post(fields_request_url, headers=self.headers, data=json.dumps(payload))
        return result

    def _format_result(self, result):
        return result.get('fixed_field', {})


class SendEmailCommand(EventCommand):

    cmd = 'send'

    @property
    def parameters(self):
        return [{'name': 'addressee_list',
                 'type': 'list',
                 'required': True,
                 'defaultValue': []},
                {'name': 'subject',
                 'type': 'list',
                 'required': True,
                 'defaultValue': []},
                {'name': 'template',
                 'type': 'string',
                 'required': True,
                 'defaultValue': None},
                {'name': 'content',
                 'type': 'string,dict',
                 'required': True,
                 'defaultValue': None}
                ]

    @property
    def headers(self):
        return {'Content-Type': 'application/json'}

    def _format_params(self, param_dict):
        addressee_list = param_dict.get('addressee_list')
        subject = param_dict.get('subject')
        content = param_dict.get('content')
        template = param_dict.get('template')
        addressee = ','.join(addressee_list)
        format_param = {'param': {'addressee': addressee, 'subject': subject},
                        'data': {'template': template, 'content': content}}
        return format_param

    def _execute(self, payload):
        event_server = self.server.get_event_server()
        request_url = event_server.get('request_url')
        token = event_server.get('token')
        send_email_url = urlparse.urljoin(request_url, 'email/%s?sign=%s' % (self.cmd, token))
        result = requests.post(send_email_url, headers=self.headers, data=json.dumps(payload))
        return result

    def _format_result(self, result):
        return result
