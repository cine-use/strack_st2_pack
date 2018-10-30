# coding=utf8
# Copyright (c) 2018 CineUse
SHOTGUN_URL = 'https://david1.shotgunstudio.com'
SHOTGUN_SCRIPT = 'event_daemon'
SHOTGUN_API_KEY = 'zlqcp7nlaqohrHrqgr-oigyzc~uyz'

STACK_SERVER_URL = "http://192.168.31.12/strack"
STACK_USER = "strack_admin"
STACK_PASSWD = "chengwei5566"


def get_dam_session(dam_type="strack"):
    if dam_type == "shotgun":
        from shotgun_api3.shotgun import Shotgun
        return Shotgun(SHOTGUN_URL, SHOTGUN_SCRIPT, SHOTGUN_API_KEY)
    else:
        from strack_api.strack import Strack
        return Strack(STACK_SERVER_URL, STACK_USER, STACK_PASSWD)


if __name__ == "__main__":
    get_dam_session()
