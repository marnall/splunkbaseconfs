import datetime

from splunk_api import SplunkApiClient, APP_NAME


class ResultsProcessor(SplunkApiClient):
    def submit_analytic_hits(self):
        if self.send_stats:
            last_checkpoint = self.fetch_checkpoint()
            search_args = {
                'dispatch.index_earliest': f'-{int(datetime.datetime.now().timestamp() - last_checkpoint) - 1}s@s',
                'dispatch.index_latest': 'now',
                'args.fields_filter': self.fields_filter()
            }
            results = self.dispatch_saved_search('Detection Hits', raise_for_failure=True, **search_args)
            self.upload_analytic_hits(results)
            return dict(last_checkpoint=last_checkpoint, new_analytic_hits=len(results))
        else:
            return dict(last_checkpoint=0, new_analytic_hits=0)
