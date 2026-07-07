"""Implement on-board validation of the app setup."""
import sys
import re
import hashlib
import logging
import socket
import json
import platform
import requests
from rfapi import ConnectApiClient
from rfapi.error import MissingAuthError

LGR = logging.getLogger(__name__)

RE_PROXY = r'(?P<proxyprotocol>https?)://' \
           r'((?P<username>[^:/]+):(?P<password>.+)@)?' \
           r'(?P<proxyhost>[^:/]+)(:(?P<proxyport>\d+))?'
COMPAT_URL = 'https://api.recordedfuture.com/rfq/aux/integration-versions/' \
             '%s/%s'


class RfeVerificationStep(object):
    """Contain config and result from a verification step."""

    fieldnames = ['Verification step', 'Status', 'Information',
                  'Suggested action']

    def __init__(self):
        """Initialize."""
        object.__init__(self)
        self.result_string = 'Verification has not been initiated.'
        self.name = type(self).__name__[19:]
        self.result_code = 'Pending'
        self.result_suggestion = ''

    def output_dict(self):
        """Report result as a dict."""
        return {
            'Verification step': self.name,
            'Status': self.result_code,
            'Information': self.result_string,
            'Suggested action': self.result_suggestion
        }

    def output_csv(self, fdcsv):
        """Write result as a CSV line."""
        fdcsv.writerow(self.output_dict())

    def report(self, code, message, suggestion):
        """Set result of verification log the message."""
        if self.result_code == 'Pending':  # Don't overwrite
            self.result_code = code
            self.result_string = message
            self.result_suggestion = suggestion

    def report_success(self, message, suggestion=''):
        """Set result of verification to success and log the message."""
        self.report('Ok', message, suggestion)

    def report_error(self, message, suggestion=''):
        """Set result of verification to success and log the message."""
        self.report('Error', message, suggestion)

    def report_warning(self, message, suggestion=''):
        """Set result of verification to success and log the message."""
        self.report('Warning', message, suggestion)

    def report_na(self, message='Unable to verify due to previous error.',
                  suggestion=''):
        """Set result of verification to not available.

        Can happen due to missing pre-condition.
        """
        self.report('NA', message, suggestion)


class RfeVerificationStepRFApiKey(RfeVerificationStep):
    """Verify that a token could be retreived from Splunk.

    Troubleshoot if not.
    """

    def run(self, app_env, token, logger):
        """Perform verification."""
        if token is not None and token != '':
            # Report success and add 6 first characters of the Md5
            # sum of the token. This allows verification that the
            # correct token has been entered without revealing any
            # sensitive data. This fingerprint is not usable in itself.
            self.report_success(
                'API key was received from Splunk. Fingerprint: %s'
                % hashlib.md5(token.encode('utf-8')).hexdigest()[:6])
            return

        # Token is not available. Figure out why.
        if app_env.session_key is None:
            self.report_na()
            return

        else:
            self.report_error('Could not retrieve api key. This indicates '
                              'that the app hasn\'t been properly setup.',
                              'Please configure the app.')


class RfeVerificationStepProxySetting(RfeVerificationStep):
    """If a proxy is configured, verify that it's a valid setting."""

    def run(self, app_env, token, logger):  # pylint: disable=unused-argument
        """Perform verification."""
        if app_env.proxies == {}:
            self.report_na('No proxy configured.')
            return

        reproxy = re.compile(RE_PROXY)
        pmatch = reproxy.match(app_env.proxies['http'])
        if pmatch is None:  # Completly wrong
            self.report_error('Invalid proxy setting: "%s"'
                              % app_env.proxies['http'],
                              'Go to Configuration and enter a valid '
                              'proxy setting. If a host name is entered '
                              'it must be resolvable by the Splunk server.')
            return

        pmd = pmatch.groupdict()
        if pmd['username'] is None or pmd['username'] in ['', 'None']:
            self.report_success('Valid proxy setting: %s://%s:%s/'
                                % (pmd['proxyprotocol'],
                                   pmd['proxyhost'], pmd['proxyport']))
        else:
            self.report_success('Valid proxy setting: '
                                '%s://<redacted>:<redacted>@%s:%s/'
                                % (pmd['proxyprotocol'],
                                   pmd['proxyhost'], pmd['proxyport']))


class RfeVerificationStepProxyDNSResolution(RfeVerificationStep):
    """If a proxy is configured, verify that hostname resolution works."""

    def run(self, app_env, token, logger):  # pylint: disable=unused-argument
        """Perform verification."""
        # NA if no proxy configured
        if app_env.proxies == {}:
            self.report_na('No proxy configured.')
            return
        # NA if proxy setting is not valid
        reproxy = re.compile(RE_PROXY)
        pmatch = reproxy.match(app_env.proxies['http'])
        if pmatch is None:
            self.report_na()
        # Check name resolution
        proxyhost = pmatch.groupdict()['proxyhost']
        try:
            proxyip = socket.gethostbyname(proxyhost)
            self.report_success('Proxy host name %s resolves to %s.'
                                % (proxyhost, proxyip))
        except socket.gaierror as err:
            self.report_error('Proxy host name can\'t be resolved: %s'
                              % err.strerror)
        except Exception as err:  # pylint: disable=broad-except
            self.report_error('Proxy host name can\'t be resolved: %s'
                              % sys.exc_info()[0])


class RfeVerificationStepProxyConnectivity(RfeVerificationStep):
    """If a proxy is configured, verify that the proxy is reachable."""

    def run(self, app_env, token, logger):  # pylint: disable=unused-argument
        """Perform verification."""
        # NA if no proxy configured
        if app_env.proxies == {}:
            self.report_na('No proxy configured.')
            return
        # NA if proxy setting is not valid
        reproxy = re.compile(RE_PROXY)
        pmatch = reproxy.match(app_env.proxies['http'])
        if pmatch is None:
            self.report_na()
        # Check connectivity
        try:
            requests.get('https://api.recordedfuture.com',
                         proxies=app_env.proxies, verify=app_env.verify)
            self.report_success('Proxy is working.')
        except requests.exceptions.ProxyError:
            self.report_error('Proxy is not working: %s'
                              % sys.exc_info()[1])
        except Exception:  # pylint: disable=broad-except
            self.report_error('Proxy is not working: %s'
                              % sys.exc_info()[0])


class RfeVerificationStepApiUrlValue(RfeVerificationStep):
    """Verify that the api url is sane."""

    def run(self, app_env, token, logger):  # pylint: disable=unused-argument
        """Perform verification."""
        try:
            self.report_success('API URL: %s' % app_env.api_url)
        except Exception:  # pylint: disable=broad-except
            self.report_error('API URL is not available')


class RfeVerificationStepApiConnectivity(RfeVerificationStep):
    """Verify that the api is reachable."""

    def run(self, app_env, token, logger):  # pylint: disable=unused-argument
        """Perform verification."""
        try:
            req = requests.get('%s' % app_env.api_url,
                               proxies=app_env.proxies,
                               verify=app_env.verify)
            if 'Recorded Future Connect API' in req.text:
                self.report_success('The Recorded Future API is reachable.')
            else:
                self.report_warning('A response was received from the '
                                    'Recorde Future API but it does not '
                                    'contain the expected text. Please '
                                    'verify that it really is the '
                                    'Recorde Future API that is reached.',
                                    'Verify that it really is a valid '
                                    'API URL, ex try to fetch the URL '
                                    '(default '
                                    'https://api.recordedfuture.com/v2/) '
                                    'manually. Ex use '
                                    'the CLI tool curl on the Splunk '
                                    'server.')
        except Exception:  # pylint: disable=broad-except
            self.report_error('The Recorded Future API could not be '
                              'reached: %s' % sys.exc_info()[0])


class RfeVerificationStepOSVersion(RfeVerificationStep):
    """Display the OS and version."""

    def run(self, app_env, token, logger):  # pylint: disable=unused-argument
        """Perform extraction of OS information."""
        os_name = platform.system()
        if os_name == 'Linux':
            osstring = "Type: %s, Distribution: %s, " \
                       "Version: %s, Machine type: %s" \
                       % (os_name, platform.dist()[0],
                          platform.dist()[1], platform.machine())
            self.report_success(osstring)
        elif os_name == 'Windows':
            osstring = "Type: %s, Version: %s, Machine type: %s" % \
                       (os_name, platform.platform(), platform.machine())
            self.report_success(osstring)
        elif os_name == 'Darwin':
            osstring = "Type: %s, Version: %s, Machine type: %s" % \
                       (os_name, platform.mac_ver()[0], platform.mac_ver()[2])
            self.report_success(osstring)
        else:
            self.report_warning("Unknown OS type. The app may not work.",
                                "Please report your machine information"
                                " to Recorded Future.")


class RfeVerificationStepAuth(RfeVerificationStep):
    """Verify that the api is reachable."""

    def run(self, app_env, token, logger):  # pylint: disable=unused-argument
        """Perform verification."""
        if token is None or token == '':
            self.report_warning('No API key available, verfication step '
                                'can not be performed.',
                                'Ensure that the RF API key can be '
                                'retrieved from Splunk\'s password store.')
            return
        api = ConnectApiClient(auth=token,
                               proxies=app_env.proxies,
                               verify=app_env.verify)
        try:
            api.search_ips(ip_range='8.8.8.8/32', limit=0)
            self.report_success('API calls can be performed. API key is '
                                'valid.')
        except MissingAuthError:
            suggestion = 'Verify that an API key is configu' \
                         'red in the global configuration and th' \
                         'at it is valid.'
            self.report_error('Invalid or missing API Key',
                              suggestion=suggestion)
        except Exception:  # pylint: disable=broad-except
            self.report_error('The API call could not be completed: %s'
                              % sys.exc_info()[0])


class RfeVerificationStepSplunkVersion(RfeVerificationStep):
    """Basic info about the Splunk environment."""

    def run(self, app_env, token, logger):  # pylint: disable=unused-argument
        """Perform verification."""
        if app_env.session_key is None:
            self.report_na()
        else:
            try:
                splunk_version = app_env.splunk_version
                self.report_success('Splunk version is %s' % splunk_version)
            except Exception:  # pylint: disable=broad-except
                self.report_error('Unable to lookup Splunk version: %s'
                                  % sys.exc_info()[0])


class RfeVerificationStepRest(RfeVerificationStep):
    """Basic info about the Splunk Rest endpoint."""

    def run(self, app_env, token, logger):  # pylint: disable=unused-argument
        """Perform verification."""
        if app_env.server_uri is None:
            self.report_na()
        else:
            try:
                self.report_success('Splunk REST endpoint is %s'
                                    % (app_env.server_uri))
            except Exception:  # pylint: disable=broad-except
                self.report_error('Unable to lookup Splunk REST endpoint: %s'
                                  % sys.exc_info()[0])


class RfeVerificationStepSearchHeadCluster(RfeVerificationStep):
    """Check if it's a Search Head cluster."""

    def run(self, app_env, token, logger):  # pylint: disable=unused-argument
        """Perform verification."""
        job = app_env.rest_call('/admin/shclusterconfig')
        if 'entry' not in job:
            self.report_success('Not part of a Search Head cluster.')
            return
        if job['entry'][0]['content']['shcluster_label'] != '':
            self.report_success('Part of a Search Head cluster.')
        else:
            self.report_success('Not part of a Search Head cluster.')


class RfeVerificationStepOldSearches(RfeVerificationStep):
    """Verify that there are no old saved searches using old scripts."""

    def run(self, app_env, token, logger):  # pylint: disable=unused-argument
        """Perform verification."""
        try:
            conf = app_env.read_config('savedsearches.conf')
            for entry in conf:
                if entry == 'rfrisklistdownload':
                    self.report_warning('Saved searches using old'
                                        ' scrips are still present.')
            self.report_success('No references to rfrisklistdownload'
                                ' in savedsearches.conf')
        except Exception as err:  # pylint: disable=broad-except
            logger.error('Failed due to: %s' % str(err))
            self.report_error('Something went wrong when trying to'
                              ' access savedsearches.conf.')


class RfeVerificationStepCompatibility(RfeVerificationStep):
    """Verify that the app is running on an compatible platform."""

    def run(self, app_env, token, logger):  # pylint: disable=unused-argument
        """Perform verification."""
        try:
            res = requests.get(COMPAT_URL % ('splunk',
                                             app_env.integration_version),
                               proxies=app_env.proxies,
                               verify=app_env.verify)
        except Exception as err:  # pylint: disable=broad-except
            self.report_warning('Compatibility information could not be '
                                'accessed for version %s. '
                                '%s' % (app_env.integration_version, err),
                                'Check compatibilty on SplunkBase.')
            return

        try:
            data = json.loads(res.content)
            if 'error' in data:
                self.report_warning(
                    'No compatibility information available for '
                    'version %s' % app_env.integration_version,
                    'Contact Recorded Future support if you '
                    'experience problems.')
                return
            if app_env.splunk_minor_version not in data:
                self.report_warning('The Splunk version (%s) is not '
                                    'supported by this version of the '
                                    'app.' % app_env.splunk_version,
                                    'Contact Recorded Future support if '
                                    'you experience problems.')
                return
            self.report_success('Splunk %s is supported '
                                'by version %s of the app.'
                                % (app_env.splunk_version,
                                   app_env.integration_version))
        except Exception as err:  # pylint: disable=broad-except
            self.report_warning('Compatibility information could not be '
                                'checked. %s' % err,
                                'Check compatibilty on '
                                'SplunkBase.')


class RfeVerificationStepVerifySSL(RfeVerificationStep):
    """Check the status of the Verify SSL global option."""

    def run(self, app_env, token, logger):
        """Check the status."""
        verify = 'Enabled' if app_env.verify else 'Disabled'
        self.report_success('Status: %s' % verify)


class RfeVerificationStepCheckpoints(RfeVerificationStep):
    """Check the status of checkpoints."""

    def run(self, app_env, token, logger):
        """Check the status."""
        checkpoints = app_env.rest_call('/storage/collections/data/%s/'
                                        % app_env.checkpoint_name)
        failed = []
        if not checkpoints:
            self.report_error('No checkpoints available',
                              suggestion='This may be normal if no risk lists'
                                         ' has been downloaded yet. Verify th'
                                         'at inputs configuration is correct '
                                         'and that both the API key and URL a'
                                         're configured.')
            return
        for checkpoint in checkpoints:
            if '_key' in checkpoint \
                    and checkpoint['_user'] == 'nobody' \
                    and 'sha256' in checkpoint \
                    and 'history' in checkpoint \
                    and 'updated' in checkpoint \
                    and 'name' in checkpoint \
                    and 'history' in checkpoint:
                continue
            elif checkpoint.get('_key').endswith('_sha256sum'):
                # Old Checkpoint, ignore
                continue
            else:
                logger.error('Failed checkpoint: %s' % checkpoint)
                failed.append(checkpoint.get('_key'))
        if failed:
            self.report_error('Missing data in the following checkpoints:'
                              ' %s' % ', '.join(failed))
            return
        self.report_success('Checkpoints are populated with data.')


class RfeVerificationStepFusionLists(RfeVerificationStep):
    """Verify that the defined fusion risk lists are accessable."""

    def run(self, app_env, token, logger):  # pylint: disable=unused-argument
        """Perform verification."""
        logger.debug("Start RL Inputs")
        api = ConnectApiClient(auth=token,
                               proxies=app_env.proxies,
                               verify=app_env.verify)
        failed = []
        logger.debug(str(app_env.risklists))
        for entry, values in app_env.risklists.items():
            logger.debug('Checking risklist: %s' % entry)
            if values.get('disabled', False) is True:
                continue
            else:
                if values.get('fusion_risk_list', None) is None:
                    cat = values.get('risk_list_category')
                    logger.debug('Category: %s' % cat)
                    if cat is not None:
                        path = ''.join(['/public/default_',
                                       cat, '_risklist.csv'])
                        try:
                            res = api.head_fusion_file(path)
                            logger.debug('Headers: %s' % str(res))
                        except requests.exceptions.HTTPError:
                            failed.append('Default %s risk list' % cat)
                        except requests.exceptions.SSLError as err:
                            suggestion = 'Disable SSL verification if this ' \
                                         'is expected. Otherwise find out ' \
                                         'why the verification fails.'
                            self.report_error('SSL certificate not valid: %s'
                                              % str(err),
                                              suggestion=suggestion)
                        except MissingAuthError:
                            suggestion = 'Verify that an API key is ' \
                                         'configured in the global ' \
                                         'configuration and that it is valid.'
                            self.report_error('Invalid or missing API Key',
                                              suggestion=suggestion)

                else:
                    path = values['fusion_risk_list']
                    logger.debug('Fusion path: %s' % path)
                    try:
                        res = api.head_fusion_file(path)
                        logger.debug('Headers: %s' % str(res))
                    except requests.exceptions.HTTPError:
                        failed.append(entry)
                    except requests.exceptions.SSLError as err:
                        self.report_error('SSL certificate not valid: %s'
                                          % str(err),
                                          suggestion='Disable SSL'
                                                     ' verification if this '
                                                     'is expected. Otherwise'
                                                     'find out why the verif'
                                                     'ication fails.')
                    except MissingAuthError:
                        suggestion = 'Verify that an API key is configu' \
                                     'red in the global configuration and th' \
                                     'at it is valid.'
                        self.report_error('Invalid or missing API Key',
                                          suggestion=suggestion)

        if failed:
            self.report_error('Could not access fusion file(s): %s'
                              % ', '.join(failed),
                              suggestion='Make sure that the current API-key'
                                         ' can access the fusion file(s) and'
                                         ' that it/they exist.')
        self.report_success('All configured risk lists can be accessed.')


class RfeVerificationStepAlertInputs(RfeVerificationStep):
    """Verify that the defined alerts are accessable."""

    def run(self, app_env, token, logger):  # pylint: disable=unused-argument
        """Perform verfication."""
        logger.debug("Start Alert Inputs")
        failed = []
        try:
            api = ConnectApiClient(auth=token, proxies=app_env.proxies,
                                   verify=app_env.verify)
            for entry, values in app_env.alerts.items():
                if values.get('disabled', False) is True:
                    continue
                else:
                    logger.debug('Alert: %s' % entry)
                    if values.get('alert_rule_id', None) is None:
                        res = api.search_alerts()
                    else:
                        res = api.get_alert_rule(values['alert_rule_id'])
                    if res.entities:
                        continue
                    failed.append(entry)
        except requests.exceptions.SSLError as err:
            self.report_error('SSL certificate not valid: %s'
                              % str(err),
                              suggestion='Disable SSL'
                                         ' verification if this is expected.'
                                         ' Otherwise find out why the'
                                         ' verification fails.')
        except MissingAuthError:
            suggestion = 'Verify that an API key is configu' \
                         'red in the global configuration and th' \
                         'at it is valid.'
            self.report_error('Invalid or missing API Key',
                              suggestion=suggestion)
        except Exception:  # pylint: disable=broad-except
            self.report_error('Something went wrong when trying to'
                              ' access the alerts.')
        if failed:
            self.report_error('Could not access alert rule(s): %s'
                              % ', '.join(failed),
                              suggestion='Make sure that the current API-key'
                                         ' can access the alert(s) and that'
                                         ' it/they exist.')
        self.report_success('All configured alerts can be accessed.')


class RfeVerificationStepKVStatus(RfeVerificationStep):
    """Verify the status of KV Storage in Splunk Enterprise."""

    def run(self, app_env, token, logger):
        """Perform verification."""
        baseurl = '%s%s' % (
            app_env.server_uri, '/services/kvstore/status')
        headers = {'Authorization': 'Splunk %s' % app_env.session_key}
        params = {'output_mode': 'json'}
        job = requests.get(baseurl,
                           headers=headers,
                           params=params,
                           verify=False).json()
        try:
            status = job['entry'][0]['content']['current']['status']
            if status == 'ready':
                self.report_success('KV Store status: %s' % status)
            else:
                self.report_warning('KV Store status is not ready: %s'
                                    % status)
        except KeyError as err:
            self.report_error('KV Store error: %s, KeyError: %s'
                              % (json.dumps(job['entry'][0]), err))


class RfeVerificationStepPythonVersion(RfeVerificationStep):
    """Verify the status of KV Storage in Splunk Enterprise."""

    def run(self, app_env, token, logger):
        """Perform verification."""
        self.report_success('Python version is %s' % sys.version.replace('\n',
                                                                         ''))


def validate(api_key, app_env, logger):
    """Execute validation."""
    verification_steps = [
        RfeVerificationStepSplunkVersion(),
        RfeVerificationStepOSVersion(),
        RfeVerificationStepRest(),
        RfeVerificationStepRFApiKey(),
        RfeVerificationStepProxySetting(),
        RfeVerificationStepProxyDNSResolution(),
        RfeVerificationStepProxyConnectivity(),
        RfeVerificationStepApiUrlValue(),
        RfeVerificationStepApiConnectivity(),
        RfeVerificationStepAuth(),
        RfeVerificationStepCompatibility(),
        RfeVerificationStepOldSearches(),
        RfeVerificationStepVerifySSL(),
        RfeVerificationStepSearchHeadCluster(),
        RfeVerificationStepCheckpoints(),
        RfeVerificationStepFusionLists(),
        RfeVerificationStepAlertInputs(),
        RfeVerificationStepKVStatus(),
        RfeVerificationStepPythonVersion()
    ]

    for count, step in enumerate(verification_steps):
        try:
            step.run(app_env, api_key, logger)
        except Exception as err:
            logger.error('Validation step failed: %s', step, exc_info=1)
            step.report_error('Error during verification: %s %s %s'
                              % sys.exc_info())

    return [{'step': 'step_%d' % (step + 1),
             'result': result.output_dict()}
            for step, result in enumerate(verification_steps)]
