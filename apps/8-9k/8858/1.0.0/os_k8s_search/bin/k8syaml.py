import json
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
import yaml
from splunklib.searchcommands import Configuration, Option, StreamingCommand, dispatch

@Configuration(distributed=False)
class K8sYAMLCommand(StreamingCommand):
    field = Option(doc='**Syntax:** **field=***<fieldname>*\n        **Description:** Field to read JSON from. Defaults to `_raw`.', default='_raw', require=False)
    output = Option(doc='**Syntax:** **output=***<fieldname>*\n        **Description:** Field to write YAML to. Defaults to the same\n        field as `field=` (in-place rewrite).', default=None, require=False)

    def stream(self, records):
        in_field = self.field
        out_field = self.output or in_field
        for record in records:
            raw = record.get(in_field, '')
            if raw:
                converted = _to_yaml(raw)
                if converted is not None:
                    record[out_field] = converted
            yield record

def _to_yaml(raw):
    try:
        obj = json.loads(raw)
    except (TypeError, ValueError):
        return None
    try:
        return yaml.safe_dump(obj, sort_keys=False, default_flow_style=False, allow_unicode=True, indent=2)
    except yaml.YAMLError:
        return None
if __name__ == '__main__':
    dispatch(K8sYAMLCommand, sys.argv, sys.stdin, sys.stdout, __name__)
