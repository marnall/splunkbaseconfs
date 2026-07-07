import sys

from splunklib.searchcommands import Configuration, EventingCommand, dispatch


@Configuration()
class EventingCSC(EventingCommand):
    """Calculate total bytes transferred between source IP address and destination IP address."""

    def transform(self, records):
        """Transform events."""
        new_results = []
        flows = {}
        list_results = list(records)

        for result in list_results:
            key = result["Destination IP Address"] + result["Source IP Address"]
            # Check if a flow is already present
            if flows.get(key):
                new_results[flows[key]]["Total_Bytes"] = str(
                    int(new_results[flows[key]]["Total_Bytes"]) + int(result["Total_Bytes"])
                )
            else:
                key = result["Source IP Address"] + result["Destination IP Address"]
                new_results.append(result)
                flows[key] = len(new_results) - 1
        return new_results


dispatch(EventingCSC, sys.argv, sys.stdin, sys.stdout, __name__)
