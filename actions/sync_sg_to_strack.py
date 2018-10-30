# coding=utf8
# Copyright (c) 2018 CineUse

import json
from st2actions.runners.pythonrunner import Action
from get_dam_session import get_dam_session
from strack_shotgun_fields_map import get_st_field


class WriteDataAction(Action):
    def __init__(self, config):
        super(WriteDataAction, self).__init__(config)

    def run(self, json_str):
        st = self.action_service.getvalue(name="strack_session")
        if not st:
            st = get_dam_session("strack")
            self.action_service.setvalue(name="strack_session", value=st)

        sg = self.action_service.getvalue(name="shotgun_session")
        if not sg:
            sg = get_dam_session("shotgun")
            self.action_service.setvalue(name="shotgun_session", value=sg)

        self.logger.info("get event from shotgun: %s" % json_str)
        try:
            # parse shotgun event info
            event_info = json.loads(json_str)
            if not event_info.get("project"):
                return True, "Event not in any project, nothing to do."
            event_meta_data = event_info.get("meta")
            # if not really changed, ignore
            if event_meta_data.get("actual_attribute_changed"):
                return True, "No field changed, nothing to do."

            # if anything created, cache entity type
            if event_meta_data.get("type") == "new_entity":  # start create
                self.logger.debug("creating")
                self.action_service.setvalue(name="in_creating", value=True)
                new_creation = {"module": event_meta_data.get("entity_type"),
                                "fields": {"source_id": event_meta_data.get("entity_id")}}
                self.action_service.setvalue(name="new_creation", value=new_creation)
                return True, "Pending create, will deferred util creating done."

            # if something created, store attributes and create it util attr set done
            elif event_meta_data.get("type") == "attribute_change" and event_meta_data.get("in_create"):  # in creating
                new_creation = self.action_service.getvalue(name="new_creation")
                field_name = get_st_field(event_meta_data.get("entity_type"), event_meta_data.get("attribute_name"))
                field_value = event_meta_data.get('new_value')
                new_creation["fields"].setdefault(field_name, field_value)
                self.action_service.setvalue(name="new_creation", value=new_creation)
                return True, "Pending create, will deferred util creating done."

            # do create
            elif self.action_service.getvalue(name="in_creating"):  # just created
                new_creation = self.action_service.getvalue("new_creation")
                module_name = new_creation.get("module")
                init_data = new_creation.get("fields")
                st.create(module_name, init_data)       # FIXME: if entity in init data, it'll be wrong
                self.logger.debug("create done")
                self.action_service.setvalue(name="in_creating", value=False)
                return True, "new %s created, data: %s" % (module_name, init_data)

            # edit fields
            elif event_meta_data.get("type") == "attribute_change":
                module_name = event_meta_data.get("entity_type")
                st_entity_id = st.find_one(module_name, ["source_id", "==", event_meta_data.get("entity_id")])
                new_data = {event_meta_data.get("attribute_name"): event_meta_data.get('new_value')}
                st.update(module_name, st_entity_id, new_data)
                return True, "successful update %s/%s to %s" % (module_name, st_entity_id, new_data)
            # remove something
            elif event_meta_data.get("type") == "entity_retirement":
                module_name = event_meta_data.get("entity_type")
                st_entity_id = st.find_one(module_name, ["source_id", "==", event_meta_data.get("entity_id")])
                st.delete(module_name, st_entity_id)
                return True, "successful delete %s/%s" % (module_name, st_entity_id)
        except Exception as e:
            # TODO: roll back operations in strack
            return False, "%s" % e

        return True, "Nothing happened, ignore"
