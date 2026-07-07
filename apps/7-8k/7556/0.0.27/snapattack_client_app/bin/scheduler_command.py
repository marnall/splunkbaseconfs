import os
import sys

sys.path.insert(0, os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'lib'))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration

from jobs import Scheduler


@Configuration()
class JobSchedulerCommand(GeneratingCommand):
    def generate(self):
        self.logger.debug('Scheduling SnapAttack search jobs')
        token = self._metadata.searchinfo.session_key
        processor = Scheduler(splunk_session_key=token)
        results = processor.schedule_jobs()
        for result in results:
            yield result


dispatch(JobSchedulerCommand, sys.argv, sys.stdin, sys.stdout, __name__)