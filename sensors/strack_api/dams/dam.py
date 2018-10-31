# coding=utf8
# Copyright (c) 2018 CineUse
import abc


def return_type(return_type):
    def typecheck(f):
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            if return_type and not isinstance(result, return_type):
                raise RuntimeError("{} should return {}".format(f.__name__, return_type.__name__))
            return result

        return wrapper

    return typecheck


class DAM(object):

    @abc.abstractmethod
    @return_type(dict)
    def find(self, module, filter="", fields=None):
        """
        虚的
        Returns:

        """

    @abc.abstractmethod
    @return_type(list)
    def select(self, module, filter="", fields=None, page=None):
        """

        Returns:

        """

    @abc.abstractmethod
    @return_type(dict)
    def create(self, module, data):
        """

        Returns:

        """

    @abc.abstractmethod
    @return_type(dict)
    def delete(self, module, id):
        """

        Returns:

        """

    @abc.abstractmethod
    @return_type(dict)
    def update(self, module, id, data):
        """

        Returns:

        """

    @abc.abstractmethod
    @return_type(dict)
    def upload(self, module, upload_file, data):
        """

        Returns:

        """