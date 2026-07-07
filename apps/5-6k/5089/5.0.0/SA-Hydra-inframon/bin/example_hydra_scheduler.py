import sys

from hydra_inframon.hydra_scheduler import HydraScheduler
from hydra_inframon.models import HydraCollectionStanza


class ExampleHydraScheduler(HydraScheduler):
    title = "Example Hydra Scheduler"
    description = "Example of distributed work scheduler implementation. Note this will do nothing valuable; it's just a code example"
    collection_model = HydraCollectionStanza
    app = "SA-Hydra-inframon"
    collection_conf_name = "hydra_collection.conf"
    worker_input_name = "example_hydra_worker"


if __name__ == '__main__':
    scheduler = ExampleHydraScheduler()
    scheduler.execute()
    sys.exit(0)
