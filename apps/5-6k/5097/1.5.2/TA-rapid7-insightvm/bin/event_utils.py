import json
import sys

class EventUtils:
    MAX_SIZE = "max_size"
    MODIFIER = "modifier"
    DEFAULT_MAX_SIZE = 1000

    EVENT_FIELDS_TO_TRUNCATE = {
        "rapid7:insightvm:vulnerability_definition":[
            "references",
            "cves",
            "description",
            "links",
            "malware_kits",
            "exploits"
        ]
    }
    
    # TODO: This should come from the props.conf.
    EVENT_MAX_LENGTHS = {
        "rapid7:insightvm:vulnerability_definition": 50000
    }

    def __init__(self, helper):
        self.helper = helper
        
        # To truncate a new type add an entry for the type to type_truncation_rules.
        self.type_truncation_rules = {
            str: {
                "max_size": self.DEFAULT_MAX_SIZE,
                "modifier": self.__string_modifier
            },
            list: {
                "max_size": 75,
                "modifier": self.__list_modifier
            }
        }

    def exceeds_max_length(self, event_data, import_type):
        if event_data is None or import_type is None:
            return False
        
        if self.EVENT_MAX_LENGTHS.get(import_type) is None:
            return False
        
        return len(event_data) > self.EVENT_MAX_LENGTHS.get(import_type)

    def truncate_json(self, json_item, import_type):
        if self.EVENT_FIELDS_TO_TRUNCATE.get(import_type) is None:
            return
        
        for field in self.EVENT_FIELDS_TO_TRUNCATE.get(import_type):
            field_value = json_item.get(field)
            
            try:
                if field_value is None or len(field_value) == 0:
                    continue
            except Exception as e:
                self.helper.log_error("Non null field {} with no length property cannot be truncated".format(field))
                continue
            
            rule = self.__get_truncation_rule(field_value)
            if rule is None:
                continue

            max_length = rule.get(self.MAX_SIZE) or self.DEFAULT_MAX_SIZE

            if len(field_value) > max_length:
                field_value = field_value[:max_length]

                # A modifier function can be used to add an indicator that some form of truncation occurred. 
                modifier = rule.get(self.MODIFIER)
                if modifier is not None:
                    field_value = modifier(field_value)

                json_item[field] = field_value

    def create_event(self, json_item, event_type):
        output = json.dumps(json_item)

        if self.exceeds_max_length(output, event_type):
            self.truncate_json(json_item, event_type)
            output = json.dumps(json_item)

        event = self.helper.new_event(source="Rapid7 InsightVM", index=self.helper.get_output_index(), 
            sourcetype=event_type, data=output)
        
        return event

    def __get_truncation_rule(self, field_value):
        rule = self.type_truncation_rules.get(type(field_value))

        # Specifically to handle unicode strings in python 2.7.
        if rule is None and sys.version_info[0] < 3 and isinstance(field_value, basestring):
            rule = self.type_truncation_rules.get(str)

        return rule

    def __string_modifier(self, initial_value):
        # Truncation may occur part the way through a multi-byte character leaving invalid bytes. If the 
        # byte string is then converted to unicode an error will occur. To mitigate this explicitly convert
        # to unicode and ignore any invalid characters.
        if sys.version_info[0] < 3 and type(initial_value) == str:
            initial_value = initial_value.decode("utf-8", errors="ignore")
        
        return initial_value + "..."
    
    def __list_modifier(self, initial_value):
        # TODO: In the future we may want to add some form of truncation indicator for lists, but be aware the list
        # can contain different types of data.
        return initial_value