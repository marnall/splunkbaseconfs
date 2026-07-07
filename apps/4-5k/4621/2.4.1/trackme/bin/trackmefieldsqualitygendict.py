#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

import os
import sys
import time
import json
import logging
from logging.handlers import RotatingFileHandler
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_trackmefieldsqualitygendict.log" % splunkhome,
    mode="a",
    maxBytes=10000000,
    backupCount=1,
)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(filename)s %(funcName)s %(lineno)d %(message)s"
)
logging.Formatter.converter = time.gmtime
filehandler.setFormatter(formatter)
log = logging.getLogger()  # root logger - Good to get it only once.
for hdlr in log.handlers[:]:  # remove the existing file handlers
    if isinstance(hdlr, logging.FileHandler):
        log.removeHandler(hdlr)
log.addHandler(filehandler)  # set the new handler
# set the log level to INFO, DEBUG as the default is ERROR
log.setLevel(logging.INFO)

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# import trackme libs
from trackme_libs import (
    trackme_reqinfo,
    run_splunk_search,
)

# import trackme libs utils
from trackme_libs_utils import remove_leading_spaces

# import trackme licensing libs
from trackme_libs_licensing import trackme_check_license


@Configuration(distributed=False)
class TrackMeFieldsQualityGenDict(GeneratingCommand):

    datamodel = Option(
        doc="""
        **Syntax:** **datamodel=****
        **Description:** The name of the datamodel.""",
        require=True,
        default=None,
        validate=validators.Match("datamodel", r"^.*$"),
    )

    show_only_recommended_fields = Option(
        doc="""
        **Syntax:** **show_only_recommended_fields=****
        **Description:** Boolean option to only include recommended fields.
        """,
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    allow_unknown = Option(
        doc="""
        **Syntax:** **allow_unknown=****
        **Description:** Boolean option to allow unknown field values.
        """,
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    allow_empty_or_missing = Option(
        doc="""
        **Syntax:** **allow_empty_or_missing=****
        **Description:** Boolean option to allow empty or missing field values.
        """,
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    # status will be statically defined as imported

    def generate(self, **kwargs):

        # Start performance counter
        start = time.time()

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key, self._metadata.searchinfo.splunkd_uri
        )
        log.setLevel(reqinfo["logging_level"])

        # check license state
        try:
            check_license = trackme_check_license(
                reqinfo["server_rest_uri"], self._metadata.searchinfo.session_key
            )
            license_is_valid = check_license.get("license_is_valid")
            logging.debug(
                f'function check_license called, response="{json.dumps(check_license, indent=2)}"'
            )

        except Exception as e:
            license_is_valid = 0
            logging.error(f'function check_license exception="{str(e)}"')

        # check restricted components
        if license_is_valid != 1:
            logging.error(
                f'The requested component is restricted to the Full and Trial edition mode, its execution cannot be accepted, check_license="{json.dumps(check_license, indent=2)}"'
            )
            raise Exception(
                f"The requested component is restricted to the Full and Trial edition mode, its execution cannot be accepted, please contact your Splunk administrator."
            )

        # results_records
        results_records = []
        records_count = 0

        # set the search
        search = remove_leading_spaces(
            f"""
            | datamodel {self.datamodel} | spath 
            | spath path=objects{{}}.fields{{}} output=v 
            | spath path=objects{{}}.calculations{{}}.outputFields{{}} output=u 
            | eval w=mvappend(v,u) 
            | fields - _raw | fields modelName w
            | mvexpand w 
            | eval field=json_extract(w,"fieldName")
            | lookup trackme_cim_recommended_fields field OUTPUT is_recommended 
            | eval recommended=json_extract(w,"comment.recommended"), recommended=if(is_recommended=="true" OR match(recommended, "(?i)true|1"), "true", "false")
            | rename modelName AS datamodel
            | stats values(recommended) AS recommended by datamodel, field
            | eval recommended=if(match(recommended, "true"), "true", "false")
            | where NOT match(field, "_time|^host$|sourcetype|source|[A-Z]+|_bunit|_category|_priority|_requires_av|_should_update") OR match(field, "object_category")
            | lookup trackme_cim_regex_v2 datamodel field OUTPUT validation_regex
            | eval validation_regex=if(isnull(validation_regex) OR validation_regex=="", ".*", validation_regex)
        """
        )
        logging.debug(f"search={search}")

        # kwargs
        kwargs_search = {
            "earliest_time": "-5m",
            "latest_time": "now",
            "preview": "false",
            "output_mode": "json",
            "count": 0,
        }

        # run the search
        try:
            reader = run_splunk_search(
                self.service,
                search,
                kwargs_search,
                24,
                5,
            )

            for item in reader:
                if isinstance(item, dict):
                    # get fields values for datamodel, field, recommended, validation_regex
                    datamodel = item.get("datamodel", "")
                    field = item.get("field", "")
                    recommended = item.get("recommended", "")
                    validation_regex = item.get("validation_regex", "")

                    # add to results_records
                    if self.show_only_recommended_fields:
                        if recommended == "false":
                            continue

                    results_records.append(
                        {
                            "_time": time.time(),
                            "datamodel": datamodel,
                            "field": field,
                            "recommended": recommended,
                            "validation_regex": validation_regex,
                            "_raw": json.dumps(item),
                        }
                    )

                    # add to results_records
                    records_count += 1

        except Exception as e:
            error_msg = f'context="error", trackmefieldsqualitygendict has failed with exception="{str(e)}"'
            logging.error(error_msg)
            raise Exception(error_msg)

        # yield the results
        # Build the json_dict
        json_dict = {}
        for record in results_records:
            field_name = record["field"]
            regex = record["validation_regex"]
            # Use json.dumps to escape the regex for JSON
            json_dict[field_name] = {
                "name": field_name,
                "regex": regex,
                "allow_unknown": self.allow_unknown,
                "allow_empty_or_missing": self.allow_empty_or_missing,
            }

        # Convert the dict to a JSON string (ensure proper escaping)
        json_dict_str = json.dumps(json_dict, ensure_ascii=False)

        # Yield a single record with the json_dict field
        yield {
            "_time": time.time(),
            "datamodel": self.datamodel,
            "json_dict": json_dict_str,
            "_raw": json.dumps(json_dict),
        }

        # Log the run time
        logging.info(
            f'context="perf", trackmefieldsquality has terminated, records_count="{records_count}", run_time="{round((time.time() - start), 3)}"'
        )


dispatch(TrackMeFieldsQualityGenDict, sys.argv, sys.stdin, sys.stdout, __name__)
