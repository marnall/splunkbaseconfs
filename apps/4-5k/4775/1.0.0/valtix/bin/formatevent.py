import json
import splunk.Intersplunk

# get the previous search results
results = splunk.Intersplunk.getOrganizedResults()

fields = ['timestamp', 'level', 'sessionId', 'accountName', 'action', 'cspName', 'status', 'type', 'statusText',
          {'connection': ['destIp', 'dstPort', 'protocol', 'srcIp', 'srcPort'], 'rule': ['id', 'ruleText', 'type'],
           'direction': ['type']}]

try:
    output_events = []
    results_json = results[0]
    raw_count = 0
    for i in results_json:
        expanded_events = []
        raw_events_str = json.loads(json.loads(json.dumps(i['_raw'])))
        raw_count += 1
        repeated_events = raw_events_str.get("repeatedEvents", [])
        event = {}
        for field in fields:
            if type(field) == str:
                event[field] = raw_events_str.get(field, '')
            elif type(field) == dict:
                for custom_field in field:
                    for inner_field in field[custom_field]:
                        event[custom_field + "." + inner_field] = raw_events_str.get(
                            custom_field, {}).get(inner_field, "")
        output_events.append(event)
        if repeated_events:
            for repeated_event in repeated_events:
                event = {}
                for field in fields:
                    if type(field) == str:
                        if repeated_event.get(field):
                            event[field] = repeated_event.get(field)
                        else:
                            event[field] = raw_events_str.get(field, '')
                    elif type(field) == dict:
                        for custom_field in field:
                            for inner_field in field[custom_field]:
                                if repeated_event.get(custom_field, {}).get(inner_field):

                                    event[custom_field + "." +
                                          inner_field] = repeated_event.get(custom_field, {}).get(inner_field)
                                else:
                                    event[custom_field + "." + inner_field] = raw_events_str.get(
                                        custom_field, {}).get(inner_field, "")
                output_events.append(event)
    splunk.Intersplunk.outputResults(output_events)
except KeyError as e:
    splunk.Intersplunk.generateErrorResults("KeyError: Cannot find the key '" + e.message + "' in the events")
except ValueError as e:
    splunk.Intersplunk.generateErrorResults("ValueError: The event is not in a valid format")
except Exception as e:
    splunk.Intersplunk.generateErrorResults("Error while formating the events")
