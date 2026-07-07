from datetime import datetime

from BaseMapper import BaseMapper
from EventItem import EventItem


class SearchEventObjectMapper(BaseMapper):
    def map(self, json_data):
        key_valued_objects = self.convert_json_to_key_value(json_data)

        mapped_items = []
        for obj in key_valued_objects:
            mapped_items.append(self.map_item(obj).to_dict())

        return mapped_items

    def map_item(self, row):
        event_item = EventItem(row)

        return event_item

    def multi_value_to_guid_array(self, row, field: str):
        value = row.get(field)
        if value:
            return [v for v in value.split(',')]
        return None

    def get_bool_value(self, row, name: str):
        value = row.get(name)
        if value:
            value = value.lower()
            if value == 'yes':
                return True
            if value == 'no':
                return False
            if value == 'true':
                return True
            if value == 'false':
                return False
        return None

    def get_date_value(self, row, name: str):
        value = row.get(name)
        if value:
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return None
        return None

    def multi_value_to_array(self, multi_value: str):
        if multi_value:
            return [v.strip() for v in multi_value.split(',') if v.strip()]
        return None
