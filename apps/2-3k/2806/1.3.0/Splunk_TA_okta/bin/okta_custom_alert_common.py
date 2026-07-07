from okta_custom_command_base import Option

def is_empty(option_value):
    """
    Check whether the option_value is None or empty string
    :param option_value: <string>
    :return: bool
    """
    return option_value is None or str(option_value).strip() is ''


def get_option(type, option_id, option_name):
    """
    Get Option object (user or group option object)
    If option_id is not empty, generate Option object according to the option_id,
    otherwise if option_name is not empty, generate Option object according to the option_name,
    otherwise return None
    :param type: <string> 'user' or 'group'
    :param option_id: <string>
    :param option_name: <string>
    :return:
    """
    option_id = None if is_empty(option_id) else option_id
    option_name = None if is_empty(option_name) else option_name

    if option_id is None and option_name is None:
        return None

    return Option(option_id=option_id, option_name=option_name,type=type)