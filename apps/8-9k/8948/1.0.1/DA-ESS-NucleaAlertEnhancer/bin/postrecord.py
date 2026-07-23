import sys
import json
from splunklib.client import Service
from splunklib.searchcommands import (
    dispatch, StreamingCommand, Configuration, Option, validators
)

@Configuration()
class PostRecord(StreamingCommand):
    finding_id_field = Option(
        doc='Finding ID Field',
        require=True,
        validate=validators.Fieldname()
    )
    
    response_field = Option(
        doc='LLM Response text',
        require=True,
        validate=validators.Fieldname()
    )

    def stream(self, records):
            for record in records:
                actual_finding_id = record.get(self.finding_id_field)
                actual_response = record.get(self.response_field)

                if not actual_finding_id or not actual_response:
                    record['api_status'] = 'skipped'
                    record['api_error'] = 'Missing required fields in this event'
                    yield record
                    continue

                endpoint = f"/servicesNS/nobody/missioncontrol/public/v2/investigations/{actual_finding_id}/notes"
                payload = {
                    "title": "# Resposta gerado via Nuclea Alert Enhancer",
                    "content": actual_response
                }

                try:
                    response = self.service.post(
                        endpoint,
                        headers=[('Content-Type', 'application/json')],
                        body=json.dumps(payload)
                    )
                    
                    status = 'success'
                    error_msg = None
                    
                except Exception as e:
                    status = 'error'
                    error_msg = str(e)

                record['api_status'] = status
                if error_msg:
                    record['api_error'] = error_msg
                    
                yield record

if __name__ == "__main__":
    dispatch(PostRecord, sys.argv, sys.stdin, sys.stdout, __name__)