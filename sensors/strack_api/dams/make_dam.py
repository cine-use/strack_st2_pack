# coding=utf8
# Copyright (c) 2018 CineUse
import imp

from return_type import return_type
from dam import DAM


@return_type(DAM)
def make_dam(dam_type, server, user, password):
    module_file, module_path, description = imp.find_module(dam_type, ['./dams'])
    dam_module = imp.load_module(module_file, module_path, description)
    dam = dam_module.connect(server, user, password)
    return dam
