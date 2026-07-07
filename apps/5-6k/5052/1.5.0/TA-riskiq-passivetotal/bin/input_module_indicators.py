"""Indicators data collection."""
# encoding = utf-8
import os
import sys

import passivetotal_utils as utils
from passivetotal_collect import PassiveTotalCollect
from threadpool import ThreadPool


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    pass


def collect_indicators_data(helper, ew, indicator, dataset):
    """Collect all datasets using threading."""
    helper.log_info("Starting the thread for dataset={} indicator={}".format(dataset, indicator))
    pt_collect = PassiveTotalCollect(helper, ew, indicator, dataset)
    pt_collect.start_data_collection()


def collect_events(helper, ew):
    """Collect indicators data."""
    input_name = helper.get_input_stanza_names()
    helper.log_info("Starting data collection for input {}".format(input_name))
    # Fetch common details for all api calls
    try:
        session_key = helper.context_meta["session_key"]

        username, password = utils.get_pt_config(session_key)
        if not username or not password:
            helper.log_warning('No account configured. Configure PassiveTotal account in the "Configuration" dashboard of Add-on.')
            sys.exit(1)

        file_name = helper.get_arg("file_name")
        csv_file_path = os.path.join(utils.CSV_STORAGE_PATH, file_name)
        indicators = utils.return_indicators_from_file(csv_file_path, helper)

        datasets = helper.get_arg("dataset")
        if not datasets:
            datasets = []

        if not indicators and ('articles' not in datasets):
            helper.log_warning("No indicators available. Stopping data collection")
            sys.exit(1)

        pool = ThreadPool(utils.MAX_WORKER_THREADS, helper=helper)
        # Complexity will be indicators * datasets

        if 'articles' in datasets:
            pool.add_task(collect_indicators_data, helper, ew, 'NULL', 'articles')
            datasets.remove('articles')

        if indicators:
            for indicator in indicators:
                for dataset in datasets:
                    pool.add_task(collect_indicators_data, helper, ew, indicator, dataset)

        pool.wait_completion()
        helper.log_info("Data collection process is completed for input {}".format(input_name))

    except Exception as e:
        helper.log_error("Error occured while collecting data {}".format(e))
