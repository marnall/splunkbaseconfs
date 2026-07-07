#!/usr/bin/env python
# coding=utf-8

"""
TrackMe Native Fit Command

A Splunk custom streaming command that fits a native density function model
to piped data, replacing Splunk's MLTK '| fit DensityFunction' command.

Usage in SPL:
    | mstats avg(trackme.metric) as metric where ... by object span=1h
    | eval factor=strftime(_time, "%H")
    | trackmefit feature="metric" by="factor" lower_threshold=0.005 upper_threshold=0.005 into="model_name" tenant_id="xxx"

    - feature: the numeric field to model
    - by: grouping field (typically "factor" for time-based segmentation)
    - lower_threshold: density threshold for lower bound
    - upper_threshold: density threshold for upper bound
    - into: model name for persistence (optional, omit for inline fit)
    - tenant_id: tenant identifier (required for KVstore persistence)
    - dist_type: distribution type (auto, norm, expon, gaussian_kde, beta). Default: auto
    - exclude_dist: comma-separated distributions to exclude from auto-selection
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
    "%s/var/log/splunk/trackme_splk_native_fit.log" % splunkhome,
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
    native_fit,
    native_apply,
    save_model_to_kvstore,
    get_model_collection_name,
)

# Import trackme libs
from trackme_libs import trackme_reqinfo


@Configuration(distributed=False)
class NativeFitCommand(StreamingCommand):
    """TrackMe native density function fit command."""

    feature = Option(
        doc="""
        **Syntax:** **feature=****
        **Description:** The numeric field name to fit the density function on.""",
        require=True,
        validate=validators.Match("feature", r"^[a-zA-Z0-9_.\-]+$"),
    )

    by = Option(
        doc="""
        **Syntax:** **by=****
        **Description:** Optional grouping field name (e.g. "factor" for time-based segmentation).""",
        require=False,
        default=None,
    )

    lower_threshold = Option(
        doc="""
        **Syntax:** **lower_threshold=****
        **Description:** Density threshold for the lower bound (e.g. 0.005).""",
        require=False,
        default="0.005",
    )

    upper_threshold = Option(
        doc="""
        **Syntax:** **upper_threshold=****
        **Description:** Density threshold for the upper bound (e.g. 0.005).""",
        require=False,
        default="0.005",
    )

    into = Option(
        doc="""
        **Syntax:** **into=****
        **Description:** Model name for persistence. If provided, the model is saved to KVstore or file. If omitted, the fit is inline only.""",
        require=False,
        default=None,
    )

    tenant_id = Option(
        doc="""
        **Syntax:** **tenant_id=****
        **Description:** Tenant identifier (required for KVstore model persistence).""",
        require=False,
        default=None,
    )

    dist_type = Option(
        doc="""
        **Syntax:** **dist_type=****
        **Description:** Distribution type: auto (default), norm, expon, gaussian_kde, beta, or DensityFunction (alias for auto).""",
        require=False,
        default="auto",
    )

    exclude_dist = Option(
        doc="""
        **Syntax:** **exclude_dist=****
        **Description:** Comma-separated list of distributions to exclude from auto-selection (e.g. "beta,expon").""",
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
        """Process all input records, fit the model, and yield augmented records."""

        # Get request info and set logging level
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
        )
        log.setLevel(reqinfo["logging_level"])

        start_time = time.time()

        # Parse thresholds - must be positive for valid ppf() computation
        try:
            lower_t = float(self.lower_threshold)
            if lower_t <= 0 or lower_t >= 1:
                logging.warning(f'Invalid lower_threshold={lower_t}, must be in (0, 1), using 0.005')
                lower_t = 0.005
        except (ValueError, TypeError):
            lower_t = 0.005
        try:
            upper_t = float(self.upper_threshold)
            if upper_t <= 0 or upper_t >= 1:
                logging.warning(f'Invalid upper_threshold={upper_t}, must be in (0, 1), using 0.005')
                upper_t = 0.005
        except (ValueError, TypeError):
            upper_t = 0.005

        # Parse group fields
        group_fields = []
        if self.by:
            # Remove quotes if present
            by_clean = self.by.strip('"').strip("'")
            group_fields = [f.strip() for f in by_clean.split(",") if f.strip()]

        # Parse exclude_dist
        exclude_dist = None
        if self.exclude_dist:
            exclude_dist = [d.strip().strip('"').strip("'") for d in self.exclude_dist.split(",") if d.strip()]

        # Collect all records first (we need all data to fit)
        all_rows = []
        for record in records:
            all_rows.append(dict(record))

        if not all_rows:
            logging.warning("No input records received for native fit.")
            return

        logging.info(
            f'Starting native fit: feature="{self.feature}", by="{self.by}", '
            f'lower_threshold={lower_t}, upper_threshold={upper_t}, '
            f'dist_type="{self.dist_type}", rows={len(all_rows)}'
        )

        # Perform the fit
        try:
            model = native_fit(
                data_values=all_rows,
                group_values=group_fields,
                feature_name=self.feature,
                lower_threshold=lower_t,
                upper_threshold=upper_t,
                dist_type=self.dist_type,
                exclude_dist=exclude_dist,
            )
        except Exception as e:
            logging.error(f"Native fit failed: {e}")
            # Yield rows unchanged with error indicator
            for row in all_rows:
                row["BoundaryRanges"] = ""
                row["LowerBound"] = 0
                row["UpperBound"] = 0
                row["IsOutlier"] = 0
                row["_native_fit_error"] = str(e)
                yield row
            return

        # Save the model if "into" is specified
        if self.into:
            model_name = self.into.strip('"').strip("'")

            if self.model_storage == "kvstore" and self.tenant_id:
                try:
                    collection_name = get_model_collection_name(self.tenant_id)
                    save_model_to_kvstore(
                        self.service, collection_name, model_name, model, logging
                    )
                    logging.info(f'Model "{model_name}" saved to KVstore collection "{collection_name}"')
                except Exception as e:
                    logging.error(f'Failed to save model to KVstore: {e}')
                    # Try file-based fallback
                    try:
                        self._save_model_to_file(model_name, model)
                        logging.info(f'Model "{model_name}" saved to file (KVstore fallback)')
                    except Exception as e2:
                        logging.error(f'File-based fallback also failed: {e2}')

            elif self.model_storage == "file" or not self.tenant_id:
                try:
                    self._save_model_to_file(model_name, model)
                    logging.info(f'Model "{model_name}" saved to file')
                except Exception as e:
                    logging.error(f'Failed to save model to file: {e}')

        # Apply the model to the input data to produce boundaries
        try:
            result_rows = native_apply(all_rows, model)
        except Exception as e:
            logging.error(f"Native apply after fit failed: {e}")
            # Yield rows unchanged with error indicator
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
            f'Native fit completed: feature="{self.feature}", '
            f'groups={len(model.get("groups", {}))}, rows={len(result_rows)}, '
            f'elapsed={elapsed}s'
        )

        # Yield augmented rows
        for row in result_rows:
            yield row

    def _save_model_to_file(self, model_name, model):
        """Save model to a file in the Splunk lookups directory (file-based fallback)."""
        lookups_dir = os.path.join(
            splunkhome, "etc", "users", "splunk-system-user", "trackme", "lookups"
        )
        os.makedirs(lookups_dir, exist_ok=True)

        # Sanitize model_name to prevent path traversal
        safe_name = os.path.basename(model_name)
        filename = f"__mlspl_{safe_name}.mlmodel"
        filepath = os.path.join(lookups_dir, filename)

        with open(filepath, "w") as f:
            json.dump(model, f, indent=2)


dispatch(NativeFitCommand, sys.argv, sys.stdin, sys.stdout, __name__)
