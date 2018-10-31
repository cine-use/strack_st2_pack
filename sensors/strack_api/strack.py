# coding=utf8
# Copyright (c) 2016 Strack

import logging
import requests
import urlparse

from strack_commands import *

log = logging.getLogger("strack_api")


class Strack(object):
    """
    the main object
    """

    COMMAND_FACTORY = {
        'find_one': FindCommand,
        'find': SelectCommand,
        'create': CreateCommand,
        'update': UpdateCommand,
        'summary': SummaryCommand,
        'delete': DeleteCommand,
        'fields': FieldsCommand,
        'tag': TagCommand,
        'relation_fields': RelationFieldsCommand,
        'creation_require_fields': RequireFeildsCommand
    }

    EVENT_COMMAND_FACTORY = {
        'create': CreateEventCommand,
        'find_one': FindEventCommand,
        'find': SelectEventCommand,
        'fields': EventFieldsCommand,
        'send_email': SendEmailCommand
    }

    PUBLIC_COMMAND_FACTORY = {
        'upload': UploadCommand,
        'get_member_data': GetMemberDataCommand,
        'get_parent_dir': GetParentDirCommand,
        'get_children_dir': GetChildrenDirCommand,
        'get_brother_dir': GetBrothersDirCommand,
        'get_template_path': GetTemplatePathCommand,
        'get_item_path': GetItemPathCommand,
        'create_media': CreateMediaCommand,
        'update_media': UpdateMediaCommand,
        'get_media_data': GetMediaDataCommand,
        'get_best_media_server': GetBestMediaServerCommand,
        'get_media_server': GetMediaServerCommand,
        'get_media_server_status': GetMediaServerStatusCommand,
        'clear_media_thumbnail': ClearMediaThumbnailCommand,
        'get_media_full_path': GetMediaFullPathCommand,
        'select_media_data': SelectMediaDataCommand,
        'get_event_server': GetEventServerCommand
    }

    def __init__(self, base_url, login_name, password):
        if not base_url.endswith("/"):
            base_url += "/"
        self.session = requests.session()
        self.__base_url = base_url
        self.__login_name = login_name
        self._scheme, self._server, self._api_base, _, _ = urlparse.urlsplit(urlparse.urljoin(base_url, 'api/'))

        self.__entity_list = []
        self.__general_doc_dict = None
        self.__logger = None
        self.__token = self.get_token(password)
        self.__modules = self._list_modules()

        self.__public_commands = {}  #

    @property
    def base_url(self):
        return self.__base_url

    @property
    def login_name(self):
        return self.__login_name

    @property
    def token(self):
        return self.__token

    @property
    def name(self):
        return "Strack"

    def cmd_to_url(self, cmd_url):
        api_path = urlparse.urljoin(self._api_base, cmd_url)
        url = urlparse.urlunparse((self._scheme, self._server, api_path, None, None, None))
        return url

    def get_token(self, password):
        """request sign code"""
        cmd = 'login/in'
        url = self.cmd_to_url(cmd)
        auth = {
            'login_name': self.login_name,
            'password': password,
            'from': 'api',
        }
        response = self.session.post(url, data=auth)
        if response.json().get("status") == 200:
            sign_info = response.json().get("data", {})
            return sign_info.get("token", "")
        else:
            log_msg = "%s: %s" % (response.status_code, response.json().get("message"))
            log.error(log_msg)
            raise log_msg

    def _list_modules(self):
        cmd = 'module/getModuleData'
        url = self.cmd_to_url(cmd)
        response = self.session.post(url, headers={"token": self.token})
        if response.json().get("status") == 200:
            data = response.json().get("data", {})
            module_info = data.get("rows", [])
            return module_info
        else:
            return

    @property
    def modules(self):
        """
        返回所有可以操作的模块
        Returns:

        """
        return self.__modules

    def set_up_command(self, module_name, command_name):
        if module_name in ['event', 'email']:
            module = {'code': 'event'}
            command_factory = self.EVENT_COMMAND_FACTORY
        else:
            # check module in all modules
            for module in self.modules:
                if module.get('code') == module_name:
                    break
            else:  # when no break triggered, go to else
                log.error('Not module named %s.' % module_name)
                raise RuntimeError('Not module named %s.' % module_name)

            command_factory = self.PUBLIC_COMMAND_FACTORY \
                if command_name in self.PUBLIC_COMMAND_FACTORY \
                else self.COMMAND_FACTORY

        CommandClass = command_factory.get(command_name)
        return CommandClass(self, module)

    def fields(self, module_name):
        """

        Args:
            module_name: [string] Name of module

        Returns: [list] Dicts about field name and field data type in module

        """
        command = self.set_up_command(module_name, 'fields')
        return command()

    def relation_fields(self, module_name):
        """

        Args:
            module_name:

        Returns:

        """
        command = self.set_up_command(module_name, 'relation_fields')
        return command()

    def creation_require_fields(self, module_name):
        command = self.set_up_command(module_name, 'creation_require_fields')
        return command()

    def find(self, module_name, filter=None, fields=None, order=None, page=None):
        """

        Args:
            module_name: [string] Name of module
            filter: [list] List of filter conditions
            fields: [list] List of fields to return
            page:
            order:

        Returns: [dict] Dict about found item in module

        """
        command = self.set_up_command(module_name, 'find')
        return command(filter, fields, order, page)

    def select(self, module_name, filter=None, fields=None, order=None, page=None):
        """

        Args:
            module_name: [string] Name of module
            filter: [list] List of filter conditions
            fields: [list] List of fields to return
            order: [dict] Dict about order field
            page: [dict] Dict about pageNum and pageSize

        Returns: [list] List of dicts about found item in module

        """
        # init command object
        command = self.set_up_command(module_name, 'select')
        # execute
        return command(filter, fields, order, page)

    def summary(self, module_name, filter=None):
        command = self.set_up_command(module_name, 'summary')
        return command(filter)

    def create(self, module_name, data):
        """

        Args:
            module:
            data:

        Returns:

        """
        log.debug("Strack API create a object info in %s." % module_name)
        command = self.set_up_command(module_name, 'create')
        return command(data)

    def update(self, module_name, id, data):
        log.debug("Strack API update a object info in %s." % module_name)
        command = self.set_up_command(module_name, 'update')
        return command(id, data)

    def tag(self, module_name, id, tag_id):
        command = self.set_up_command(module_name, 'tag')
        return command(id, tag_id)

    def delete(self, module_name, id):
        log.debug("Strack API delete a object info in %s." % module_name)
        command = self.set_up_command(module_name, 'delete')
        return command(id)

    def upload(self, file_path, server=None):
        # fixme: get the best server when server is None
        command = self.set_up_command('media', 'upload')
        return command(file_path, server)

    def get_member_data(self, user_id, module_id):
        """
        查询某一用户在某模块下被分配了哪些对象
        Args:
            user_id: [int] id of a user
            module_id: [int] id of a module

        Returns: [list] List of objects assigned to a user

        """
        command = self.set_up_command('user', 'get_member_data')
        return command(user_id, module_id)

    def get_parent_dir(self, id):
        """
        获取当前对象父级路径
        Args:
            module:
            id:

        Returns:

        """
        command = self.set_up_command('dir_template', 'get_parent_dir')
        return command(id)

    def get_children_dir(self, id):
        """
        获取当前对象子级路径
        Args:
            module:
            id:

        Returns:

        """
        command = self.set_up_command('dir_template', 'get_children_dir')
        return command(id)

    def get_brother_dir(self, id):
        """
        获取当前路径模板对象的兄弟路径
        Args:
            module:
            id:

        Returns:

        """
        command = self.set_up_command('dir_template', 'get_brother_dir')
        return command(id)

    def get_template_path(self, module_name, id, template_code=''):
        """
        获取指定项目的某种类型的模块的对象的路径模板
        Args:
            module_name:
            entity_id:
            project_id:
        Returns:

        """
        command = self.set_up_command('dir_template', 'get_template_path')
        return command(module_name, id, template_code)

    def get_item_path(self, module_name, id, template_code=''):
        """
        根据dir_template 求出某一对象的具体路径
        Args:
            module_name:
            id:
            template_code:

        Returns:

        """
        command = self.set_up_command('dir_template', 'get_item_path')
        return command(module_name, id, template_code)

    def create_media(self, module_name, id, media_data, media_server=None):
        """

        Args:
            module:
            id:
            server:
            duration:
            md5name:
            size:

        Returns:

        """
        command = self.set_up_command('media', 'create_media')
        return command(module_name, id, media_data, media_server)

    def update_media(self, module_name, id, media_data, media_server=None):
        """

        Args:
            module:
            id:
            media_data:
            media_server:

        Returns:

        """
        command = self.set_up_command('media', 'update_media')
        return command(module_name, id, media_data, media_server)

    def get_media_data(self, filter=None):
        command = self.set_up_command('media', 'get_media_data')
        return command(filter)

    def get_best_media_server(self):
        """
        Description: 获取连接速度最快的媒体服务器

        Returns:

        """
        command = self.set_up_command('media', 'get_best_media_server')
        return command()

    def get_media_server(self, server_id):
        """
        Description: 获取指定id的媒体服务器

        Args:
            server_id:

        Returns:

        """
        command = self.set_up_command('media', 'get_media_server')
        return command(server_id)

    def get_media_server_status(self):
        """

        Description: 获取所有的媒体服务器状态

        Returns:

        """
        command = self.set_up_command('media', 'get_media_server_status')
        return command()

    def clear_media_thumbnail(self, filter):
        command = self.set_up_command('media', 'clear_media_thumbnail')
        return command(filter)

    def get_media_full_path(self, filter, size='origin'):
        command = self.set_up_command('media', 'get_media_full_path')
        return command(filter, size)

    def select_media_data(self, server_id, md5_name_list):
        command = self.set_up_command('media', 'select_media_data')
        return command(server_id, md5_name_list)

    def get_event_server(self):
        command = self.set_up_command('media', 'get_event_server')
        return command()

    def send_email(self, addressee_list, subject, template, content):
        command = self.set_up_command('email', 'send_email')
        return command(addressee_list, subject, template, content)


if __name__ == "__main__":
    # st = Strack(base_url="http://192.168.31.168/strack/api/",
    #             login_name="strack_admin", password="chengwei5566")
    st = Strack(base_url="http://192.168.31.234/strack/",
                login_name="strack_admin", password="chengwei5566")
    from pprint import pprint
    # pprint(st.get_member_data(1, 4))
    # print st.send_email(["298081132@qq.com"], u"Strack测试", "text", u"测试内容")
    pprint(st.find('task', fields=st.relation_fields('task')))
    # pprint(st.create('dir_template', {'link_module_id': 4, 'link_id': 10001, 'rule': 'test_link_module', 'pattern': '{1}'}))
    # pprint(len(st.select('file', filter=[['id', '>', 1000]], fields=st.relation_fields('file'),
    #                      page={'page_size': 20000, 'page_num': 1})))
    # pprint(st.find('project', fields=st.relation_fields('project')))
    # pprint(st.select('file', filter=[['link_module_id', '=', 4]],
    #                  fields=st.relation_fields('file')))
    # print st.select('file', order={'id': 'desc'})
    # print st.relation_fields('project')
    # pprint(st.find('note', fields=st.relation_fields('note')))
    # pprint(st.find('file'))
    # pprint(st.update('file', 2, {'proxy_path': "b1a", "public_path": "b1c"}))
    # pprint(st.select('file', fields=st.relation_fields('file'))[0])
    # pprint(st.find('event', filter=[['id', '=', 2]]))
    # pprint(st.select('event'))
    # pprint(st.fields('event'))
    # pprint(st.create('event', {"link_module_id": 24,
    #                            "operate": "file_action",
    #                            "type": "custom",
    #                            "table": "File",
    #                            "project_id": 22,
    #                            "link_id": 222,
    #                            "from": "strack_action",
    #                            "record": []}))
