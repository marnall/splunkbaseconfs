import json
import sys
import time
import re
import StringIO
import tldextract
import os
from Utils.app_env import AppEnv
from domaintools import API
from domaintools import __version__ as dt_api_version
from domaintools.exceptions import NotFoundException
from domaintools.exceptions import NotAuthorizedException
from domaintools.exceptions import BadRequestException
from domaintools.exceptions import InternalServerErrorException
from domaintools.exceptions import ServiceUnavailableException
from domaintools.exceptions import IncompleteResponseException
from domaintools.exceptions import ServiceException
import socket

import splunk.Intersplunk
import splunk.rest
from splunk.clilib import cli_common as cli
import splunk.entity as en

app_env = AppEnv()
cache_path = os.path.join(app_env.app_home, "default", "data",
                          "tld_cache.json")
tldextract_cached = tldextract.TLDExtract(cache_file=cache_path)


def getCredentials(sessionKey):
    """Get the api_key from the Splunk password store.
    """
    headers, payloadstr = splunk.rest.simpleRequest('/services/domaintools_credentials', method='POST',
                                                    sessionKey=sessionKey,
                                                    postargs={})
    payload = json.loads(payloadstr)
    if 'username' in payload:
        return payload['username'], payload['password']
    return '', ''


def flatten(info_dict, result_dict=None, prefix=""):
    if result_dict is None:
        result_dict = {}

    if not hasattr(info_dict, "items"):
        return info_dict

    for item_key, item_value in info_dict.items():
        if prefix:
            new_prefix = "{0}_{1}".format(prefix, item_key)
        else:
            new_prefix = item_key

        if hasattr(item_value, "items"):
            flatten(item_value, result_dict, new_prefix)
        elif isinstance(item_value, list):
            result_dict[new_prefix] = map(str, item_value)
        else:
            result_dict[new_prefix] = item_value

    return result_dict


def gen_message(message, sessionKey):
    splunk.rest.simpleRequest('/services/messages', method='POST',
                              sessionKey=sessionKey,
                              postargs={'name':
                                        'DomainTools error', 'value': message,
                                        'severity': 'error'})


class UnknownModeException(Exception):
    def __init__(self, mode):
        self.mode = mode

    def __str__(self):
        return "Unknown operating mode: {0}".format(self.mode)


class UnknownFieldException(Exception):
    def __init__(self, field):
        self.field = field

    def __str__(self):
        return "Unknown operating field: {0}".format(self.field)


def make_query(api, query, mode, field=None):
    if mode == "whois_parsed":
        try:
            results = api.parsed_whois(query)
            results = results.response()
        except IncompleteResponseException as ex:
            results = results.data()
            pass
    elif mode == "whois":
        results = api.whois(query).response()
    elif mode == "domain_profile":
        results = api.domain_profile(query).response()
    elif mode == "reputation":
        results = api.reputation(query, include_reasons=True).response()
    elif mode == "risk" or mode == "risk_beta":
        beta = mode == "risk_beta"
        results = api.risk(query, include_reasons=True, beta=beta).response()
        if "components" in results:
            components = []
            for component in results["components"]:
                name = component["name"]
                risk_score = str(component["risk_score"])
                components.append(name + " - " + risk_score)
            results["components"] = components

    elif mode == "whois_reputation":
        # Query parsed whois and reputation endpoints and then merge output
        try:
            w_results = api.parsed_whois(query)
            w_results = w_results.response()
        except IncompleteResponseException as ex:
            w_results = w_results.data()
            pass
        r_results = api.reputation(query, include_reasons=True).response()
        results = w_results.copy()
        results.update(r_results)
    elif mode == "whois_risk":
        # Query parsed whois and reputation endpoints and then merge output
        try:
            w_results = api.parsed_whois(query)
            w_results = w_results.response()
        except IncompleteResponseException as ex:
            w_results = w_results.data()
            pass
        r_results = api.risk(query, include_reasons=True).response()
        results = w_results.copy()
        results.update(r_results)
    elif mode == "whois_risk_beta":
        # Query parsed whois and reputation endpoints and then merge output
        try:
            w_results = api.parsed_whois(query)
            w_results = w_results.response()
        except IncompleteResponseException as ex:
            w_results = w_results.data()
            pass
        r_results = api.risk(query, include_reasons=True, beta=True).response()
        results = w_results.copy()
        results.update(r_results)
    elif mode == "whois_history":
        results = api.whois_history(query).response()
    elif mode == "reverse_whois":
        results = api.reverse_whois(query).response()
    elif mode == "reverse_ns":
        results = api.reverse_name_server(query).response()
    elif mode == "reverse_ip":
        # This functionality was in dtapi.py so it has to be moved here
        try:
            socket.inet_aton(query)
            results = api.host_domains(query).response()
        except Exception as ex:
            results = api.reverse_ip(query).response()

    elif mode == "hosting_history":
        results = api.hosting_history(query).response()
    elif mode == "registrant_alert":
        results = api.registrant_monitor(query).response()["alerts"]
        for result in results:
            result["query"] = query
    elif mode == "ip_monitor":
        results = api.ip_monitor(query).response()["alerts"]
        for result in results:
            result["query"] = query
    else:
        raise UnknownModeException(mode)
    if hasattr(results, "items"):
        results = [results]
    return results


def json2tabular(jsonrecord, dictrecord, keyname=None):
    try:
        if type(jsonrecord) is list or type(jsonrecord) is dict:
            for k in jsonrecord:
                if k == 'domain_risk':
                    if 'risk_score' in jsonrecord[k]:
                        dictrecord['risk_score'] = jsonrecord[k]['risk_score']
                    if 'components' in jsonrecord[k]:
                        for sk in jsonrecord[k]['components']:
                            if sk.get('name') == 'threat_profile':
                                dictrecord['risk_evidence'] = ','.join(sk.get('evidence', []))
                            dictrecord[sk['name']] = sk['risk_score']
                    keyname is None
                    continue
                else:
                    if type(jsonrecord[k]) is list:
                        if keyname is None:
                            tkeyname = k
                        else:
                            tkeyname = "{0}_{1}".format(
                                keyname, k)
                        idx = 1
                        for v in jsonrecord[k]:
                            if type(v) is dict:
                                if 'value' in v:
                                    dictrecord["{0}_{1}".format(
                                        tkeyname, idx)] = v['value']
                                else:
                                    json2tabular(v, dictrecord, "{0}_{1}".format(
                                        tkeyname, idx))
                                    keyname = None

                            else:
                                json2tabular(v, dictrecord, "{0}_{1}".format(
                                    tkeyname, idx))
                                keyname = None

                            idx += 1
                            if idx >= 3:
                                keyname = None
                                break
                    elif type(jsonrecord[k]) is dict:
                        if keyname is None:
                            tkeyname = k
                        else:
                            tkeyname = "{0}_{1}".format(
                                keyname, k)
                        if 'value' in jsonrecord[k]:
                            dictrecord[tkeyname] = jsonrecord[k]['value']
                        else:
                            json2tabular(jsonrecord[k], dictrecord, tkeyname)
                            # keyname = None
                    else:
                        dictrecord[k] = jsonrecord[k]
                        keyname is None
    except TypeError as ex:
        print(ex)


def iris_main(username, api_key, proxy, mode, field, use_ssl, args):
    output_events = list()
    _time = int(round(time.time()))
    api = API(username, api_key, app_partner='splunk',
              app_name=app_env.package_id, https=use_ssl, proxy_url=proxy,
              app_version=app_env.integration_version,
              api_version=dt_api_version, rate_limit=True)

    batches = list()
    batches.append(list())
    batch_idx = 0
    try:
        for srch in args:
            # try:
            # print("srch={0}".format(srch))
            # print("type(srch)={0}".format(type(srch)))
            # print("srch['domain']={0}".format(srch['domain']))
            if type(srch) is not str and 'domain' in srch:
                domain = srch['domain']
            # elif type(srch) is list:
            #     domain = srch[0]
            else:
                domain = srch
                srch = {
                    '_time': _time,
                    'key': domain,
                    'domain': domain,
                    'fooyn': _time,
                    'qwaittime': 0,
                    'queued': _time,
                    'retrieved': _time
                }
            # print("domain={0}".format(domain))
            # print("srch={0}".format(srch))
            # except KeyError as ex:
            #     continue
            # print(srch)
            if field == 'domain':
                extracted = tldextract_cached(domain)
                if extracted.domain == '' or extracted.suffix == '':
                    # skip
                    output_events.append({
                        '_time': _time,
                        'key': domain,
                        'domain': domain,
                        'fooyn': srch.get('fooyn', _time),
                        'qwaittime': _time-int(srch.get('queued', _time)),
                        'queued': srch.get('queued', _time),
                        'retrieved': _time,
                        'note': 'skipped: {extdom} {extsuf}'.format(
                            extdom=extracted.domain,
                            extsuf=extracted.suffix
                        )
                    })
                    continue
                else:
                    domain = "{0}.{1}".format(extracted.domain, extracted.suffix)

            if re.search('[^a-zA-Z0-9\-\.]', domain) or re.search('^[-:\.]', domain) or (field == domain
                                                                                         and (
                    re.search('^[0-9\.]+$', domain) or re.search('^[0-9a-fA-F:]+$', domain))):
                    # skip
                reasons = list()
                if re.search('[^a-zA-Z0-9\-\.]', domain):
                    reasons.append('Non Domain Character')
                if re.search('^[-:\.]', domain):
                    reasons.append('Illegal Domain Starting Character')
                if (field == 'domain'
                    and (
                        re.search('^[0-9\.]+$', domain) or re.search('^[0-9a-fA-F:]+$', domain))):
                    if re.search('^[0-9\.]+$', domain):
                        reasons.append('IP 4 Address')
                    if re.search('^[0-9a-fA-F:]+$', domain):
                        reasons.append('IP 6 Address')

                output_events.append({
                    '_time': _time,
                    'key': domain,
                    'domain': domain,
                    'fooyn': srch.get('fooyn', _time),
                    'qwaittime': _time-int(srch.get('queued', _time)),
                    'queued': srch.get('queued', _time),
                    'retrieved': _time,
                    'note': 'skipped: {reasons}'.format(
                        reasons=','.join(reasons)
                    )
                })
                continue
            batches[batch_idx].append(domain)
            if len(batches[batch_idx]) == 100 or len(','.join(batches[batch_idx])) >= 1400:
                batch_idx += 1
                batches.append(list())
        results = list()
        for batch in batches:
            search_res = list()
            try:
                if mode == 'iris_enrich':
                    # print("batch={0}".format(batch))
                    search_res = api.iris_enrich(*batch).response()
                    results.append(search_res)
                elif mode == "iris_investigate":
                    search_res = api.iris_investigate(**{field: batch}).response()
                    results.append(search_res)
            except BadRequestException as ex:
                # TODO: catch IRIS exceptions
                pass
            except Exception as ex:
                print('{0},{1}'.format(ex, len(','.join(batch))))
                # pass

        for result in results:
            for obj in result['results']:
                output_event = dict()
                output_event["_time"] = _time
                output_event['fooyn'] = srch.get('fooyn', _time)
                output_event['qwaittime'] = _time-int(srch.get('queued', _time))
                output_event['queued'] = srch.get('queued', _time)
                output_event['retrieved'] = _time
                output_event['key'] = obj['domain']
                # print('json2tabular')
                if 'tags' in obj:
                    tags = []
                    for tag in obj['tags']:
                        tags.append(tag['label'])
                    output_event['tags'] = ','.join(tags)
                    obj.pop('tags')

                json2tabular(obj, output_event)
                output_events.append(output_event)
    except Exception as ex:
        print(ex)
    return output_events


def generating_main(username, api_key, proxy, mode, field, use_ssl, args):
    output_events = list()
    _time = time.time()
    if mode == 'reverse_whois':
        api = API(username, api_key, app_partner='splunk',
                  app_name=app_env.package_id, https=use_ssl, proxy_url=proxy,
                  app_version=app_env.integration_version,
                  api_version=dt_api_version,
                  rate_limit=False, mode='purchase')
    else:
        api = API(username, api_key, app_partner='splunk',
                  app_name=app_env.package_id, https=use_ssl, proxy_url=proxy,
                  app_version=app_env.integration_version,
                  api_version=dt_api_version, rate_limit=False)

    skip_modes = [
        'reverse_whois',
    ]
    for domain_or_ip in args:
        if mode not in skip_modes:
            if re.search('[^a-zA-Z0-9\-\.]', domain_or_ip) or re.search('^[-:\.]', domain_or_ip):
                continue
        extracted = tldextract_cached(domain_or_ip)
        if mode not in skip_modes:
            if extracted.domain == '' or extracted.suffix == '':
                continue
            else:
                domain = "%s.%s" % (extracted.domain, extracted.suffix)

        try:
            results = make_query(api, domain_or_ip, mode, field)
            for result in results:
                out_event = {
                    '_time': _time,
                    'key': domain_or_ip,
                    'domain': domain_or_ip,
                    'fooyn': _time,
                    'qwaittime': 0,
                    'queued': _time,
                    'retrieved': _time
                }
                out_event = flatten(result)
                out_event["_raw"] = json.dumps(result)
                out_event["_time"] = _time
                out_event["orig_domain"] = domain_or_ip
                output_events.append(out_event)

        except BadRequestException as ex:
            out_event = {
                '_time': _time,
                'key': domain_or_ip,
                'domain': domain_or_ip,
                'fooyn': _time,
                'qwaittime': 0,
                'queued': _time,
                'retrieved': _time
            }
            out_event["_time"] = _time
            out_event["domain"] = domain_or_ip
            out_event["orig_domain"] = domain_or_ip
            output_events.append(out_event)

    return output_events


def pipeline_main(username, api_key, proxy, mode, pipeline_events, key,
                  use_ssl, silent=False):
    api = API(username, api_key, app_partner='splunk',
              app_name=app_env.package_id, https=use_ssl, proxy_url=proxy,
              app_version=app_env.integration_version,
              api_version=dt_api_version)
    output_events = list()
    _time = time.time()
    for pipeline_event in pipeline_events:
        domain_or_ip = pipeline_event.get(key, None)
        if domain_or_ip is None:
            output_events.append(pipeline_event)
            continue
        if re.search('[^a-zA-Z0-9\-\.]', domain_or_ip):
            out_event = pipeline_event
            out_event["_time"] = _time
            out_event["domain"] = domain_or_ip
            out_event["orig_domain"] = domain_or_ip
            output_events.append(out_event)
            continue
        if re.search('^[-:\.]', domain_or_ip):
            out_event = pipeline_event
            out_event["_time"] = _time
            out_event["domain"] = domain_or_ip
            out_event["orig_domain"] = domain_or_ip
            output_events.append(out_event)
            continue

        extracted = tldextract_cached(domain_or_ip)
        if extracted.domain == '' or extracted.suffix == '':
            out_event = pipeline_event
            out_event["_time"] = _time
            out_event["domain"] = domain_or_ip
            out_event["orig_domain"] = domain_or_ip
            output_events.append(out_event)
            continue
        else:
            domain = "%s.%s" % (extracted.domain, extracted.suffix)

        try:
            results = make_query(api, domain, mode)
            for result in results:
                output_event = dict()
                output_event.update(pipeline_event)
                output_event.update(flatten(result))
                output_event["orig_domain"] = domain_or_ip
                output_events.append(output_event)
        except NotFoundException as ex:
            out_event = pipeline_event
            out_event["_time"] = _time
            out_event["domain"] = domain_or_ip
            out_event["orig_domain"] = domain_or_ip
            output_events.append(out_event)
            continue
        except BadRequestException as ex:
            out_event = pipeline_event
            out_event["_time"] = _time
            out_event["domain"] = domain_or_ip
            out_event["orig_domain"] = domain_or_ip
            output_events.append(out_event)
            continue
        except ServiceUnavailableException as ex:
            if silent:
                continue
            else:
                raise ex
        except NotFoundException as ex:
            output_events.append(pipeline_event)
            if silent:
                continue
            else:
                raise ex
        except NotImplementedError as ex:
            if silent:
                continue
            else:
                raise ex
        except UnknownModeException as ex:
            if silent:
                continue
            else:
                raise ex
        except NotAuthorizedException as ex:
            if silent:
                continue
            else:
                raise ex
        except BadRequestException as ex:
            output_events.append(pipeline_event)
            if silent:
                continue
            else:
                raise ex
        except InternalServerErrorException as ex:
            if silent:
                continue
            else:
                raise ex
        except ServiceUnavailableException as ex:
            if silent:
                continue
            else:
                raise ex
        except ServiceException as ex:
            if silent:
                continue
            else:
                raise ex
        except Exception as ex:
            output_events.append(pipeline_event)
            if silent:
                continue
            else:
                raise ex

    return output_events

def main(inbuf):
    silent = False
    settings = dict()
    sessionkey = re.search(r'sessionKey:(.*)', inbuf).groups(1)[0]
    output_events = dict()
    try:
        buf_fp = StringIO.StringIO(inbuf)
        pipeline_events = splunk.Intersplunk.readResults(buf_fp, settings, True)
        buf_fp.close()
        search = settings["search"].strip(" |")
        generating = (search.lower().startswith("domaintools")
                      and len(pipeline_events) == 0)

        # Get credentials
        try:
            username, api_key = getCredentials(sessionkey)
        except IOError:
            output_events = splunk.Intersplunk.generateErrorResults(
                "No credentials found. Please enter credentials on TA-domaintools setup page")
            splunk.Intersplunk.outputResults(output_events)
            sys.exit(0)

        # Get config file options
        cfg = cli.getConfStanza("domaintools", "domaintools")
        proxy = cfg.get("proxy_url", None)
        new_risk = cfg.get("new_risk", "0")
        if new_risk in ["true", "1", "t"]:
            new_risk = True
        else:
            new_risk = False
        risk_beta = cfg.get("risk_beta", "0")
        if risk_beta in ["true", "1", "t"]:
            risk_beta = True
        else:
            risk_beta = False
        use_ssl = str(cfg.get("use_ssl", "false")).lower()
        if use_ssl in ["true", "1", "t"]:
            use_ssl = True
        else:
            use_ssl = False

        keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
        score_type = options.get("score_type", "iris_enrich")
        whois = options.get("whois", "true")
        mode = options.get("mode", None)
        field = options.get("field", None)
        if whois in ["true", "1", "t"]:
            whois = True
        else:
            whois = False
        # Switch to new risk endpoint depending on options
        if mode is None:
            if whois:
                mode = "whois_{0}".format(score_type)
            else:
                mode = score_type

        silent = str(options.get("silent", "false")).lower()
        if silent in ["true", "1", "t"]:
            silent = True
        else:
            silent = False

        useIris = mode.lower().startswith("iris")
        if useIris:
            if generating:
                output_events = iris_main(
                    username, api_key, proxy, mode, field, use_ssl, keywords)
            else:
                output_events = iris_main(
                    username, api_key, proxy, mode, field, use_ssl, pipeline_events)
        else:
            if generating:
                output_events = generating_main(
                    username, api_key, proxy, mode, field, use_ssl, keywords)
            else:
                output_events = pipeline_main(username, api_key, proxy,
                                              mode, pipeline_events, keywords[0], use_ssl, silent)

    except NotFoundException as ex:
        if silent: #KLUDGE: This var needs to be set before the try block, need to know what default should be
            pass
        else:
            output_events = splunk.Intersplunk.generateErrorResults("DomainTools Message: {0} (code {1})".format(
                ex.reason['error']['message'], ex.reason['error']['code']))
    except NotImplementedError as ex:
        if silent:
            pass
        else:
            message = "DomainTools Error: The API feature you requested has not been implemented: {0}".format(
                mode)
            output_events = splunk.Intersplunk.generateErrorResults(message)
    except UnknownModeException as ex:
        if silent:
            pass
        else:
            output_events = splunk.Intersplunk.generateErrorResults(ex)
    except NotAuthorizedException as ex:
        try:
            api = API(username, api_key, app_partner='splunk',
                      app_name=app_env.package_id, proxy_url=proxy,
                      app_version=app_env.integration_version)
            api.https = use_ssl
            results = api.account_information().response()
            message = "DomainTools Error: not authorized. Credentials are invalid or your license does not include the specified mode: {0}: {1} {2}".format(
                mode, ex.code, ex.reason)
            output_events = splunk.Intersplunk.generateErrorResults(message)
        except NotAuthorizedException as ex2:
            if silent:
                pass
            else:
                # splunk.rest.simpleRequest('/servicesNS/nobody/{0}/saved/searches/Domain%20Analysis%20Datamodel%20Populator/disable'.format(app_env.package_id), method='POST', sessionKey=sessionkey)
                message = "DomainTools API account disabled. Populating search has been disabled to prevent further requests. Please contact support@domaintools.com for assistance."
                output_events = splunk.Intersplunk.generateErrorResults(message)

    except BadRequestException as ex:
        if silent:
            pass
        else:
            message = "DomainTools Error: bad request. Check that your query is correct and try again."
            output_events = splunk.Intersplunk.generateErrorResults(message)
    except InternalServerErrorException as ex:
        if silent:
            pass
        else:
            message = "DomainTools Error: unable to connect to API server"
            output_events = splunk.Intersplunk.generateErrorResults(message)
    except ServiceUnavailableException as ex:
        if silent:
            pass
        else:
            message = "DomainTools Error: {0}".format(ex.reason['error']['message'])
            # gen_message(message, sessionkey)
            output_events = splunk.Intersplunk.generateErrorResults(message)
    except ServiceException as ex:
        if silent:
            pass
        else:
            message = "DomainTools Error: {0}".format(ex.reason['error']['message'])
            # gen_message(message, sessionkey)
            output_events = splunk.Intersplunk.generateErrorResults(message)
    except Exception as ex:
        if silent:
            pass
        else:
            message = "An unknown error occurred: {0}, {1}".format(type(ex), ex)
            output_events = splunk.Intersplunk.generateErrorResults(message)
    return output_events


if __name__ == "__main__":

    # Read results in case we're in a pipeline
    inbuf = ""
    inbuf = sys.stdin.read()
    splunk.Intersplunk.outputResults(main(inbuf))
