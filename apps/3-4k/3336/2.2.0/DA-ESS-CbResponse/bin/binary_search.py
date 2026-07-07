from cbhelpers import CbSearchCommand2
from cbapi.response import Binary

import sys
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option

@Configuration()
class BinarySearchCommand(CbSearchCommand2):
    field_names = ['digsig_publisher', 'digsig_result', 'digsig_sign_time', 'host_count', 'is_executable_image',
                   'last_seen', 'original_filename', 'os_type', 'product_name', 'product_version', 'md5']
    search_cls = Binary
    log_file = "binary_search"


if __name__ == '__main__':
    try:
        dispatch(BinarySearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception as e:
        BinarySearchCommand.logger.exception("during dispatch: {1} {0}".format(e, type(e)))
