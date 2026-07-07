# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.
import sys
import time
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))

from ITOA.setup_logging import setup_logging, InstrumentCall
from SA_ITOA_app_common.splunklib.searchcommands import Configuration, GeneratingCommand, dispatch
from itsi.duplicate_entities_manager.duplicate_entities_nightly_job_scheduler_job import \
    DuplicateEntitiesNightlyJobSchedulerJob

logger = setup_logging('itsi_duplicate_entities_generate_job_enqueuer.log',
                       'itsi_duplicate_entities_generate_job_enqueuer')
logger.info("Initialized duplicate entities generate job enqueuer log")


@Configuration()
class EnqueueDuplicateEntitiesGenerateJob(GeneratingCommand):

    def __init__(self):
        super().__init__()
        self.transaction_id = None
        self._instrumentation = InstrumentCall(logger)

    def generate(self):
        try:
            with self._instrumentation.track(
                    'EnqueueDuplicateEntitiesGenerateJob.generate'
            ) as transaction_id:
                self.transaction_id = transaction_id
                logger.info(f'tid={self.transaction_id} Enqueueing duplicate entities generate job')
                result = self.enqueue_job()

            data_to_return = {
                'tid': self.transaction_id,
                '_raw': 'Enqueue of duplicate entities generation job successful.',
                'job_key': result['_key'],
                '_time': time.time()
            }
            logger.info(data_to_return)
            yield data_to_return

        except Exception as e:
            data_to_return = {
                'tid': self.transaction_id,
                '_raw': f'Error while enqueueing duplicate entities generate job. Error = {e}',
                'log_level': 'ERROR',
                '_time': time.time()
            }
            logger.error(data_to_return)
            # Explicitly specify Exception message due to missing Python3 support in error_exit()
            self.error_exit(e, message=str(e))

    def enqueue_job(self):
        job_scheduler = DuplicateEntitiesNightlyJobSchedulerJob(session_key=self.service.token)
        enqueue_result = job_scheduler.enqueue_job("SEARCH_COMMAND")
        return enqueue_result


dispatch(EnqueueDuplicateEntitiesGenerateJob, sys.argv, sys.stdin, sys.stdout, __name__)
