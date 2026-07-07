from rest_handler.rest_interface_splunkd import BaseRestInterfaceSplunkd
from rest_handler.session import session
import ite_constants


class IteRestInterfaceSplunkd(BaseRestInterfaceSplunkd):
    def __init__(self, command_line, command_arg):
        super(IteRestInterfaceSplunkd, self).__init__(command_line, command_arg)

    def handle(self, in_string):
        '''
        Wrapper around BaseRestInterfaceSplunkd.handle()
        '''
        session.save(req_source=ite_constants.REQ_SOURCE_REST_API)
        return super(IteRestInterfaceSplunkd, self).handle(in_string)
