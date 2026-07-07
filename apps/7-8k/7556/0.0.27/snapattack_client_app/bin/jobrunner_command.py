import os
import sys

sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'lib'))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

from jobs import RankJobProcessor, ImportJobProcessor


@Configuration()
class JobRunnerCommand(GeneratingCommand):
    guid = Option(require=True)
    type = Option(require=True)

    @property
    def job_runner(self):
        """Map the job type to the processor class"""
        map = {
            'Rank': RankJobProcessor,
            'Hunt': RankJobProcessor,
            'Test': RankJobProcessor,
            'IOC': RankJobProcessor,
            'Import': ImportJobProcessor,
        }
        return map.get(self.type)

    def generate(self):
        self.logger.debug('Processing SnapAttack search jobs')
        token = self._metadata.searchinfo.session_key
        processor = self.job_runner(splunk_session_key=token, guid=self.guid)
        results = processor.process_job()
        for result in results:
            yield result


dispatch(JobRunnerCommand, sys.argv, sys.stdin, sys.stdout, __name__)
