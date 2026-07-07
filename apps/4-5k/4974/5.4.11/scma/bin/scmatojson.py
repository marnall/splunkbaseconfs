import sys
import json
import re
from distutils.util import strtobool
from wsgiref.validate import validator
import os 
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import (
    StreamingCommand,
    Configuration,
    Option,
    validators,
    dispatch
)

FIELD_NAME_REGEX = "[_a-zA-Z0-9\-\. ]*"
FIELDS_REGEX = '([_a-zA-Z0-9\-\. \*]+)((?i)(\((json|string|int|float|bool)\)|\[(json|string|int|float|bool)?\]))?'
ERROR_INVALID_FIELD_NAME = "Invalid field name %s. Fields must be expressed in the format '" + FIELDS_REGEX + "'."
ERROR_FIELD_PATH_CONFLICT = "Can't create field %s due to conflict."


def convert_field(val, field_type, default=None):
    try:
        if field_type == STRING:
            return val
        elif field_type == INT:
            return int(val)
        elif field_type == FLOAT:
            return float(val)
        elif field_type == BOOL:
            return bool(strtobool(val))
        elif field_type == JSON:
            return json.loads(val)
        else:
            # auto detect type if none is specified, defaults to string
            convert_val = convert_field(val, INT)
            if convert_val is not None:
                return convert_val

            convert_val = convert_field(val, FLOAT)
            if convert_val is not None:
                return convert_val

            return val

    except ValueError:  # return default if forced conversion fails
        return default


def convert_list(vals, field_type):
    res = []
    for idx, val in enumerate(vals):
        res.append(convert_field(val, field_type, default=val))
    return res


AUTO, JSON, INT, STRING, FLOAT, BOOL = ["AUTO", "JSON", "INT", "STRING", "FLOAT", "BOOL"]


@Configuration()
class MakeJsonCommand(StreamingCommand):
    _validFields = [{
        "regex": re.compile(FIELD_NAME_REGEX),
        "type": AUTO,
        "forceArray": False
    }]

    output = Option(
        doc="""
        Name of field that contains the JSON output.
        """,
        require=False,
        default='_raw'
    )

    include_internal = Option(
        doc="""
        When set to true, include internal fields such as _time, _indextime, or _cd in its JSON object output.
        """,
        require=False,
        default=False,
        validate=validators.Boolean()
    )

    include_defaults = Option(
        doc="""
        When set to true, include default fields such as index, host, or date_hour in its JSON object output.
        """,
        require=False,
        default=False,
        validate=validators.Boolean()
    )

    fill_null = Option(
        doc="""
        When set to true, fill null field values so all fields will appear in its JSON object output.
        """,
        require=False,
        default=False,
        validate=validators.Boolean()
    )

    include_orig_raw = Option(
        doc="""
        When set to true, the original raw format will appear as orig_raw field in its JSON object output.
        """,
        require=False,
        default=False,
        validate=validators.Boolean()
    )

    def get_field_type(self, field):
        for validField in self._validFields:
            if validField["regex"].match(field):
                return validField["type"], validField["forceArray"]

        return None, None

    def get_json(self, data):
        res = {}
        default_fields = ['date_hour','date_mday','date_minute','date_month','date_second','date_wday','date_year','date_zone','eventtype','host','index','linecount','punct','source','sourcetype','splunk_server','splunk_server_group','tag','tag::eventtype','thread_id','thread_name','timeendpos','timestartpos']
        internal_fields = ['_bkt','_cd','_eventtype_color','_kv','_si','_time','_sourcetype','_indextime','_subsecond','_serial']

        for k, v in data.items():

            if self.include_internal == False:
                if k in internal_fields:
                    continue

            if self.include_defaults == False:
                if k in default_fields:
                    continue
            
            if self.fill_null == False:
                if v == "":
                    continue

            field_type, force_array = self.get_field_type(k)
            if field_type:
                dotpath = k.split(".")

                # Setup the correct amount of nested dicts based on the dot path
                target = res
                for segment in dotpath[:-1]:
                    target.setdefault(segment, {})
                    target = target[segment]

                try:
                    if isinstance(v, list):
                        target[dotpath[-1]] = convert_list(v, field_type)
                    elif v is not None:
                        converted_val = convert_field(v, field_type, default=v)
                        target[dotpath[-1]] = [
                            converted_val] if force_array else \
                            converted_val
                    else:
                        target[dotpath[-1]] = None

                except TypeError:
                    raise Exception(ERROR_FIELD_PATH_CONFLICT % k)
        return res

    def set_valid_fields(self):
        errors = []
        self._validFields = []

        for jsonField in self.fieldnames:
            match = re.search("^" + FIELDS_REGEX + "$", jsonField)

            if match and match.group(1):
                field_type = match.group(2)

                if field_type:
                    force_array = (
                        field_type[:1] == "[")  # force conversion to array
                    field_type = field_type[1:-1].upper()
                    if field_type == "":
                        field_type = AUTO
                else:
                    force_array = False
                    field_type = AUTO

                regex_pattern = match.group(1).replace(".", "\\.") \
                    .replace("*", FIELD_NAME_REGEX)

                self._validFields.append({
                    "type": field_type,
                    "forceArray": force_array,
                    "regex": re.compile("^" + regex_pattern + "$")

                })

            else:
                errors.append(ERROR_INVALID_FIELD_NAME % jsonField)

        if len(self._validFields) == 0:
            self._validFields.append({
                "regex": re.compile(FIELD_NAME_REGEX),
                "type": AUTO,
                "forceArray": False
            })

        return errors

    def prepare(self):
        errors = self.set_valid_fields()
        for error in errors:
            self.write_error(error)

        if len(errors) > 0:
            self.error_exit(Exception("Fieldname validation failed "
                                      "for makejson command."))

    def stream(self, results):

        error_counts = {}
        found_results = 0

        for res in results:
            #res['raw'] = res['_raw']
            found_results += 1
            try:
                json_val = self.get_json(res)
                
                json_val['orig_raw'] = json_val.pop('_raw')
                if self.include_orig_raw == False:
                    json_val.pop('orig_raw')

                res[self.output] = json.dumps(json_val)
            except Exception as e:
                if e.message in error_counts:
                    error_counts[e.message] += 1
                else:
                    error_counts[e.message] = 1

                res[self.output] = "{}"

            yield res

        # report all errors
        for err in error_counts:
            if error_counts[err] > 0:
                self.write_error(
                    err + " (" + str(error_counts[err]) + " of " + str(
                        found_results) + " events)")


dispatch(command_class=MakeJsonCommand, argv=sys.argv, module_name= __name__)
