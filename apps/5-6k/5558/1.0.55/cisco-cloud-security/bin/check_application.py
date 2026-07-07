# encoding = utf-8
from __future__ import print_function
import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))
from splunk.persistconn.application import PersistentServerConnectionApplication
import splunklib.client as client
from validator import cummulative_validator, get_host
from logger import Logger
from common import Common

class CheckApplication(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        main_response = {'app':'not present'}
        try:
            params = Common().parse_in_string(in_string)
            session_token = params['session']['authtoken']
            header = params.get('headers', [])
            host = get_host(header)
            app_name = params["query"]["app_name"]
            if not cummulative_validator(str(app_name)):
                raise Exception('app_name id validation failed')
            service = client.connect(host=host, token=session_token)
            for i in service.apps.list():
                #Logger().info('apps available>>>>>>>'+str(i.name))
                if app_name==str(i.name):
                    main_response.update({'app': 'present'})
                    break
            # if app_name in list(service.apps.list()):
            #     main_response.update({'app':'present'})
            return {'payload': main_response, 'status': 200}
        except Exception as e:
            Logger().error("API: check_application, Exception : {0}".format(str(e)))
            return {'payload': {"message": str(e)}, "status": 500}
