"""Passivetotal Client."""
import requests
import six
import re

from passivetotal.libs.dns import DnsRequest
from passivetotal.libs.ssl import SslRequest
from passivetotal.libs.enrichment import EnrichmentRequest
from passivetotal.libs.attributes import AttributeRequest
from passivetotal.libs.trackers import TrackersRequest
from passivetotal.libs.services import ServicesRequest
from passivetotal.libs.whois import WhoisRequest
from passivetotal.libs.actions import ActionsClient
from passivetotal.libs.account import AccountClient

from custom_passivetotal.libs.articles import ArticlesRequest
from custom_passivetotal.libs.reputation import ReputationRequest

from errors import QuotaException
from passivetotal_utils import \
    setup_logging, create_requests_proxy_dict, get_pt_config
from passivetotal_utils import EVENTS_PER_PAGE, PAGE_LIMIT


CERTIFICATES_COMMON_KEYS = [
    'CommonName',
    'OrganizationName',
    'AlternativeNames',
    'OrganizationUnitName',
    'StreetAddress',
    'LocalityName',
    'StateOrProvinceName',
    'Country',
]

IPV4_REGEX = re.compile(
    r"""^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?).){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$""")


class PTClient(object):
    """Provide Abstraction over PassiveTotal API upto Tab level (DNS, Components, Trackers, etc.)."""

    def __init__(self, session_key):
        """Initialize object."""
        self.session_key = session_key
        self.logger = setup_logging(self.session_key)
        self.setup_configs()

    # Decorator
    def handle_errors(method):
        """Handle errors in response."""
        def wrapper(self, *args, **kwargs):
            try:
                response = method(self, *args, **kwargs)
            except requests.exceptions.HTTPError as ex:
                status_code = ex.response.status_code

                if status_code == 400:
                    raise Exception('Bad Request, Check Query Parameters that are passed: {}'.format(ex))

                elif status_code == 401:
                    raise Exception("Invalid PassiveTotal Account Credentials")

                elif status_code == 404:
                    # Check if an error occured due to resource is not available
                    try:
                        response = ex.response.json()
                    except Exception:
                        raise ex

                    if 'message' in response:
                        raise Exception(response['message'])
                    else:
                        raise ex

                elif status_code == 429:
                    raise QuotaException(self.session_key)

                elif status_code in range(500, 599):
                    raise Exception("An interval server error has occured {}".format(ex))

                else:
                    raise ex

            except requests.exceptions.ConnectionError as ex:
                err_msg = "Error while connecting to PassiveTotal Platform: {}".format(ex)
                raise Exception(err_msg)

            except requests.exceptions.Timeout as ex:
                err_msg = "Timeout while requesting data: {}".format(ex)
                raise Exception(err_msg)

            except requests.exceptions.RequestException as ex:
                err_msg = "Error while requesting data: {}".format(ex)
                raise Exception(err_msg)

            else:
                return response

        return wrapper

    def setup_configs(self):
        """Set the configurations."""
        proxies = create_requests_proxy_dict(self.session_key)
        username, password = get_pt_config(self.session_key)
        if not(username and password):
            raise Exception(
                'No account configured. Configure PassiveTotal account in the "Configuration" dashboard of Add-on.')

        self.config_args = [
            username,
            password
        ]
        self.config_kwargs = {
            'http_proxy': proxies.get('http', None),
            'https_proxy': proxies.get('https', None),
            'headers': {'PT-Integration': 'Splunk v1.0.0'},
        }

    def is_ip_addr(self, query):
        """Check if given query is of type IP Address."""
        if not isinstance(query, six.string_types):
            return False
        try:
            if IPV4_REGEX.search(query):
                return True
            else:
                return False
        except Exception:
            return False

    def get_tab(self, tab, params={}):
        """
        Return curated data of given tab.

        :param tab: Name of the tab for which data will be returned.
        :param params: API Parameters, specific to tab.
        :throws QuotaException: If API Quota is reached.
        """
        # Pre Condition, continue only if it return None else return response as is
        func = 'pre_{}'.format(tab)
        if hasattr(self, func):
            response = getattr(self, func)(params)
            if response is not None:
                return response

        response = self._fetch_tab(tab, params)
        response = self._process_tab(tab, response, params)
        return response

    @handle_errors
    def _fetch_tab(self, tab, params):
        """Call fetch_<tab>."""
        func = 'fetch_{}'.format(tab)
        if hasattr(self, func):
            response = getattr(self, func)(params)
        else:
            raise Exception('Could not find "{}" function!'.format(func))
        return response

    def _process_tab(self, tab, response, params):
        """Call process_<tab>, if exists."""
        # General Processing
        func = 'process_{}'.format(tab)
        if hasattr(self, func):
            response = getattr(self, func)(response, params)
        return response

    def get_results_with_pagination(self, params, tab):
        """
        Paginate through the API and return results.

        :param params: Parameters to pass in the API Call
        :param tab: The name of the datatset for which data is to be fetched

        :return list of events
        """
        attribute_request = AttributeRequest(*self.config_args, **self.config_kwargs)

        func = "get_host_attribute_" + tab
        if not hasattr(attribute_request, func):
            raise Exception('Pagination is not supported for "{}" tab'.format(tab))

        page = 0
        all_events = []

        while page < PAGE_LIMIT:
            params['page'] = page

            response = getattr(attribute_request, func)(**params)
            response_events = response.get("results", [])
            no_of_events = len(response_events)

            # extend() the orignial list as its performance wise cheaper when adding multiple elements than append()
            all_events.extend(response_events)

            if no_of_events < EVENTS_PER_PAGE:
                break
            page += 1

        return all_events

    def fetch_articles(self, params):
        """Fetch articles."""
        return ArticlesRequest(*self.config_args, **self.config_kwargs).get_articles(**params)

    def process_articles(self, response, params):
        """Process articles."""
        res = []
        if isinstance(response, dict):
            total_articles = response.get('totalRecords', 0)
            if int(total_articles) > 0:
                res = response.get("articles", [])
        return res

    def fetch_reputation(self, params):
        """Fetch reputation."""
        return ReputationRequest(*self.config_args, **self.config_kwargs).get_reputation(**params)

    def fetch_resolutions(self, params):
        """Fetch resolutions."""
        return DnsRequest(*self.config_args, **self.config_kwargs).get_passive_dns(**params)

    def process_resolutions(self, response, params):
        """Process resolutions."""
        # Switch resolutions to dns, if query is of type IP
        if self.is_ip_addr(params.get('query')):
            return [result for result in response.get('results', []) if result.get('resolveType', "") == 'domain']
        else:
            return [result for result in response.get('results', []) if result.get('resolveType', "") == 'ip']

    def fetch_whois(self, params):
        """Fetch whois."""
        params['compact_record'] = True
        params['history'] = True
        return WhoisRequest(*self.config_args, **self.config_kwargs).get_whois_details(**params)

    def process_whois(self, response, params):
        """Process whois."""
        data = []
        updated_date_lookup = []
        for result in response.get('results', []):

            # keep only the first occurance of events having same registryUpdatedAt (just different lastLoadedAt)
            registry_updated_at = result.get('registryUpdatedAt')
            if registry_updated_at in updated_date_lookup:
                continue
            else:
                updated_date_lookup.append(registry_updated_at)

            # Noramalize "compact" records
            for key, value in result.get('compact', {}).items():
                if not value['values']:
                    continue
                result[key] = []
                for event in value['values']:
                    if not event:
                        continue
                    suffix = ', '.join(sorted(event[1]))
                    result[key].append('{} ({})'.format(event[0], suffix))
            result.pop('compact', None)
            data.append(result)

        return sorted(data, key=lambda e: e.get('registryUpdatedAt', ""), reverse=True)

    def fetch_whois_search(self, params):
        """Fetch whois search records."""
        return WhoisRequest(*self.config_args, **self.config_kwargs).search_whois_by_field(**params)

    def process_whois_search(self, response, params):
        """Process certificates."""
        return response.get("results", [])

    def fetch_certificates(self, params):
        """Fetch certificates."""
        if 'field' not in params:
            params['field'] = 'name'
        return SslRequest(*self.config_args, **self.config_kwargs).search_ssl_certificate_by_field(**params)

    def process_certificates(self, response, params):
        """Process certificates."""
        data = []
        for result in response.get('results', []):
            for key in CERTIFICATES_COMMON_KEYS:
                values = []
                issuer_data = result.get('issuer' + key)
                subject_data = result.get('subject' + key)

                if issuer_data:
                    if isinstance(issuer_data, six.string_types):
                        values.append(issuer_data + ' (issuer)')
                    elif isinstance(issuer_data, list):
                        values.extend([item + ' (issuer)' for item in issuer_data])

                if subject_data:
                    if isinstance(subject_data, six.string_types):
                        values.append(subject_data + ' (subject)')
                    elif isinstance(subject_data, list):
                        values.extend([item + ' (subject)' for item in subject_data])

                result[key[:1].lower() + key[1:]] = values
            data.append(result)
        return data

    def pre_subdomains(self, params):
        """Pre condition of subdomains."""
        if self.is_ip_addr(params.get('query')):
            return []

    def fetch_subdomains(self, params):
        """Fetch subdomains."""
        return EnrichmentRequest(*self.config_args, **self.config_kwargs).get_subdomains(**params)

    def fetch_trackers(self, params):
        """Fetch trackers."""
        return self.get_results_with_pagination(params, tab="trackers")

    def process_trackers(self, response, params):
        """Process trackers."""
        return response

    def fetch_trackers_search(self, params):
        """Fetch trackers."""
        return TrackersRequest(*self.config_args, **self.config_kwargs).get_trackers_search(**params)

    def process_trackers_search(self, response, params):
        """Process trackers."""
        return response.get("results", [])

    def fetch_components(self, params):
        """Fetch components."""
        return self.get_results_with_pagination(params, tab="components")

    def process_components(self, response, params):
        """Process components."""
        data = []
        for result in response:
            if result.get('version'):
                result['value'] = '{} (v{})'.format(result['label'], result['version'])
            else:
                result['value'] = result['label']
            data.append(result)
        return data

    def fetch_hostpairs(self, params):
        """Fetch hostpairs."""
        if not params.get('direction'):
            params['direction'] = 'pairs'
        return self.get_results_with_pagination(params, tab="pairs")

    def process_hostpairs(self, response, params):
        """Process hostpaires."""
        return response

    def fetch_cookies(self, params):
        """Fetch cookies."""
        return self.get_results_with_pagination(params, tab="cookies")

    def process_cookies(self, response, params):
        """Process cookies."""
        return response

    def fetch_services(self, params):
        """Fetch services."""
        return ServicesRequest(*self.config_args, **self.config_kwargs).get_services(**params)

    def process_services(self, response, params):
        """Process services."""
        data = []
        if response.get('results'):
            for result in response['results']:
                slim_record = dict()
                slim_record['firstSeen'] = result.get('firstSeen')
                slim_record['lastSeen'] = result.get('lastSeen')
                slim_record['portNumber'] = result.get('portNumber')
                slim_record['protocol'] = result.get('protocol')
                slim_record['status'] = result.get('status')
                data.append(slim_record)
        return data

    def fetch_osint(self, params):
        """Fetch osint."""
        return EnrichmentRequest(*self.config_args, **self.config_kwargs).get_osint(**params)

    def process_osint(self, response, params):
        """Process osint."""
        return response.get('results', [])

    def fetch_hashes(self, params):
        """Fetch hashes."""
        return EnrichmentRequest(*self.config_args, **self.config_kwargs).get_malware(**params)

    def process_hashes(self, response, params):
        """Process hashes."""
        return response.get('results', [])

    def pre_dns(self, params):
        """Pre condition of dns."""
        if self.is_ip_addr(params.get('query')):
            return []

    def fetch_dns(self, params):
        """Fetch dns."""
        return DnsRequest(*self.config_args, **self.config_kwargs).get_passive_dns(**params)

    def process_dns(self, response, params):
        """Process dns."""
        return [result for result in response.get("results", []) if result.get('resolveType', "") == 'domain']

    def fetch_passivedns(self, params):
        """Fetch passivedns."""
        return DnsRequest(*self.config_args, **self.config_kwargs).get_passive_dns(**params)

    def process_passivedns(self, response, params):
        """Process passivedns."""
        return response.get('results', [])

    def fetch_tags(self, params):
        """Fetch whois."""
        return ActionsClient(*self.config_args, **self.config_kwargs).get_tags(**params)

    def fetch_history(self, params):
        """Fetch history."""
        return AccountClient(*self.config_args, **self.config_kwargs).get_account_history(**params)

    def process_history(self, response, params):
        """Process history."""
        return response.get('history', [])

    def fetch_teamstream(self, params):
        """Fetch teamstream."""
        return AccountClient(*self.config_args, **self.config_kwargs).get_account_organization_teamstream(**params)

    def process_teamstream(self, response, params):
        """Process teamstream."""
        return response.get('teamstream', [])

    # Extra custom commands for back version support

    def fetch_ptcomponents(self, params):
        """Fetch ptcomponents."""
        return AttributeRequest(*self.config_args, **self.config_kwargs).get_host_attribute_components(**params)

    def fetch_ptenrich(self, params):
        """Fetch ptenrich."""
        enrichment = EnrichmentRequest(*self.config_args, **self.config_kwargs).get_enrichment(**params)
        classification = ActionsClient(*self.config_args, **self.config_kwargs).get_classification_status(**params)
        return (enrichment, classification)

    def fetch_pthistory(self, params):
        """Fetch ptphistory."""
        return AccountClient(*self.config_args, **self.config_kwargs).get_account_organization_teamstream()

    def fetch_pthostpairs(self, params):
        """Fetch pthostpairs."""
        return AttributeRequest(*self.config_args, **self.config_kwargs).get_host_attribute_pairs(**params)

    def fetch_ptpdns(self, params):
        """Fetch ptpdns."""
        return DnsRequest(*self.config_args, **self.config_kwargs).get_passive_dns(**params)

    def fetch_ptssl(self, params):
        """Fetch ptssl."""
        return SslRequest(*self.config_args, **self.config_kwargs).get_ssl_certificate_history(**params)

    def fetch_pttrackers(self, params):
        """Fetch pttrackers."""
        return AttributeRequest(*self.config_args, **self.config_kwargs).get_host_attribute_trackers(**params)

    def fetch_ptupdns(self, params):
        """Fetch ptpudns."""
        return DnsRequest(*self.config_args, **self.config_kwargs).get_unique_resolutions(**params)

    def fetch_ptwhois(self, params):
        """Fetch ptwhois."""
        params['compact_record'] = True
        return WhoisRequest(*self.config_args, **self.config_kwargs).get_whois_details(**params)
