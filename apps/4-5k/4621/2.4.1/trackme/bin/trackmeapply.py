#!/usr/bin/env python
# coding=utf-8

"""
TrackMe Native Apply Command

A Splunk custom streaming command that applies a previously fitted native density
function model to piped data, replacing Splunk's MLTK '| apply model_name' command.

Usage in SPL:
    | mstats avg(trackme.metric) as metric where ... by object span=1h
    | eval factor=strftime(_time, "%H")
    | trackmeapply model_name="model_name" tenant_id="xxx"

    - model_name: the model to load and apply
    - tenant_id: tenant identifier (required for KVstore model loading)
    - model_storage: "kvstore" or "file". Default: "kvstore"

Output: augments each input row with BoundaryRanges, LowerBound, UpperBound, IsOutlier fields.
"""

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import os
import sys
import time
import json

# Logging imports
import logging
from logging.handlers import RotatingFileHandler

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# set logging
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_splk_native_apply.log" % splunkhome,
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

# Import Splunk libs
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
    Option,
    validators,
)

# Import native ML library
from trackme_libs_mlnative import (
    native_apply,
    load_model_from_kvstore,
    get_model_collection_name,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo


@Configuration(distributed=False)
class NativeApplyCommand(StreamingCommand):
    """TrackMe native density function apply command."""

    model_name = Option(
        doc="""
        **Syntax:** **model_name=****
        **Description:** The name of the saved model to apply.""",
        require=True,
    )

    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** Tenant identifier (required for KVstore model loading).""",
        require=False,
        default=None,
    )

    model_storage = Option(
        doc="""
        **Syntax:** **model_storage=****
        **Description:** Model storage backend: "kvstore" (default) or "file".""",
        require=False,
        default="kvstore",
        validate=validators.Match("model_storage", r"^(kvstore|file)$"),
    )

    def stream(self, records):
        """Process all input records, apply the model, and yield augmented records."""

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
        )
        log.setLevel(reqinfo["logging_level"])

        start_time = time.time()
        model_name = self.model_name.strip('"').strip("'")

        logging.info(
            f'Starting native apply: model_name="{model_name}", '
            f'tenant_id="{self.tenant_id}", model_storage="{self.model_storage}"'
        )

        # Load the model
        model = None

        if self.model_storage == "kvstore" and self.tenant_id:
            try:
                collection_name = get_model_collection_name(self.tenant_id)
                model = load_model_from_kvstore(
                    self.service, collection_name, model_name, logging
                )
                if model:
                    logging.info(f'Model "{model_name}" loaded from KVstore')
            except Exception as e:
                logging.warning(f'Failed to load model from KVstore: {e}')

        # Fallback to file-based if KVstore failed or file mode requested
        if model is None:
            try:
                model = self._load_model_from_file(model_name)
                if model:
                    logging.info(f'Model "{model_name}" loaded from file')
            except Exception as e:
                logging.warning(f'Failed to load model from file: {e}')

        if model is None:
            logging.error(
                f'Model "{model_name}" not found in KVstore or file. '
                f'The model may not have been trained yet.'
            )
            # Yield rows unchanged with error marker
            for record in records:
                row = dict(record)
                row["BoundaryRanges"] = ""
                row["LowerBound"] = 0
                row["UpperBound"] = 0
                row["IsOutlier"] = 0
                row["_native_apply_error"] = f"Model '{model_name}' not found"
                yield row
            return

        # Collect all records
        all_rows = []
        for record in records:
            all_rows.append(dict(record))

        if not all_rows:
            logging.warning("No input records received for native apply.")
            return

        # Apply the model
        try:
            result_rows = native_apply(all_rows, model)
        except Exception as e:
            logging.error(f"Native apply failed: {e}")
            for row in all_rows:
                row["BoundaryRanges"] = ""
                row["LowerBound"] = 0
                row["UpperBound"] = 0
                row["IsOutlier"] = 0
                row["_native_apply_error"] = str(e)
                yield row
            return

        elapsed = round(time.time() - start_time, 3)
        logging.info(
            f'Native apply completed: model_name="{model_name}", '
            f'rows={len(result_rows)}, elapsed={elapsed}s'
        )

        # Yield augmented rows
        for row in result_rows:
            yield row

    def _load_model_from_file(self, model_name):
        """Load model from a file in the Splunk lookups directory."""
        lookups_dir = os.path.join(
            splunkhome, "etc", "users", "splunk-system-user", "trackme", "lookups"
        )
        # Sanitize model_name to prevent path traversal
        safe_name = os.path.basename(model_name)
        filename = f"__mlspl_{safe_name}.mlmodel"
        filepath = os.path.join(lookups_dir, filename)

        if not os.path.exists(filepath):
            return None

        with open(filepath, "r") as f:
            return json.load(f)


dispatch(NativeApplyCommand, sys.argv, sys.stdin, sys.stdout, __name__)
