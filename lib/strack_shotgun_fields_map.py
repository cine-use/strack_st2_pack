# coding=utf8
# Copyright (c) 2018 CineUse

SG_ST_FIELD_PARES = {
    "Asset": [
        ("sg_asset_type", "category"),
        ("sg_status_list", "status"),
    ],
    "Task": [
        ("sg_status_list", "status"),
    ]
}


def get_sg_field(module, st_field_name):
    module_field_pair = SG_ST_FIELD_PARES.get(module)
    module_field_map = dict(map(lambda pair: (pair[1], pair[0]), module_field_pair))
    if st_field_name in module_field_map:
        return module_field_map.get(st_field_name)
    return st_field_name


def get_st_field(module, sg_field_name):
    module_field_pair = SG_ST_FIELD_PARES.get(module)
    module_field_map = dict(module_field_pair)
    if sg_field_name in module_field_map:
        return module_field_map.get(sg_field_name)
    return sg_field_name

