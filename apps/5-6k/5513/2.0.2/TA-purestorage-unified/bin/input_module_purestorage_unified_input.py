# encoding = utf-8
import time
import datetime
import calendar
import re
import input_module_purestorage_flashblade
import input_module_purestorage_flasharray
import input_module_purestorage_pure1
from purestorage_unified_utils import get_conf_file, input_with_account_exists
'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''


def validate_input_parameters(input_parameter, helper):
    """Input validation."""
    global_account = input_parameter.get('global_account', None)
    start_date = input_parameter.get('start_date')
    interval = input_parameter.get('interval')
    input_type = input_parameter.get('input_type')
    helper.log_debug("PureStorage Debug: interval is " + str(interval))
    current_utc = calendar.timegm(datetime.datetime.utcnow().timetuple())

    if input_type not in ['flashblade', 'flasharray', 'pure1']:
        msg = 'Input Type should be from flashblade, flasharray or pure1.'
        return True, msg

    if input_type == "pure1" and not (int(interval) >= 3600):
        msg = 'Interval should be greater than or equal to 3600 seconds.'
        return True, msg

    if not (int(interval) >= 60):
        msg = 'Interval should be greater than or equal to 60 seconds.'
        return True, msg

    if not global_account:
        msg = "System not found. Please add the valid system."
        return True, msg

    if start_date:
        if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", start_date):
            msg = 'Start Date should be in "YYYY-MM-DDTHH:mm:ssZ" format.'
            return True, msg

        try:
            time_pattern = "%Y-%m-%dT%H:%M:%SZ"
            start_date = calendar.timegm(time.strptime(start_date, time_pattern))

            if start_date < 0:
                msg = 'Start Date can not be lesser than "1970-01-01T00:00:00Z".'
                return True, msg

            if start_date > current_utc:
                msg = 'Start Date can not be greater than current UTC.'
                return True, msg
        except Exception:
            msg = "Please enter correct UTC date of format('YYYY-MM-DDTHH:mm:ssZ)"
            return True, msg
    return False, ""


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    # This example accesses the modular input variable
    error_msg_prefix = "PureStorage Error: "
    input_parameter = {}
    input_type = definition.parameters.get('input_type')
    global_account = definition.parameters.get('global_account', None)

    input_parameter["global_account"] = global_account
    input_parameter["start_date"] = definition.parameters.get('start_date')
    input_parameter["interval"] = definition.parameters.get('interval')
    input_parameter["input_type"] = input_type
    error_flag, error_message = validate_input_parameters(input_parameter, helper)
    if error_flag:
        helper.log_error("{}for input: {}. Error: {}"
                         .format(error_msg_prefix, definition.metadata.get('name'), error_message))
        raise ValueError(error_message)


def collect_events(helper, ew):
    """Implement your data collection logic here."""
    input_type = helper.get_arg('input_type')
    global_account = helper.get_arg('global_account')
    server_address = global_account.get('server_address')

    input_parameter = {}
    input_parameter["global_account"] = global_account
    input_parameter["start_date"] = helper.get_arg('start_date')
    input_parameter["interval"] = helper.get_arg('interval')
    input_parameter["input_type"] = input_type
    validate_input_parameters(input_parameter, helper)
    error_flag, error_message = validate_input_parameters(input_parameter, helper)
    if error_flag:
        helper.log_error("PureStorage Error: for input: {}. "
                         "Error: {}".format(helper.get_input_stanza_names(), error_message))
        return

    if server_address.startswith("https") or server_address.startswith("http"):
        helper.log_error("The server address {} should not include the scheme/protocol,"
                         " terminating the data collection".format(server_address))
        exit(1)
    else:
        if input_type == "flashblade":
            mod_input_obj = input_module_purestorage_flashblade.PureStroageFlashblade()
            mod_input_obj.collect_events(helper, ew)
        elif input_type == "flasharray":
            mod_input_obj = input_module_purestorage_flasharray.PureStroageFlasharray()
            mod_input_obj.collect_events(helper, ew)
        elif input_type == "pure1":
            input_parser_obj, input_stanzas = get_conf_file("inputs.conf")
            existing_input = input_with_account_exists(input_stanzas, input_parser_obj, global_account.get('name'),
                                                       input_type, helper.get_input_stanza_names(),
                                                       check_disabled=True)
            if existing_input is not None:
                msg = 'Input {} is already configured with same pure1 credentials. Exiting input {}.'.format(
                    existing_input, helper.get_input_stanza_names()
                )
                helper.log_error(msg)
                exit(1)
            mod_input_obj = input_module_purestorage_pure1.PureStroagePure1()
            mod_input_obj.collect_events(helper, ew)
