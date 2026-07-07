from BaseMapper import BaseMapper

class ThreatModelItem:
    def __init__(self):
        self.ID= None
        self.Name = None
        self.Category = None
        self.Severity = None
        self.Source = None

    def __getitem__(self, key: str):
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"{key} not found in EventItem")

    def to_dict(self):
        return {key: value for key, value in self.__dict__.items() if value is not None}
        
class ThreatModelObjectMapper(BaseMapper):
    def map(self, json_data):
        key_valued_objects = json_data

        mapped_items = []
        for obj in key_valued_objects:
            mapped_items.append(self.map_item(obj).to_dict())

        return mapped_items

    def map_item(self, row: dict) -> ThreatModelItem:
        threat_model_item = ThreatModelItem()
        threat_model_item.ID = row[ThreatModelAttributes.Id]
        threat_model_item.Name = row[ThreatModelAttributes.Name]
        threat_model_item.Category = row[ThreatModelAttributes.Category]
        threat_model_item.Source = row[ThreatModelAttributes.Source]
        threat_model_item.Severity = row[ThreatModelAttributes.Severity]

        return threat_model_item


class ThreatModelAttributes:
    Id = "ruleID"
    Name = "ruleName"
    Category = "ruleArea"
    Source = "ruleSource"
    Severity = "severity"

    Columns = [Id, Name, Category, Source, Severity]