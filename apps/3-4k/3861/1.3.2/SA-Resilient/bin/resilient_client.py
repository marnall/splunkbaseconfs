# -*- coding: utf-8 -*-
# pragma pylint: disable=unused-argument, no-self-use

# (c) Copyright IBM Corp. 2022. All Rights Reserved.

import json
import csv
from collections import defaultdict, namedtuple
from xml.sax.saxutils import escape as xml_escape
from xml.sax.saxutils import quoteattr as xml_quoteattr
import re
import time
import co3base as resilient
import datetime
from datetime import timedelta, tzinfo
import sys
from functools import lru_cache
import time
import traceback

try:
    from datetime import timezone
    utc = timezone.utc
except ImportError:
    # python2 implementation
    class UTC(tzinfo):
        def utcoffset(self, dt):
            return timedelta(0)
        def tzname(self, dt):
            return "UTC"
        def dst(self, dt):
            return timedelta(0)
    utc = UTC()

# This represents the version in which we introduced the
# feature that prevents duplicate artifacts on the same incident.
# If we detect a version >= the number below, we do not need to go
# through the trouble of checking for duplicates manually when
# updating an incident.
RES_ARTIFACT_VERSION=37.1

class ResilientClient:
    """ ResilientClient component"""
    # Fields marked as read-only that aren't really..
    READ_ONLY_OVERRIDES = ['inc_training', ]
    resilient_client = None
    configuration = None
    logger = None
    EMAIL_MEMBER_MATCH = re.compile(r"([^\(]+\()(.+@.+)(?=\))")

    def __init__(self, logger, org_name=None, base_url=None, proxies=None, verify=None):
        self.logger = logger

    @staticmethod
    def htmlencode(value):
        return xml_escape(value)

    @staticmethod
    def attrencode(value):
        return xml_quoteattr(value)
    
    @staticmethod
    def get_ttl_hash(seconds=604800): # one week in seconds
        return round(time.time() / seconds)

    def connect(self, config, verify, password=None, api_key_secret=None):
        """Connect to resilient server using the config and password"""
        self.configuration = config

        url = "https://{}:{}".format(self.configuration.get("host", ""),
                                     self.configuration.get("port", 443))

        args = {"base_url": url,
                "verify": verify}
        org = self.configuration.get("org", None)
        if org:
            args["org_name"] = org

        # Utilize the BaseClient from co3base as our client
        self.resilient_client = resilient.BaseClient(**args)
        if api_key_secret:
            self.logger.info("Connecting to resilient server with API key ID and secret: " + str(args))
            self.resilient_client.set_api_key(self.configuration["user"], api_key_secret)
        elif password:
            self.logger.info("Connecting to resilient server with username and password: " + str(args))
            self.resilient_client.connect(self.configuration["user"], password)

        ret = False
        if self.resilient_client is not None:
            self.logger.info("Connected successfully.")
            ret = True

        return ret

    def get_fields(self, objecttype):
        """Retrieve information about fields for incident and artifact
        objecttype is either "incident" or "artifact"
        """
        if objecttype in ("incident", "artifact"):
            return self.resilient_client.get("/types/" + objecttype + "/fields")
        else:
            return None

    def is_field_present(self, objecttype, field):
        """
        Try to get the provided custom field from Resilient.
        If it exists, return True. Otherwise return false
        """
        try:
            res = self.resilient_client.get("/types/" + objecttype + "/fields/" + field)
            # if the platform send a response with an ID for the field, it exists
            if res["id"]:
                return True
            else:
                return False
        # 404's throw an exception
        except Exception:
            return False

    def extract_member(self, member):
        """ Keep just the email or group name
        """
        self.logger.info("Extract member(s) from " + str(member))

        match = self.EMAIL_MEMBER_MATCH.match(member)
        if match and len(match.groups()) == 2:
            # Extracted email
            self.logger.debug("Got email " + match.groups()[1])
            return match.groups()[1]
        else:
            # no email address found, assume the whole thing is a group name
            self.logger.debug("Got group " + member)
            return member

    def get_resilient_field_defs(self, incident_file):
        """Load field types and acceptable values from saved json file"""
        field_defs = {}

        FieldDef = namedtuple('FieldDef', ['field_type', 'valid_values', 'display_name', 'required'])

        with open(incident_file, 'r') as infile:
            data = infile.read()
            incident_json = json.loads(data)
            for field_def in incident_json:
                if field_def['read_only'] is True and field_def['name'] not in self.READ_ONLY_OVERRIDES:
                    # We can't map read-only fields.
                    continue
                fieldname = field_def['name']
                if field_def['prefix']:
                    fieldname = field_def['prefix'] + "." + fieldname
                required = field_def.get('required', '') == 'always'
                values = [value['label'] for value in field_def['values'] if value["enabled"] and not value["hidden"]] 
                field_defs[fieldname] = FieldDef(field_type=field_def['input_type'],
                                                 valid_values=values,
                                                 display_name=field_def['text'],
                                                 required=required)

        return field_defs

    @staticmethod
    def get_artifacts(configuration, limit):
        """Get artifact mappings from conf file data"""
        artifacts = []
        for key, value in configuration.items():
            if key.startswith('artifact') and key.endswith('value'):
                # parse the integer values from the string
                artifact_nbr = re.search("^[a-zA-Z]*([0-9]*)[a-zA-Z]*$", key).group(1)
                # Splunk does not let us delete values from the .conf file
                # If the user reduces the max number of artifacts, the .conf file
                # will have more artifacts in it than desired. Those artifacts are also
                # not visiable in the HTML, so the user will be confused when they appear
                # on the incident with values.
                # Skip artifact numbers that exceed the limit.
                if int(artifact_nbr) > limit:
                    continue
                artifact_type = configuration.get("artifact" + artifact_nbr + "type", "")
                description = configuration.get("artifact" + artifact_nbr + "description", "")
                if type and len(value) > 0:
                    artifacts.append({"value": value,
                                      "type": artifact_type,
                                      "description": description})
        return artifacts

    @staticmethod
    def fix_multiselect_values(mapping_config, incident_file, field_defs=None):
        """Convert CSV strings to lists of values"""
        if not field_defs:
            try:
                field_defs = ResilientClient.get_resilient_field_defs(incident_file)
            except IOError as e:
                #logger.error("Can't find resilient.json, so can't verify loaded conf values")
                return

        for fieldname, value in mapping_config.items():
            if value == "":
                # skip empty
                continue

            if fieldname in field_defs:
                # Artifacts and deleted fields won't be in there
                try:
                    # If a multiselect value contains a comma (the default delimiter), single
                    # quotes around the value (quotechar parameter) are used to delimit the value.  
                    if field_defs[fieldname].field_type in ("multiselect", "multiselect_members"):
                        values = csv.reader(value.splitlines(), skipinitialspace=True, quotechar="'")
                        new_values = []
                        for row in values:
                            for row_value in row:
                                new_values.append(row_value)

                        mapping_config[fieldname] = new_values
 
                except AttributeError:
                    # Handle the case where returned values have been cast to a list
                    # Already in the format we want
                    mapping_config[fieldname] = value

    @staticmethod
    def fix_boolean_values(mapping_config, incident_file, field_defs=None):
        """Splunk turns Yes/True/No/False into 1's and 0's. Fix them back"""
        if not field_defs:
            #incident_file = os.path.join(STATIC_DATA, 'resilient.json')
            try:
                field_defs = ResilientClient.get_resilient_field_defs(incident_file)
            except IOError as e:
                #logger.error("Can't find resilient.json, so can't verify loaded conf values")
                return

        for fieldname, value in mapping_config.items():
            if value == "":
                # No need to process empty value
                continue
            real_fieldname = fieldname.replace('mapping_', '')

            if real_fieldname not in field_defs:
                continue

            if field_defs[real_fieldname].field_type == "boolean":
                mapping_config[fieldname] = True if value in ('1', 1, 'true', 'True') else False

            elif value in ('1', '0', 1, 0):
                # This one might need to be changed back to its original value
                # Strip off our conf file prefix if necessary
                valid_values = field_defs[real_fieldname].valid_values
                if len(valid_values) > 0 and value not in valid_values:
                    if value in ('1', 1):
                        # Use the first possibility if we find one, else keep original value
                        possible_real_values = {'yes', 'Yes', 'true', 'True'} & set(valid_values)
                    else:
                        possible_real_values = {'no', 'No', 'false', 'False'} & set(valid_values)

                    real_value = possible_real_values.pop() if possible_real_values else value

                    mapping_config[fieldname] = real_value
                    #logger.debug("Field [%s] orig_value [%s] new_value [%s]",
                    #             fieldname, value, mapping_config[fieldname])

    def process_dt_value(self, value):
        # save intial input value so we can log it out at the end if needed
        inval = value

        # try to convert 3 supported input types, skip the remaining if one succeedes
        try:
            # parse a date string
            # convert seconds float to milliseconds int
            if sys.version_info.major < 3:
                # python 2
                value = int((datetime.datetime.strptime(value, '%Y/%m/%d') - datetime.datetime(1970, 1, 1)).total_seconds() * 1000)
            else:
                # python 3

                value = int(datetime.datetime.strptime(value, '%Y/%m/%d').timestamp() * 1000)
            return value
        except Exception:
            # could not parse as YYYY/MM/DD
            pass

        # try the next type
        try:
            # parse a datetime with (or without, it's optional to provide) timezone
            # convert seconds float to milliseconds int
            if sys.version_info.major < 3:
                # python2
                # parse the base of the datetime
                dt = datetime.datetime.strptime(value[:19], '%Y/%m/%d %H:%M:%S')
                # set timezone to utc
                dt = dt.replace(tzinfo=utc)

                # account for the offset if one is provided
                try:
                    offset_hours = int(value[21:23])
                    offset_mins = int(value[23:25])
                    offset_sign = value[20]
                    if offset_sign == '+':
                        dt -= timedelta(hours=offset_hours, minutes=offset_mins)
                    elif offset_sign == '-':
                        dt += timedelta(hours=offset_hours, minutes=offset_mins)
                except IndexError:
                    # no offset provided, assume GMT. nothing to do
                    pass
                except ValueError:
                    # no offset provided, assume GMT. nothing to do
                    pass

                # convert to mills
                value = int((dt - datetime.datetime(1970, 1, 1, 0, 0, 0, tzinfo=utc)).total_seconds() * 1000)
            else:
                # python3
                try:
                    value = int(datetime.datetime.strptime(value, '%Y/%m/%d %H:%M:%S %z').timestamp() * 1000)
                except ValueError:
                    # offest was not provided. set to utc
                    value = int(datetime.datetime.strptime(value, '%Y/%m/%d %H:%M:%S').replace(tzinfo=utc).timestamp() * 1000)
            return value
        except Exception as e:
            # could not parse as YYYY/MM/DD HH:MM:SS [%z]
            pass

        # try to convert epoch
        try:
            # convert seconds epoch to miliseconds epoch
            value = int(float(value) * 1000)
            return value
        except Exception as e:
            # all 3 conversion procedures failed if we have gotten this far without returning value
            self.logger.error("Unexpected datetime format encountered for: {}.\nWill attempt to create Resilient Incident without "
                              "at least one datetime field.\nThis will fail if the datetime field is required.".format(inval))
            self.logger.info("Datetime values are accepted in the following formats: "
                             "%Y/%m/%d, %Y/%m/%d %H:%M:%S %z, or epoch (in seconds).")
            self.logger.info("Datetimes stored in Splunk are represented as epochs in (seconds). "
                             "Check your alert configuration to ensure date and datetime values match one of the above formats.")
            # no need to raise an error.
            # if this is a required field, resilient will reject the POST request.
            # otherwise, the incident will be posted without this field.
            return

    def get_incident_artifacts(self, incident_id):
        uri = '/incidents/{}/artifacts'.format(incident_id)
        artifacts = self.resilient_client.get(uri)
        return artifacts

    @lru_cache()
    def getResilientVersion(self, ttl_hash=None):
        res = self.resilient_client.get_const()
        version = float("{}.{}".format(res["server_version"]["major"], res["server_version"]["minor"]))
        return version

    @lru_cache()
    def getArtifactDefs(self, ttl_hash=None):
        artifact_res = self.resilient_client.get("/artifact_types")
        return artifact_res

    def create_incident(self, mapping_config, artifacts, incident_file, update=False, existing_incident=None):
        """Create a new incident in Resilient"""
        res_version = self.getResilientVersion(ttl_hash=self.get_ttl_hash())

        incident_dict = defaultdict(dict)

        #incident_file = os.path.join(STATIC_DATA, 'resilient.json')
        field_defs = self.get_resilient_field_defs(incident_file)

        ResilientClient.fix_multiselect_values(mapping_config, incident_file, field_defs=field_defs)

        ResilientClient.fix_boolean_values(mapping_config, incident_file, field_defs=field_defs)

        #
        #   One common problem for using our Addon is that customer failed to find
        #   something valid to map to the required field "discovered_date". This
        #   results in an empty string for "discovered_date" and then escalation failed.
        #   We put in the current time for this if it is an empty string
        if mapping_config.get("discovered_date", None) == u'':
            mapping_config["discovered_date"] = str(time.time())

        for key, value in mapping_config.items():
            key_path = key.split('.')
            if key not in field_defs:
                # This must be a field that was deleted. Skip it.
                continue
            if value == "":
                # Skip empty value as well
                continue

            if value and field_defs[key].field_type in ('datepicker', 'datetimepicker'):
                value = self.process_dt_value(value)

            if value and field_defs[key].field_type in 'number':
                # These are numeric field types
                value = int(value)

            if key == "members":
                value = [self.extract_member(member) for member in value]
            elif key == "owner_id":
                value = self.extract_member(value)
            elif key == "description":
                value = {"format": "html",
                         "content": value}

            # mapping_config stores items like properties and pii as
            # properties.example_property and pii.exposure
            # However, the Resilient platform expects these as a dictionary
            # eg 'properties': {'splunk_notable_event_id': 'some-long-notable-ID-value'}
            if len(key_path) == 2:
                # Key has a prefix
                incident_dict[key_path[0]][key_path[1]] = value
            else:
                # Key is at top level
                incident_dict[key] = value

        if update:
            def update_fn(inc):
                inc.update(incident_dict)
                return inc
            incident = self.resilient_client.get_put("/incidents/{}".format(existing_incident['id']), update_fn)

            if res_version >= RES_ARTIFACT_VERSION:
                # v37.1 and higher prevents duplicate artifacts,
                # so we can just post them without checking any artifacts
                for artifact in artifacts:
                    self.resilient_client.post("/incidents/{}/artifacts".format(existing_incident['id']), artifact)
                return incident
            else:
                # get the artifact type definitions from Resilient
                artifact_res = self.getArtifactDefs(ttl_hash=self.get_ttl_hash())
                # create a dict of artifact type mapping from id to name
                # ex 7: "Email Attachment"
                artifact_types = {}
                for item in artifact_res['entities']:
                    artifact_types[item["id"]] = item["name"]

                # get the artifacts that are already associated with the target incident
                existing_artifacts = self.resilient_client.get("/incidents/{}/artifacts".format(existing_incident["id"]))
                
                # create a list of (value, type) tuples for the existing artifacts
                # we cast the int type to the programmatic name using the artifact_types dict
                values = []
                for artifact in existing_artifacts:
                    values.append((artifact['value'], artifact_types[artifact['type']]))

                # post the artifacts that don't match an existing (value, type) on the incident
                for artifact in artifacts:
                    tup = (artifact['value'], artifact['type'])
                    if tup not in values:
                        self.logger.info("posting artifact: " + repr(artifact))
                        self.resilient_client.post("/incidents/{}/artifacts".format(existing_incident['id']), artifact)
                return incident

        if len(artifacts) > 0:
            incident_dict["artifacts"] = artifacts

        if sys.version_info.major > 2:
            self.logger.info("INCIDENT TO POST: " + repr(incident_dict))
        else:
            # python2 REPL can not correctly interpret unicode inside a data container
            self.logger.info(
                # pylint: disable=no-member
                "INCIDENT TO POST: {" + "".join("u'%s': u'%s', " % (k, v) for k, v in incident_dict.iteritems()) + "}") 

        incident = self.resilient_client.post('/incidents', incident_dict)

        return incident

    @staticmethod
    def generate_alert_html(sa_action_name, field_def_dict, num_artifacts, artifact_types):
        """Generate the view for the resilient alert configuration"""
        TEMPLATE = """
           <form class="form-horizontal">
           <div class="control-group">
           <div class="controls" style="margin-left:40%; padding-left:10px; font-size:smaller; color:gray;">
           Enter a value to map for each incident field. This text can include tokens that will resolve to text based on search results.
           <a href="http://docs.splunk.com/Documentation/Splunk/6.3.3/AdvancedDev/ModAlertsIntro#About_token_replacement_in_custom_alert_actions" target="_blank"
           title="Splunk help">Learn More <i class="icon-external"></i></a></div>
           <br/>
           <div class="controls" style="margin-left:40%; padding-left:10px; color:red;"> * required</div>
           </div>
           {required_fields}
           {default_filled}
           {optional_fields}
           {artifacts}
           <br/>
           <div class="control-group">
           <div class="controls" style="margin-left:40%; padding-left:10px; color:green;">  + Field accommodates multiple comma-delimited selections.
           </div></div>


           </form>"""

        ARTIFACT_TEMPLATE = """<div class="control-group">
           <label class="control-label" for="{name}type" style="width:40%;">{display_name}</label>
           <div class="controls" style="margin-left:40%; padding-left:10px;">
           <span>
           <select style="width:90%;" name="action.{action_name}.param.{name}type" id="{name}type">
           {options}
           </select>
           <input style="width:90%;" name="action.{action_name}.param.{name}value" id="{name}value" placeholder="value"/>
           <input style="width:90%;" name="action.{action_name}.param.{name}description" id="{name}desc" placeholder="description"/>
           </span></div></div>"""

        TEXT_FIELD_TEMPLATE = """<div class="control-group">
           <label class="control-label" for="{name}" style="width:40%;">{display_name}</label>
           <div class="controls" style="margin-left:40%; padding-left:10px;">
           <input style="width:90%;" name="action.{action_name}.param.mapping_{name}" id="{name}"/>{required}
           </div></div>"""

        TEXT_AREA_FIELD_TEMPLATE = """<div class="control-group">
           <label class="control-label" for="{name}" style="width:40%;"> {display_name}</label>
           <div class="controls" style="margin-left:40%; padding-left:10px;">
           <input style="width:90%;" name="action.{action_name}.param.mapping_{name}" id="{name}"/>{required}
           </div></div>"""

        BOOLEAN_FIELD_TEMPLATE = """<div class="control-group">
           <label class="control-label" for="{name}" style="width:40%;">{display_name}</label>
           <div class="controls" style="margin-left:40%; padding-left:10px;">
           <input style="width:90%;" name="action.{action_name}.param.mapping_{name}" id="{name}" list="{name}list"/>{required}
           <datalist id="{name}list">
           <option value=""> </option>
           <option value="true">true</option>
           <option value="false">false</option>
           </datalist>
           </div></div>"""

        DATETIME_FIELD_TEMPLATE = """<div class="control-group">
           <label class="control-label" for="{name}" style="width:40%;">{display_name}</label>
           <div class="controls" style="margin-left:40%; padding-left:10px;">
           <input style="width:90%;" type="datetime-local" name="action.{action_name}.param.mapping_{name}" id="{name}"/>{required}
           </div></div>"""

        DATE_FIELD_TEMPLATE = """<div class="control-group">
           <label class="control-label" for="{name}" style="width:40%;">{display_name}</label>
           <div class="controls" style="margin-left:40%; padding-left:10px;">
           <input style="width:90%;" type="date" name="action.{action_name}.param.mapping_{name}" id="{name}"/>{required}
           </div></div>"""

        NUMBER_FIELD_TEMPLATE = """<div class="control-group">
           <label class="control-label" for="{name}" style="width:40%;">{display_name}</label>
           <div class="controls" style="margin-left:40%; padding-left:10px;">
           <input style="width:90%;" type="number" name="action.{action_name}.param.mapping_{name}" id="{name}"/>{required}
           </div></div>"""

        SELECT_FIELD_TEMPLATE = """<div class="control-group">
           <label class="control-label" for="{name}" style="width:40%;">{display_name}</label>
           <div class="controls" style="margin-left:40%; padding-left:10px;">
           <input style="width:90%;" name="action.{action_name}.param.mapping_{name}" id="{name}" list="{name}list"/>{required}
           <datalist id="{name}list">
           {options}
           </datalist>
           </div></div>"""

        # Multiselect doesn't work right now, just a copy of select
        # We would need to use javascript to accomplish this
        MULTISELECT_FIELD_TEMPLATE = """<div class="control-group">
           <label class="control-label" for="{name}" style="width:40%;">{display_name} <span style="color:green; font-size:larger;">+</span></label>
           <div class="controls" style="margin-left:40%; padding-left:10px;">
           <input style="width:90%;" name="action.{action_name}.param.mapping_{name}" id="{name}" list="{name}list"/>{required}
           <datalist id="{name}list">
           {options}
           </datalist>
           </div></div>"""

        # This one doesn't work b/c multiple tag is not XHTML compliant
        MULTISELECT_MEMBERS_FIELD_TEMPLATE = """<div class="control-group">
           <label class="control-label" for="{name}" style="width:40%;">{display_name} <span style="color:green; font-size:larger;">+</span></label>
           <div class="controls" style="margin-left:40%; padding-left:10px;">
           <input style="width:90%;" type="email" name="action.{action_name}.param.mapping_{name}" id="{name}" multiple list="{name}list"/>{required}
           <datalist id="{name}list">
           {options}
           </datalist>
           </div></div>"""

        OPTION_TEMPLATE = """<option value={attr}>{value}</option>"""

        REQUIRED_STR = """<span style="color:red;">*</span>"""

        # These are the fields that come with default values in alert_actions.conf
        DEFAULT_FILLED = ["Description", "Splunk Notable Event ID",
                          "Reporting Individual", "Simulation"]
        
        # List of some of the most common fields used when creating an incident
        # We will gather these and display close to the top to make the experience
        # feel a bit more similar to creating an incident in Resilient.
        STANDARD_FIELDS = ["Incident Type", "Incident Disposition", "Address", "City", "Country/Region", "Postal Code",
                            "Criminal Activity", "Exposure Type", "Department", "Negative PR", "Severity",
                            "Was personal information or personal data involved?", "Owner", "Date Determined"]

        # Map field type to a form field template
        template_dict = {"text": TEXT_FIELD_TEMPLATE,
                         "textarea": TEXT_AREA_FIELD_TEMPLATE,
                         "boolean": BOOLEAN_FIELD_TEMPLATE,
                         # "datepicker": DATE_FIELD_TEMPLATE,
                         "datepicker": TEXT_FIELD_TEMPLATE,
                         # "datetimepicker": DATETIME_FIELD_TEMPLATE,
                         "datetimepicker": TEXT_FIELD_TEMPLATE,
                         "number": NUMBER_FIELD_TEMPLATE,
                         "select": SELECT_FIELD_TEMPLATE,
                         "multiselect": MULTISELECT_FIELD_TEMPLATE,
                         # "multiselect_members": MULTISELECT_MEMBERS_FIELD_TEMPLATE,
                         "multiselect_members": MULTISELECT_FIELD_TEMPLATE,
                         "select_owner": SELECT_FIELD_TEMPLATE
                         }

        required_fields = []
        default_filled = []
        optional_fields = []

        for fieldname, field_def in sorted(field_def_dict.items()):
            template = template_dict[field_def.field_type]
            # Always allow nothing as a value as well   
            options = [OPTION_TEMPLATE.format(attr=ResilientClient.attrencode(value),
                                              value=ResilientClient.htmlencode(value)) for value in
                       [''] + field_def.valid_values]
            if field_def.required:
                # Required
                required_fields.append(template.format(action_name=sa_action_name,
                                                       name=fieldname,
                                                       display_name=ResilientClient.htmlencode(field_def.display_name),
                                                       options="\n".join(options) + "\n",
                                                       required=REQUIRED_STR))
            elif field_def.display_name in DEFAULT_FILLED or field_def.display_name in STANDARD_FIELDS:
                # Optional fields with default values
                default_filled.append(template.format(action_name=sa_action_name,
                                                      name=fieldname,
                                                      display_name=ResilientClient.htmlencode(field_def.display_name),
                                                      options="\n".join(options) + "\n",
                                                      required=""))
            else:
                # Other optional fields
                optional_fields.append(template.format(action_name=sa_action_name,
                                                       name=fieldname,
                                                       display_name=ResilientClient.htmlencode(field_def.display_name),
                                                       options="\n".join(options) + "\n",
                                                       required=""))

        artifacts = []
        # allow for no selection as well so the user can "unset" artifact type selection
        options = [OPTION_TEMPLATE.format(attr=ResilientClient.attrencode(value),
                                          value=ResilientClient.htmlencode(value)) for value in [''] + artifact_types]
        for i in range(num_artifacts):
            artifact_nbr = i + 1
            artifacts.append(ARTIFACT_TEMPLATE.format(action_name=sa_action_name,
                                                      name="artifact%d" % artifact_nbr,
                                                      display_name="Artifact %d" % artifact_nbr,
                                                      options="\n".join(options) + "\n"))
        generated_html = TEMPLATE.format(required_fields="\n".join(required_fields),
                                         default_filled="\n".join(default_filled),
                                         optional_fields="\n".join(optional_fields),
                                         artifacts="\n".join(artifacts))
        return generated_html
