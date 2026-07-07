#!/usr/bin/env python
# coding=utf-8
#
# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.

import sys

# Add SA-Hydra packages to sys.path
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Hydra', 'bin']))

from ta_ontap.models import TAOntapCollectionStanza
from hydra.hydra_scheduler import HydraScheduler


class TAOntapScheduler(HydraScheduler):
    """
    TA-Ontap implementation of the HydraScheduler. Breaks up collection conf and
    distributes it to all worker nodes.
    Significant overloads:
        None as yet.
    """
    title = "TA-Ontap Collection Scheduler"
    description = "Breaks up the TA-Ontap collection into config tokens and distributes jobs to all worker nodes. Should only have 1 of these active at a time."
    collection_model = TAOntapCollectionStanza
    app = "Splunk_TA_ontap"
    collection_conf_name = "ta_ontap_collection.conf"
    worker_input_name = "ta_ontap_collection_worker"


if __name__ == '__main__':
    scheduler = TAOntapScheduler()
    scheduler.execute()
    sys.exit(0)
