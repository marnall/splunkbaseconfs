
# encoding = utf-8

import sys
import requests
import json
import pytz

from datetime import datetime, timedelta
from dateutil import tz


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # trellix_edr_tenant_region = definition.parameters.get('trellix_edr_tenant_region', None)
    # trellix_edr_client_id = definition.parameters.get('trellix_edr_client_id', None)
    # trellix_edr_client_secret = definition.parameters.get('trellix_edr_client_secret', None)
    # initial_pull_in_days = definition.parameters.get('initial_pull_in_days', None)
    pass

def collect_events(helper, ew):

    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)
    proxy = helper.get_proxy()

    tenant_region = helper.get_arg('trellix_edr_tenant_region')
    client_id = helper.get_arg('trellix_edr_client_id')
    client_secret = helper.get_arg('trellix_edr_client_secret')
    initial_pull = helper.get_arg('initial_pull_in_days')

    if tenant_region == 'EU':
        base_url = 'soc.eu-central-1.mcafee.com'
    elif tenant_region == 'US-W':
        base_url = 'soc.mcafee.com'
    elif tenant_region == 'US-E':
        base_url = 'soc.us-east-1.mcafee.com'
    elif tenant_region == 'SY':
        base_url = 'soc.ap-southeast-2.mcafee.com'
    elif tenant_region == 'GOV':
        base_url = 'soc.mcafee-gov.com'

    session = requests.Session()

    if proxy != {}:
        session.proxies['https'] = '{ptype}://{user}:{pwd}@{ip}:{port}'.format(
            ptype=proxy['proxy_type'],
            user=proxy['proxy_username'],
            pwd=proxy['proxy_password'],
            ip=proxy['proxy_url'],
            port=proxy['proxy_port']
        )

    creds = (client_id, client_secret)

    ldtime = helper.get_check_point('ldtime')

    if ldtime is not None:
        last_detection = datetime.strptime(ldtime, '%Y-%m-%dT%H:%M:%SZ')
        last_detection_utc = last_detection.replace(tzinfo=pytz.UTC)
        next_pull = last_detection_utc.astimezone(tz.tzlocal()) + timedelta(seconds=1)

        helper.log_debug('Cache exists. Last detection date UTC: {0}'.format(last_detection))
        helper.log_debug('Pulling newest threats from: {0}'.format(next_pull))
    else:
        helper.log_debug('Cache does not exists. Pulling data from last {0} days.'.format(initial_pull))
        next_pull = datetime.now() - timedelta(days=int(initial_pull))

    epoch_pull = str(datetime.timestamp(next_pull) * 1000)[:13]
    helper.log_debug('New pulling date {0} - epoch {1}'.format(next_pull, epoch_pull))

    auth(helper, session, creds)
    limit = 10000

    get_threats(helper, session, base_url, ldtime, epoch_pull, limit, ew)


def auth(helper, session, creds):
    try:
        payload = {
            'scope': 'soc.hts.c soc.hts.r soc.rts.c soc.rts.r soc.qry.pr',
            'grant_type': 'client_credentials',
            'audience': 'mcafee'
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        res = session.post('https://iam.mcafee-cloud.com/iam/v1.1/token', headers=headers, data=payload, auth=creds)

        if res.ok:
            token = res.json()['access_token']
            session.headers = {'Authorization': 'Bearer {}'.format(token)}
            helper.log_debug('AUTHENTICATION: Successfully authenticated.')
            helper.log_debug(res.text)
        else:
            helper.log_error('Error in retrieving edr.auth(). Request url: {}'.format(res.url))
            helper.log_error('Error in retrieving edr.auth(). Request headers: {}'.format(res.request.headers))
            helper.log_error('Error in retrieving edr.auth(). Request body: {}'.format(res.request.body))
            raise Exception('Error in retrieving edr.auth(). Error: {0} - {1}'.format(str(res.status_code), res.text))

    except Exception as error:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        helper.log_error("Error in {location}.{funct_name}() - line {line_no} : {error}"
                     .format(location=__name__, funct_name=sys._getframe().f_code.co_name,
                             line_no=exc_tb.tb_lineno, error=str(error)))
        raise


def get_threats(helper, session, base_url, ldtime , epoch_pull, limit, ew):
    try:
        tthreat = 0
        tdetect = 0
        skip = 0
        tnextflag = True

        filter = {}
        severities = ["s0", "s1", "s2", "s3", "s4", "s5"]
        filter['severities'] = severities
        filter['scoreRange'] = [30]

        while (tnextflag):
            res = session.get(
                'https://api.{0}/ft/api/v2/ft/threats?sort=-lastDetected&filter={1}&from={2}&limit={3}&skip={4}'
                    .format(base_url, json.dumps(filter), epoch_pull, limit, skip))

            if res.ok:
                res = res.json()

                if int(res['skipped']) + int(res['items']) == int(res['total']):
                    tnextflag = False
                else:
                    skip = int(res['skipped']) + int(res['items'])

                if len(res['threats']) > 0:
                    if ldtime is not None:
                        last_detection = datetime.strptime(ldtime, '%Y-%m-%dT%H:%M:%SZ')
                        if last_detection < (datetime.strptime(res['threats'][0]['lastDetected'], '%Y-%m-%dT%H:%M:%SZ')):
                            helper.log_debug('More recent detection timestamp detected. Updating cache.log.')
                            helper.save_check_point('ldtime', res['threats'][0]['lastDetected'])
                        else:
                            helper.log_debug('More recent detection timestamp in cache.log already saved.')
                    else:
                        helper.save_check_point('ldtime', res['threats'][0]['lastDetected'])

                    for threat in res['threats']:
                        affhosts = get_affected_hosts(helper, session, base_url, epoch_pull, limit, threat['id'])
                        ddetect_count = 0
                        for host in affhosts:
                            detections = get_detections(helper, session, base_url, epoch_pull, limit, threat['id'], host['id'])

                            for detection in detections:
                                threat['detection'] = detection

                                traceid = detection['traceId']
                                maguid = detection['host']['maGuid']
                                sha256 = detection['sha256']

                                threat[
                                    'url'] = 'https://ui.{0}/monitoring/#/workspace/72,TOTAL_THREATS,{1}?traceId={2}&maGuid={3}&sha256={4}' \
                                    .format(base_url, threat['id'], traceid, maguid, sha256)

                                event = helper.new_event(source=helper.get_input_type(), index=helper.get_arg('index'),
                                                         sourcetype=helper.get_sourcetype(), data=json.dumps(threat, sort_keys=True))

                                ew.write_event(event)
                                helper.log_debug(json.dumps(threat))
                                helper.log_info('Retrieved new MVISION EDR Threat Detection. {0}'.format(threat['name']))

                                tdetect += 1
                                ddetect_count += 1

                        helper.log_debug('For threat {0} identified {1} new detections.'.format(threat['name'], ddetect_count))
                        tthreat += 1

                else:
                    helper.log_debug('No new threats identified. Exiting. {0}'.format(res))

            else:
                helper.log_error('Error in retrieving edr.get_threats(). Request url: {}'.format(res.url))
                helper.log_error(
                    'Error in retrieving edr.get_threats(). Request headers: {}'.format(res.request.headers))
                helper.log_error('Error in retrieving edr.get_threats(). Request body: {}'.format(res.request.body))
                raise Exception(
                    'Error in retrieving edr.get_threats(). Error: {0} - {1}'.format(str(res.status_code),
                                                                                     res.text))

        helper.log_debug('Pulled total {0} Threats and {1} Detections.'.format(tthreat, tdetect))

    except Exception as error:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        helper.log_error("Error in {location}.{funct_name}() - line {line_no} : {error}"
                         .format(location=__name__, funct_name=sys._getframe().f_code.co_name,
                                 line_no=exc_tb.tb_lineno, error=str(error)))
        raise


def get_affected_hosts(helper, session, base_url, epoch_pull, limit, threatId):
    try:
        skip = 0
        anextflag = True
        affhosts = []

        while (anextflag):

            res = session.get('https://api.{0}/ft/api/v2/ft/threats/{1}/affectedhosts?sort=-rank&from={2}&limit={3}&skip={4}'
                    .format(base_url, threatId, epoch_pull, limit, skip))

            if res.ok:
                res = res.json()
                if int(res['skipped']) + int(res['items']) == int(res['total']):
                    anextflag = False
                else:
                    skip = int(res['skipped']) + int(res['items'])

                if len(affhosts) == 0:
                    affhosts = res['affectedHosts']
                else:
                    for affhost in res['affectedHosts']:
                        affhosts.append(affhost)

            else:
                helper.log_error('Error in retrieving edr.get_affectedHosts(). Request url: {}'.format(res.url))
                helper.log_error('Error in retrieving edr.get_affectedHosts(). Request headers: {}'.format(res.request.headers))
                helper.log_error('Error in retrieving edr.get_affectedHosts(). Request body: {}'.format(res.request.body))
                raise Exception('Error in retrieving edr.get_affectedHosts(). Error: {0} - {1}'.format(str(res.status_code), res.text))

        return affhosts

    except Exception as error:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        helper.log_error("Error in {location}.{funct_name}() - line {line_no} : {error}"
                     .format(location=__name__, funct_name=sys._getframe().f_code.co_name,
                             line_no=exc_tb.tb_lineno, error=str(error)))
        raise


def get_detections(helper, session, base_url, epoch_pull, limit, threatId, affhost):
    try:
        skip = 0
        dnextflag = True
        detections = []

        while(dnextflag):
            filter = {
                'affectedHostId': affhost
            }

            res = session.get('https://api.{0}/ft/api/v2/ft/threats/{1}/detections?sort=-rank&from={2}&filter={3}&limit={4}&skip={5}'
                    .format(base_url, threatId, epoch_pull, json.dumps(filter), limit, skip))

            if res.ok:
                res = res.json()
                if int(res['skipped']) + int(res['items']) == int(res['total']):
                    dnextflag = False
                else:
                    skip = int(res['skipped']) + int(res['items'])

                if len(detections) == 0:
                    detections = res['detections']
                else:
                    for detection in res['detections']:
                        detections.append(detection)
            else:
                helper.log_error('Error in retrieving edr.get_detections(). Request url: {}'.format(res.url))
                helper.log_error('Error in retrieving edr.get_detections(). Request headers: {}'.format(res.request.headers))
                helper.log_error('Error in retrieving edr.get_detections(). Request body: {}'.format(res.request.body))
                raise Exception('Error in retrieving edr.get_detections(). Error: {0} - {1}'.format(str(res.status_code), res.text))

        return detections

    except Exception as error:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        helper.log_error("Error in {location}.{funct_name}() - line {line_no} : {error}"
                     .format(location=__name__, funct_name=sys._getframe().f_code.co_name,
                             line_no=exc_tb.tb_lineno, error=str(error)))
        raise