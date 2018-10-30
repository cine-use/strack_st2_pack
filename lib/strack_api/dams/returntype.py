# coding=utf8
# Copyright (c) 2018 CineUse


def return_type(return_type):
    def typecheck(f):
        def wrapper(*args, **kwargs):
            result = f(*args, **kwargs)
            if return_type and not isinstance(result, return_type):
                raise RuntimeError("{} should return {}".format(f.__name__, return_type.__name__))
            return result

        return wrapper

    return typecheck
