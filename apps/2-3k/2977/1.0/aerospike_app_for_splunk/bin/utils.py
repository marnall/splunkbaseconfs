import fileinput
import constant


def return_exceptions(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            args[0].alive = False
            return e
    return wrapper


@return_exceptions
def get_previous_node_list():

    """The method reads old node list from a conf file"""

    nodes = []
    for each_line in fileinput.input(constant.NODES_FILENAME):
        words = each_line.strip()
        if words != '':
            nodes.append(words)
    fileinput.close()
    return nodes


@return_exceptions
def write_new_node_list(nodes):

    """The method writes new node list to a conf file"""

    fileip = open(constant.NODES_FILENAME, 'w')
    for node in nodes:
        fileip.write(node + '\n')
    fileip.close()


@return_exceptions
def text_to_list(text, delimiter=";"):

    """The method used to convert given text of attributes
    seperated by delimiter to list"""

    if text.strip() == "":
        return []
    return text.split(delimiter)


@return_exceptions
def bytes_to_gb(bytes_data):

    """The method used to convert given bytes_data to GB"""

    return str(round((float(bytes_data) / constant.BYTES_TO_GB), 3))


@return_exceptions
def text_to_dict(text, delimiter1=";", delimiter2="="):

    """The method used to convert given text of attributes
    seperated by delimiter to dictonary"""

    dictionary = {}
    if text.strip() == "":
        return dictionary
    for record in text.split(delimiter1):
        namevalue = record.split(delimiter2)
        dictionary[namevalue[0]] = namevalue[1]

    return dictionary


@return_exceptions
def get_seed_node():

    """The method used to get seed_node Entered by user
    of splunk app"""
    for each_line in fileinput.input(constant.CONF_FILENAME):
        words = each_line.split("=")
        if words[0] == "seed_node ":
            fileinput.close()
            return words[1]
    fileinput.close()
    return "-1"
