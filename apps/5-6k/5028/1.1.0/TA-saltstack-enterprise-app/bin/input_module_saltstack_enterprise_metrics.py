# -*- encoding: utf-8 -*-

import datetime
import hashlib
import urllib.parse
import json
import time


class CollectD:
    def __init__(self):
        self.values = []
        self.dstypes = []
        self.dsnames = ['value']
        self.time = None
        self.interval = None
        self.host = None
        self.plugin = None
        self.plugin_instance = None
        self.type = None
        self.type_instance = None

    def as_dict(self):
        return self.__dict__.copy()

    def get_epoch_from_iso8601(self, iso_time):
        ret = None
        # raas measurements sometimes will not have the microseconds.
        if len(iso_time) == 19:
            ret = (datetime.datetime.strptime(iso_time, '%Y-%m-%dT%H:%M:%S') -
                   datetime.datetime(1970, 1, 1)).total_seconds()
        else:
            ret = (datetime.datetime.strptime(iso_time, '%Y-%m-%dT%H:%M:%S.%f') -
                   datetime.datetime(1970, 1, 1)).total_seconds()
        return ret

    def format(self, name, series):
        ret = []
        max_time = 0
        metric, _id = name.split('-', 1)
        self.plugin = 'SaltStack'
        self.type = metric
        self.host = _id
        self.dstypes = ['gauge']
        for s in series:
            self.values = [s['value']]
            self.time = self.get_epoch_from_iso8601(iso_time=s['name'])
            if int(self.time) > max_time:
                max_time = int(self.time)
            ret.append(self.as_dict())
        return max_time, ret


def chunkify(array, per_chunk=10):
    return [array[i: i + per_chunk] for i in range(0, len(array), per_chunk)]


def patch_helper(helper):
    """
    Patch helper function to have get_arg
    """
    if hasattr(helper, 'get_param'):
        if not hasattr(helper, 'get_arg'):
            setattr(helper, 'get_arg', helper.get_param)
    return helper


def get_checkpoint_key(helper, for_=None):
    """
    Form the checkpoint key using URL and index name.
    """
    key = None

    helper = patch_helper(helper)

    if helper.get_arg('saltstack_enterprise_url'):
        saltstack_enterprise_url = helper.get_arg(
            'saltstack_enterprise_url').strip()
    else:
        saltstack_enterprise_url = helper.get_global_setting(
            'saltstack_enterprise_url').strip()

    index = helper.get_output_index()

    key = '{for_}:{url}:{index}'.format(
        for_=for_,
        url=saltstack_enterprise_url,
        index=index
    )

    return hashlib.sha256(key.encode('utf-8')).hexdigest()


class SSE:
    def __init__(self, helper):
        self.helper = helper
        self.cookies = None
        self.headers = {
            'X-RaaS-RPC-Version': '7'
        }
        self.saltstack_enterprise_url = None
        self.config_name = 'internal'
        self.global_account = None
        self.certificate_path = None
        self.request_timeout = None
        self.verify_ssl = None
        self.load_params(helper)

    def load_params(self, helper):
        """
        Load params for data inputs and alert actions
        """
        # Splunk helper for data input and alerts are inconsistent with their
        # naming convention. Also, there is no way to get credentials by account
        # id for an alert.
        # So, use account for data input and user name for alert as per Splunk
        # documentation. Use get_arg to get parameters for both alert and data
        # input.
        helper = patch_helper(helper)
        if hasattr(helper, 'action_name') and isinstance(helper.action_name, str):
            self.global_account = self.helper.get_user_credential(self.helper.get_arg('saltstack_username'))
        else:
            self.global_account = self.helper.get_arg('global_account')

        if self.helper.get_arg('saltstack_enterprise_url'):
            self.saltstack_enterprise_url = self.helper.get_arg(
                'saltstack_enterprise_url').strip()
        else:
            self.saltstack_enterprise_url = self.helper.get_global_setting(
                'saltstack_enterprise_url').strip()

        if self.helper.get_arg('certificate_path'):
            self.certificate_path = self.helper.get_arg('certificate_path')
        elif self.helper.get_global_setting('certificate_path'):
            self.certificate_path = self.helper.get_global_setting('certificate_path')

        if self.helper.get_arg('request_timeout'):
            self.request_timeout = int(self.helper.get_arg('request_timeout'))
        elif self.helper.get_global_setting('request_timeout'):
            self.request_timeout = int(self.helper.get_global_setting('request_timeout'))

        self.verify_ssl = False
        if self.helper.get_global_setting('verify_ssl') is True or self.helper.get_global_setting('verify_ssl') == '1':
            self.verify_ssl = True
        if self.helper.get_arg('verify_ssl') is True or self.helper.get_arg('verify_ssl') == '1':
            self.verify_ssl = True
        elif self.helper.get_arg('verify_ssl') is False or self.helper.get_arg('verify_ssl') == '0':
            self.verify_ssl = False

    def authenticate(self):
        response = self.send_http_request(
            url=urllib.parse.urljoin(
                self.saltstack_enterprise_url,
                '/account/login'),
            payload=None,
            method='GET'
        )
        if 'X-Xsrftoken' in response.headers:
            self.headers['X-Xsrftoken'] = response.headers['X-Xsrftoken']
        response = self.send_http_request(
            url=urllib.parse.urljoin(
                self.saltstack_enterprise_url,
                '/account/login'),
            payload={
                'config_name': self.config_name,
                'username': self.global_account.get('username'),
                'password': self.global_account.get('password'),
            },
        )
        self.cookies = response.cookies

    def send_http_request(self, url, payload, method='POST'):
        response = self.helper.send_http_request(
            url, method,
            parameters=None,
            payload=json.dumps(payload),
            headers=self.headers,
            cookies=self.cookies,
            verify=self.verify_ssl,
            cert=self.certificate_path,
            timeout=self.request_timeout,
            use_proxy=True)
        response.raise_for_status()
        return response

    def api(self, payload):
        self.helper.log_debug('Sending request to SSE - {}'.format(payload))
        response = self.send_http_request(
            url=urllib.parse.urljoin(
                self.saltstack_enterprise_url,
                '/rpc'),
            payload=payload,
        )
        return response.json().get('ret')


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    collect_metrics = definition.parameters.get('collect_metrics', None)
    assert collect_metrics in ('0', '1'), '{} is not a valid input for collect_metrics'.format(
        collect_metrics)


def get_metrics(sse, metrics_start_time=None):
    payload = {
        'resource': 'stats',
        'method': 'get_system_metrics',
        'kwarg': {
            'daterange': {}
        }
    }
    if metrics_start_time:
        payload['kwarg']['daterange'] = dict(
            start=datetime.datetime.utcfromtimestamp(metrics_start_time).isoformat())
    response = sse.api(payload)
    return response


def route_cmd(sse, cmd, fun, tgt, tgt_type, args, kwargs, master):
    payload = {
        'resource': 'cmd',
        'method': 'route_cmd',
        'kwarg': {
            'fun': fun,
            'cmd': cmd,
            'tgt': {
                master: {
                    'tgt_type': tgt_type,
                    'tgt': tgt,
                }
            },
            'arg': {
                'arg': args,
                'kwarg': kwargs
            }
        }
    }
    response = sse.api(payload)
    return response


def save_metrics(helper, ew, metrics):
    max_time = 0
    one_day = 24 * 3600
    c_fmt = []
    helper.log_info('{} metrics received from SSE'.format(metrics['count']))
    for r in metrics['results']:
        c_max, c = CollectD().format(name=r.get('name'),
                                     series=r.get('series'))
        if c_max > max_time:
            max_time = c_max
        c_fmt.extend(c)

    for cc in chunkify(c_fmt, per_chunk=10):
        event = helper.new_event(source=helper.get_input_type(),
                                 index=helper.get_output_index(),
                                 sourcetype='collectd_http',
                                 data=json.dumps(cc),
                                 done=True,
                                 unbroken=True)
        ew.write_event(event)

    metrics_start_time = helper.get_check_point(
        get_checkpoint_key(
            helper, for_='metrics_start_time'
        )
    )
    if metrics_start_time and (metrics_start_time == max_time or (
            max_time == 0 and metrics_start_time < time.time() - one_day
    )):
        helper.log_debug('Incrementing metrics_start_time checkpoint. metrics_start_time = {}, max_time = {}, '
                         'current_time = {}'.format(metrics_start_time, max_time, time.time()))
        if metrics_start_time == max_time:
            max_time += 1
        else:
            max_time = metrics_start_time + one_day
            if max_time > time.time():
                max_time = int(time.time())

    if max_time:
        helper.save_check_point(
            get_checkpoint_key(
                helper,
                for_='metrics_start_time'
            ),
            max_time
        )
        helper.log_debug('Metrics written to Splunk. Max time = {}'.format(max_time))


def collect_events(helper, ew):
    helper.log_debug('Collecting events.')
    opt_collect_metrics = helper.get_arg('collect_metrics')
    helper.log_info('Param: Collect metrics - {}'.format(opt_collect_metrics))

    helper.log_debug('Authenticating with SaltStack Enterprise.')
    sse = SSE(helper=helper)
    sse.authenticate()

    if opt_collect_metrics:
        helper.log_debug('Collecting metrics from SaltStack Enterprise.')
        metrics_start_time = helper.get_check_point(
            get_checkpoint_key(helper, for_='metrics_start_time')
        )
        helper.log_debug('Metrics start time - {}'.format(metrics_start_time))
        metrics = get_metrics(sse, metrics_start_time)
        save_metrics(helper, ew, metrics=metrics)
        helper.log_info('Metrics collection complete.')


def format_args(key, val):
    ret = None
    if key == 'args':
        ret = list(map(lambda x: x.strip(),
                       val.split(',')))
    else:
        try:
            ret = json.loads(val)
        except (TypeError, json.decoder.JSONDecodeError):
            ret = val
    return ret


def get_params_from_payload(event, whitelist=()):
    """
    Return route command parameters from event payload.
    """
    ret = dict()
    ident, ident_kwargs = 'salt__.', 'salt__.kwargs.'
    is_kwarg_param = False
    for key, value in event.items():
        if not key.startswith(ident):
            continue
        _, param = key.split(ident)
        if key.startswith(ident_kwargs):
            _, param = key.split(ident_kwargs)
            is_kwarg_param = True
        if param and whitelist and (param in whitelist or (
           is_kwarg_param and 'kwargs' in whitelist)
        ):
            if param == 'args':
                ret[param] = format_args(param, value)
            else:
                v = format_args(key=param, val=value)
                if is_kwarg_param:
                    ret.setdefault('kwargs', {}).update({param: v})
                else:
                    ret[param] = v
    return ret


def get_route_cmd_params(helper, event):
    """
    Get the parameters required to call route_cmd
    """
    def _format(key, val):
        ret = None
        if key == 'args':
            ret = list(map(lambda x: x.strip(),
                           val.split(',')))
        elif key == 'kwargs':
            ret = json.loads(val)
        return ret

    ret = dict()
    ret['args'] = []
    ret['kwargs'] = {}
    ret['tgt'], ret['tgt_type'] = event['host'], 'list'

    route_param_keys = ['tgt', 'tgt_type', 'fun', 'cmd',
                        'master', 'args', 'kwargs']

    # Retrieve parameters from alert form values
    for key in route_param_keys:
        val = helper.get_param(key)
        if val:
            # don't replace the tgt_type from payload if the tgt_type value is not selected.
            if key == 'tgt_type' and val == 'select':
                continue
            ret[key] = format_args(key, val)

    # Override form parameters with event payload.
    params = get_params_from_payload(
        event,
        whitelist=route_param_keys
    )
    if params:
        ret.update(params)

    return ret


def process_event(helper, *args, **kwargs):
    """
    Process the event triggered by Splunk with a call to
    SaltStack Enterprise
    """
    helper.log_info('Alert action {} started.'.format(helper.action_name))

    helper.log_debug('Authenticating with SaltStack Enterprise.')
    sse = SSE(helper=helper)
    sse.authenticate()

    # Default alert action is to invoke the salt command.
    if helper.action_name == 'saltstack_alert_action':
        events = helper.get_events()
        for event in events:
            params = get_route_cmd_params(helper, event)
            if params['fun'] and params['tgt']:
                jid = route_cmd(sse=sse, **params)
                helper.log_info('Initiated action in SaltStack Enterprise. JID = {}'.format(jid))

    helper.log_info('Alert action {} completed.'.format(helper.action_name))

    return 0
