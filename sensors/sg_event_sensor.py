# coding=utf8
# Copyright (c) 2018 CineUse

import json
import datetime
from st2reactor.sensor.base import PollingSensor
from common_lib.get_dam_session import get_dam_session

__all__ = [
    'ShotgunEventSensor'
]

INIT_EVENT_ID = 458021
# process json datetime


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        else:
            return json.JSONEncoder.default(self, obj)


class ShotgunEventSensor(PollingSensor):
    def __init__(self, sensor_service, config=None, poll_interval=None):
        super(ShotgunEventSensor, self).__init__(
            sensor_service=sensor_service,
            config=config,
            # poll_interval = poll_interval
            poll_interval=0.5
        )
        self._logger = self.sensor_service.get_logger(name=self.__class__.__name__)

        self._datastore = self._get_datastore_dict()
        self._logger.debug("get datastore: %s" % self._datastore)

    def setup(self):
        """ get shotgun connection """
        self._client = get_dam_session("shotgun")

        """ init event id , init in the self._get_event_id() """
        # self._get_event_id()

        """ set query parameters """
        self._filters = [['id', 'greater_than', int(self._get_event_id())]]
        self._fields = ['id', 'event_type', 'attribute_name', 'meta', 'entity', 'user', 'project', 'session_uuid',
                        'created_at']
        self._order = [{'column': 'id', 'direction': 'asc'}]

        """ set query count per time """
        self._per_query_count = 1

    def poll(self):
        self._logger.debug("------- start polling ---------")
        shotgun = self._client
        # update the next event id
        self._filters = [['id', 'greater_than', int(self._get_event_id())]]
        results = shotgun.find("EventLogEntry", self._filters, self._fields, self._order)
        self._logger.debug("polled: %s" % results)
        for result in results:
            try:
                self._dispatch_trigger(result)
            except Exception as e:
                self._logger.exception('Polling Shotgun Event failed: %s' % (str(e)))
        if len(results) > 0:
            self._set_event_id(results[-1]['id'])
            self._logger.debug('set last event id to %s' % results[-1]['id'])
        self._logger.debug("------- end polling ---------")

    def _dispatch_trigger(self, json_dict):
        trigger = 'strack.shotgun_event_change'
        payload = {
            'json_str': json.dumps(json_dict, cls=DateEncoder)
        }
        self._logger.info("dispatch trigger %s with payload %s" % (trigger, payload))
        self._sensor_service.dispatch(trigger=trigger, payload=payload)

    """ get nextEventId for shotgun find filers """

    def _get_event_id(self):
        self._last_id = int(self._sensor_service.get_value('last_id'))
        return unicode(self._last_id)

    def _set_event_id(self, last_id):
        self._last_id = last_id
        if hasattr(self._sensor_service, 'set_value'):
            if last_id < INIT_EVENT_ID:
                self._sensor_service.set_value(name='last_id', value='%s' % INIT_EVENT_ID)
            else:
                self._sensor_service.set_value(name='last_id', value=last_id)

    """ 
    convert sensor_service datastore to dict 
    ! this should be runned only ONCE !    
    """

    def _get_datastore_dict(self):
        kvps = self.sensor_service.list_values()
        _dict = {}
        for kvp in kvps:
            _dict[kvp.name] = kvp.value
        return _dict

    """ when sensor to be died , call cleanup """

    def cleanup(self):
        self._stop = True

    """ trigger event : add , update ,remove trigger will call the funcs """

    def add_trigger(self, trigger):
        pass

    def update_trigger(self, trigger):
        pass

    def remove_trigger(self, trigger):
        pass
