import sys
from splunklib.searchcommands import dispatch, EventingCommand, Configuration

@Configuration()
class ExEventsCommand(EventingCommand):
    def transform(self, records):
        new_results=[]
        flows = {}
        list_results = list(records)

        for result in list_results:
            key = result['Destination IP Address'] + result['Source IP Address']

            # Check if already a flow is present
            if flows.get(key):
                new_results[flows[key]]['Total Bytes'] = str(long(new_results[flows[key]]['Total Bytes']) + long(result['Total Bytes']))

            else:
                key = result['Source IP Address'] + result['Destination IP Address']
                new_results.append(result)
                flows[key] = len(new_results) - 1

        return new_results
if __name__ == "__main__":
    dispatch(ExEventsCommand, sys.argv, sys.stdin, sys.stdout, __name__)