import calendar
import json
import logging
import random
import splunk.rest as rest
import time

from cexc import BaseChunkHandler
from splunk.clilib import cli_common
from splunk.clilib.bundle_paths import make_splunkhome_path
from splunk.util import mktimegm


class CefOutHandler(BaseChunkHandler):
    DEFAULT_HEADER = '***SPLUNK*** index=cef\n'
    DEFAULT_BREAKER = '==##~~##~~  1E8N3D4E6V5E7N2T9 ~~##~~##==\n'

    def __init__(self, *args, **kwargs):
        super(CefOutHandler, self).__init__(*args, **kwargs)

        file_handler = logging.handlers.RotatingFileHandler(
            make_splunkhome_path(['var', 'log', 'splunk', 'cefout.log']),
            maxBytes=25000000)

        self.setup_logging_handler(file_handler)

        # placeholder for storing the routing group, can be empty string
        self.routing = ''

        self.splunk_server = cli_common.getConfKeyValue(
            'server', 'general', 'serverName')

        self.required_fields = [
            '_chunked_idx',
            'splunk_server',
            '_time',
            '_raw',
            'file_name',
            'count'
        ]

    def get_info(self, metadata=None):
        metadata = {} if metadata is None else metadata

        searchinfo = metadata.get('searchinfo', {})
        session_key = searchinfo.get('session_key')
        args = searchinfo.get('args', [])

        # splunk calls this method twice. once for parsing,
        # once for actual execution. in parsing phase session_key
        # is not passed to this command. search/parser gathers
        # semantic map of commands, so it's necessary to return these things.
        if not session_key:
            return {
                'type': 'streaming',
                'required_fields': self.required_fields
            }

        # actual get_info execution
        try:
            # retrieve input groups
            response, content = rest.simpleRequest(
                '/services/data/inputs/all',
                getargs={'output_mode': 'json', 'count': 0},
                sessionKey=session_key
            )

            if response.status != 200:
                raise Exception('Could not retrieve input groups')

            input_groups = json.loads(content)
            self.logger.debug('ARGS: %s', args)
            if len(args) != 1:
                raise Exception(
                    'Invalid number of arguments provided, '
                    'please provide routing argument only.'
                )

            key, val = args[0].split("=")
            if key != 'routing':
                raise Exception("Invalid argument '%s'" % key)

            # atleast one routing group should exist
            valid = any(
                group['name'].endswith('stash_cef_%s' % val)
                for group in input_groups['entry']
            )
            if valid:
                # store routing group for easy access
                self.routing = val
            else:
                self.logger.warn("Invalid routing group '%s'", val)

        except Exception as e:
            return self.die(str(e))

        # everything went well.
        return {
            'type': 'streaming',
            'required_fields': self.required_fields
        }

    def handler(self, metadata=None, data=None):
        metadata = {} if metadata is None else metadata
        empty_response = (
            {'finished': metadata.get('finished', True)},
            []
        )

        if metadata.get('action') == 'getinfo':
            return self.get_info(metadata)

        # if we don't have a routing group, don't do any work.
        if not self.routing:
            return empty_response

        # no data
        try:
            data = list(data)
        except Exception:
            self.logger.warn('No data to write; invalid-data')
            return empty_response

        # no body
        if len(data) <= 1:
            self.logger.warn('No data to write; header-only')
            return empty_response

        # CSV reader implementation
        fields = data[0]
        chunk_idx = fields.index('_chunked_idx')
        splunk_server_idx = fields.index('splunk_server')
        time_idx = fields.index('_time')
        raw_idx = fields.index('_raw')
        file_idx = fields.index('file_name')
        count_idx = fields.index('count')

        # Formulate output file string
        fout = CefOutHandler.DEFAULT_BREAKER.join(
                x[raw_idx].strip() + '\n'
                for x in data[1:]
                if x[raw_idx].strip())
        fout.rstrip('\n')

        # no fout
        if not fout:
            self.logger.warn('No data to write; empty-rows')
            return empty_response

        fout = CefOutHandler.DEFAULT_HEADER +\
            CefOutHandler.DEFAULT_BREAKER +\
            fout

        # set up file name and path
        fn = '{0}_{1}.stash_cef_{2}'.format(
            mktimegm(time.gmtime()),
            random.randint(0, 100000),
            self.routing
        )
        fp = make_splunkhome_path(['var', 'spool', 'splunk', fn])

        try:
            with open(fp, 'w') as fh:
                fh.write(fout)
        except Exception as e:
            self.logger.error(str(e))
            self.die('Could not write to spool file')

        # create new_event
        new_event = data[-1][:]
        new_event[chunk_idx] = new_event[raw_idx] = ''
        new_event[splunk_server_idx] = self.splunk_server
        new_event[time_idx] = calendar.timegm(time.gmtime())
        new_event[count_idx] = len(data)-1
        new_event[file_idx] = fn

        return (
            {'finished': metadata.get('finished', True)},
            [fields, new_event]
        )


if __name__ == "__main__":
    CefOutHandler(handler_data=CefOutHandler.DATA_CSVROW).run()
