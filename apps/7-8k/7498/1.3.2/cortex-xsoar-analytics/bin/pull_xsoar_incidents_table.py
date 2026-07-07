
from xsoar_module import XSOAR
from constants import WIDGET_CONFIG, XSOAR_WIDGETS_API_ENDPOINT
from utils import print_table_results, get_help_text, prepare_csv_value, parse_modified_time_param, extract_time_unit_and_value

import urllib3
import argparse

# Suppress warnings related to unverified HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def main():
    parser = argparse.ArgumentParser(description="Command allows you to search for incidents in Cortex XSOAR directly from Splunk. This command integrates Splunk with Cortex XSOAR, enabling seamless incident analysis. You can specify search criteria to pull incidents by time.")

    parser.add_argument('--created_earliest', type=str, help="Earliest creation time. Default: 24 hours.", default='24h')
    parser.add_argument('--created_latest', type=str, help="Latest creation time. Default: 0 seconds.", default='0s')
    parser.add_argument('--modified_earliest', type=str, help="Earliest modified time.", default='')
    parser.add_argument('--modified_latest', type=str, help="Latest modified time.", default='')
    parser.add_argument('--query', type=str, help="Cortex XSOAR query.  If it's not specified, it will be by default ''.", default='')
    parser.add_argument('--exclude_fields', type=str, help="Fields to be excluded from output, in comma separated form. Labels will be always excluded.", default='labels')
    
    argument_help_text = {}
    for argument in ['created_earliest', 'created_latest', 'modified_earliest', 'modified_latest', 'query', 'exclude_fields']:
        argument_help_text[argument] = get_help_text(parser, argument)

    args = parser.parse_args()
    
    date_range_by_to = extract_time_unit_and_value(args.created_latest).get('unit')
    date_range_by_from = extract_time_unit_and_value(args.created_earliest).get('unit')
    date_range_to_value = extract_time_unit_and_value(args.created_latest).get('value')
    date_range_from_value = extract_time_unit_and_value(args.created_earliest).get('value')
    modified_time_query = parse_modified_time_param(args.modified_earliest, args.modified_latest)
    query = f"{args.query} {modified_time_query}" if modified_time_query else args.query
    fields_to_exclude = args.exclude_fields
    
    list_of_mandatory_argument_dicts = {
            'date_range_by_to': date_range_by_to,
            'date_range_by_from': date_range_by_from,
            'date_range_to_value': date_range_to_value,
            'date_range_from_value': date_range_from_value,
            'exclude_fields': fields_to_exclude
        }
    
    for key, value in list_of_mandatory_argument_dicts.items():
        if value == '':
            print("Error")
            print(f"An error occurred: Command argument --{key} is missing.")
            help_text = prepare_csv_value('Help: ' + argument_help_text.get(key))
            print(help_text)
            return
    
    xsoar = XSOAR()
    xsoar.payload_generation(
        widget_config = WIDGET_CONFIG, 
        date_range_by_to = date_range_by_to, 
        date_range_by_from = date_range_by_from,
        date_range_to_value = date_range_to_value, 
        date_range_from_value = date_range_from_value,
        query = query)
    
    try:
        response = xsoar.pull_incidents(endpoint=XSOAR_WIDGETS_API_ENDPOINT)
        print_table_results(response, fields_to_exclude)
    except Exception as e:
        print("Error message")
        error_text = prepare_csv_value("An error occurred: "  + str(e))
        print(error_text)

if __name__ == "__main__":
    main()