import re
import copy
import json
import sys
import os
from datetime import datetime, timedelta, timezone
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "taxii2client"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "stix2"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "BaseClient1"))
from taxii2client.v21 import Server, Collection, as_pages
from BaseClient1.baseclient import BaseClient
from stix2 import Indicator
from base64 import b64encode
stix_regex_parser = re.compile(r"([\w-]+?):(\w.+?) (?:[!><]?=|IN|MATCHES|LIKE) '(.*?)' *[OR|AND|FOLLOWEDBY]?")


class Taxii2Client(object):
    def __init__(self, discovery_url, username=None, password=None, port=None, collection_url=None, logger=None,
                 verify_cert=False, source_confidence=None, user_verdict=None, cert=None, discovery_url_path=""):
        self.base_client = BaseClient()
        self.discovery_url = discovery_url if discovery_url.endswith("/") else f"{discovery_url}/"
        self.discovery_url_path = discovery_url_path
        self.username = username
        self.password = password
        self.port = port
        self.conn = None
        self.client_conn = None
        self.verify_cert = verify_cert
        self.job_errors = []
        self.collection_url = collection_url
        self.source_confidence = source_confidence
        self.headers = self.prepare_headers(username, password)
        self.user_verdict = user_verdict
        self.logger = logger
        self.certs = cert
        self.supported_iocs = ["url", "domain", "ipv4", "ipv6", "md5", "sha1", "sha256"]
        self.iocs2_stix_mapping = {
            "url": "url:value=",
            "domain": "domain-name:value=",
            "ipv4": "ipv4-addr:value=",
            "ipv6": "ipv6-addr:value=",
            "md5": "file:hashes.md5=",
            "sha1": "file:hashes.sha1=",
            "sha256": "file:hashes.sha256="
        }
        self.stix_to_ioc_mapping = {
            "url:value": "url",
            "domain-name:value": "domain",
            "ipv4-addr:value": "ipv4",
            "ipv6-addr:value": "ipv6",
            "file:hashes.md5": "md5",
            "file:hashes.sha1": "sha1",
            "file:hashes.sha256": "sha256"
        }
        self.IOC_TYPE_MAPPER = {
            "url": "url",
            "domain-name": "domain",
            "ipv4-addr": "ipv4",
            "ipv6-addr": "ipv6",
            "file": "file"
        }
        self.HASH_MAPPING = {
            "hashes.md5": "md5",
            "hashes.sha1": "sha1",
            "hashes.sha256": "sha256",
            "hashes.sha512": "sha512"
        }
        self.comment = ''
        self.setup_connection()

    def setup_connection(self):
        """ Setup connection to the taxii server based on the discovery url and user credentials """
        self.conn = Server(url=self.discovery_url, user=self.username, password=self.password, verify=self.verify_cert,
                           cert=self.certs)

    def prepare_headers(self, username, password):
        auth_str = b64encode(b":".join((username.encode("latin1"), password.encode("latin1")))).decode("ascii")
        headers = {
            'User-Agent': 'taxii2-client/2.3.0',
            'Accept': 'application/taxii+json;version=2.1',
            'Authorization': f"Basic {auth_str}"
        }
        return headers

    def test_connection(self):
        try:
            status, rsp_obj = self.request_handler(url=self.discovery_url, method='GET', headers=self.headers,
                                                   return_json=False, return_json_data=True)
            self.logger.info('Authorization successful with Taxii Server')
            return status
            # return True if li else False
        except Exception:
            raise Exception("Authentication error")

    def get_api_routes(self):
        """ Returns all api routes available """
        status = True
        api_routes = []
        status, resp_obj = self.request_handler(url=self.discovery_url, method="GET", headers=self.headers,
                                                return_json_data=True, return_json=False)
        self.logger.info(f"Status for API routes: {status} and Api routes are {resp_obj}")
        all_api_routes = resp_obj.get('api_roots')

        for api_route in all_api_routes:
            if not api_route.startswith("http"):
                # if discovery url exist in api root
                api_route = api_route.replace(self.discovery_url_path, "")
                api_route = self.discovery_url + api_route if not api_route.startswith("/") else \
                    self.discovery_url + api_route.lstrip("/")
            status, resp_obj = self.request_handler(url=api_route, method="GET", headers=self.headers,
                                                    return_json_data=True, return_json=False)
            route = {'url': api_route}
            try:
                route.update({
                    'title': resp_obj.get('title'),
                    'description': resp_obj.get('description'),
                    'versions': resp_obj.get('versions'),
                    'max_content_length': resp_obj.get('max_content_length')
                })
            except Exception as err:
                raise Exception(f'Api route {api_route.url} does not'
                                                  f' contain description due to reason: {err}')
            api_routes.append(route)
        return status, api_routes

    def get_collections(self, api_route_url):
        """ Return available collections of provided api route"""
        if not api_route_url:
            raise Exception("Collection URL not provided")
        status = True
        collection_url = ''
        collections, parse_collections = [], []

        status, api_routes = self.get_api_routes()
        for route_obj in api_routes:
            if route_obj.get('url') == api_route_url:
                collection_url = f'{api_route_url}collections/' if api_route_url.endswith('/')\
                    else f'{api_route_url}/collections/'
                status, resp = self.request_handler(url=collection_url, method="GET", headers=self.headers,
                                                    return_json_data=True, return_json=False)
                collections.extend(resp.get('collections', []))
                break
        if not collections:
            raise Exception("Collections not found")

        for collection in collections:
            collection_id = collection.get("id")
            parse_collections.append({
                'url': f'{collection_url}{collection_id}/',
                'meta': {
                    "can_read": collection.get("can_read"),
                    "can_write": collection.get("can_write"),
                    "description": collection.get("description"),
                    "id": collection_id,
                    "media_types": collection.get("media_types"),
                    "title": collection.get("title")
                }
            })
        return status, parse_collections

    def extract_iocs_with_regex(self, each_ioc, pattern, ioc_type_list, collection_url):
        temp_list = []
        for match in stix_regex_parser.findall(pattern):
            c_type, sub_type, value = match
            mapped_type = self.IOC_TYPE_MAPPER.get(c_type, '')
            if mapped_type == 'file':
                mapped_type = self.HASH_MAPPING.get(sub_type.lower())
            if mapped_type in ioc_type_list:
                ioc_copy = each_ioc.copy()
                ioc_copy.update({"ioc": value, "type": mapped_type, "collection_url": collection_url})
                temp_list.append(ioc_copy)
        return temp_list

    def extract_iocs_using_index(self, each_ioc, pattern, ioc_type_list, collection_url):
        pattern = pattern.replace(" ", "")
        ioc_list = pattern.split('=')
        if ioc_list and len(ioc_list) >= 2:
            temp_ioc_type = ioc_list[0][1:]
            ioc_value = ioc_list[1][1:-2]
            ioc_type = self.stix_to_ioc_mapping.get(temp_ioc_type)
            if ioc_type and (ioc_type in ioc_type_list):
                each_ioc.update({'ioc': ioc_value, 'type': ioc_type, "collection_url": collection_url})
                return [each_ioc]
        return []

    def parse_stix_data(self, objects, ioc_type_list, collection_url, confidence_value):
        """Filtering indicators based on pattern and other stix objects """
        result_list, other_objects = [], {}
        obj_type_list = ['marking-definition', 'identity']
        ignore_confidence = False if confidence_value else True

        for each_obj in objects:
            obj_id = each_obj.get('id', '')
            obj_type = each_obj.get('type', '')
            if obj_type == 'indicator':
                confidence = int(each_obj.get('confidence', 0))
                if confidence and (not ignore_confidence):
                    if confidence < confidence_value:
                        continue
                pattern = each_obj.get('pattern')
                if not pattern:
                    continue
                required_iocs = self.extract_iocs_with_regex(each_obj, pattern, ioc_type_list, collection_url)
                if not required_iocs:
                    required_iocs = self.extract_iocs_using_index(each_obj, pattern, ioc_type_list, collection_url)
                result_list.extend(required_iocs)

            elif obj_type in obj_type_list:
                other_objects.update({obj_id: each_obj})

        return result_list, other_objects

    def request_handler(self, url, method, return_json_data=True, **kwargs):
        json_response = {}
        kwargs.update({
            'url': url,
            'method': method
        })
        status, comment, resp, errors = self.base_client.http_method(**kwargs)

        if return_json_data:
            try:
                json_response = resp.json()
            except Exception as err:
                pass
            return status, json_response
        return status, resp

    def is_collection_readable(self, collection_url):

        status, rsp_obj = self.request_handler(url=collection_url, method='GET',
                                               headers=self.headers, return_json=False,
                                               return_json_data=True)
        return rsp_obj.get("can_read", False)

    def get_stix_objects(self, collection_url, args, max_limit, ioc_type_list, confidence):
        """Fetch stix objects from provided collection"""
        response_list, other_objects = [], {}
        hits = 0
        if self.is_collection_readable(collection_url):
            url = collection_url.rstrip("/")
            url = f'{url}/objects/'
            more = True
            while more:
                hits += 1
                status, stix_object = self.request_handler(url=url, method='GET', params=args,
                                                           headers=self.headers, return_json=False,
                                                           return_json_data=True)
                more = stix_object.get('more', False)
                if stix_object and stix_object.get('objects'):
                    objects = stix_object.get('objects')
                    """Isolating indicators and other stix objects for IOCs enrichment later"""
                    #resp, other_objs = self.parse_stix_data(objects, ioc_type_list, collection_url, confidence)
                    response_list.extend(objects)
                    #self.logger.info(f"IOCs extracted till now {len(response_list)}")
                    #other_objects.update(other_objs)
                else:
                    break

                if (len(response_list) >= max_limit) or (hits > 100):
                    break
        else:
            message = f'Read access is not allowed to collection url {collection_url}'
            self.logger.info(message)

        if response_list:
            return response_list[:max_limit], other_objects
        return response_list, other_objects

    def get_custom_stix_obj(self, collection_url, obj_id):
        """Get single object from provided collection based on object id"""
        base_url = f'{collection_url}/{obj_id}'
        status, resp = self.request_handler(url=base_url, method='GET', headers=self.headers,
                                            return_json=False, return_json_data=True)
        result = {}
        if resp and resp.get('objects'):
            result = resp.get('objects')[0]
        return result

    def enrich_iocs(self, stix_iocs, other_stix_objs):
        """Enrich IOCs based on 'created_by_ref' id and 'object_marking_refs' id"""
        final_response = []
        for ioc in stix_iocs:
            identity_ref = ioc.get('created_by_ref', '')
            if identity_ref:
                identity_obj = other_stix_objs.get(identity_ref)
                if identity_obj:
                    ioc.update({"identity_obj": identity_obj})
                else:
                    identity_obj = self.get_custom_stix_obj(ioc.get('collection_url'),
                                                            identity_ref)
                    if identity_obj:
                        ioc.update({"identity_obj": identity_obj})

            marking_ref = ioc.get('object_marking_refs', [])
            if marking_ref:
                marking_list = []
                for mark_id in marking_ref:
                    marking_obj = other_stix_objs.get(mark_id)
                    if not marking_obj:
                        marking_obj = self.get_custom_stix_obj(ioc.get('collection_url'),
                                                               mark_id)
                        if not marking_obj:
                            continue
                    marking_list.append(marking_obj)
                if marking_list:
                    ioc.update({"marking_obj": marking_list})
            ioc.pop("collection_url")
            ioc.update({'source_confidence': self.source_confidence, 'user_verdict': self.user_verdict})
            final_response.append(ioc)
        return final_response

    def get_objects(self, params=None):
        """
        Fetches objects from provided collection otherwise fetches objects
        from all available collections
        """
        status, begin_time = True, None
        stix_ioc_objects, collections = [], []
        utc_time = params.get('start_date', datetime.utcnow().timestamp())
        limit = params.get('max_limit', 1000)
        ioc_type = params.get('ioc_type')
        filters = params.get("filter", {})
        confidence = int(filters.get('confidence', 0))
        filter_source = filters.get("source_url")
        args, other_objects = None, {}

        if not ioc_type:
            ioc_type = self.supported_iocs
        if isinstance(ioc_type, str):  # Backward Compatibility
            ioc_type = [ioc_type]

        if utc_time:
            begin_time = datetime.fromtimestamp(utc_time).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            args = {"added_after": begin_time}
        # else:
        #     begin_time = datetime.now(timezone.utc) - timedelta(days=days)
        self.logger.info(f'Time --> {begin_time}')

        if filter_source:
            self.logger.info(f"filter source: {filter_source}")
            collections = filter_source

        elif self.collection_url:
            """If multiple collections provided, split them on comma delimiter"""
            self.logger.info(f"collection URL: {self.collection_url}")
            collections = self.collection_url.split(',')

        elif self.discovery_url:
            """Fetch all available collections if no collection provided"""
            self.logger.info(f"Discovery URL: {self.discovery_url}")
            status, api_routes = self.get_api_routes()
            self.logger.info(f"Api routes call status: {status} and API routes are {api_routes}")
            collections = []

            for api_route in api_routes:
                status, collection = self.get_collections(api_route.get('url'))
                self.logger.info(f"collection call status: {status} and collection are {collection}")
                if not collection:
                    continue
                for c in collection:
                    if not c.get("url"):
                        continue
                    collections.append(c.get("url"))
            self.logger.info(f"Total collections are: {collections}")

        if collections:
            """Get IOCs and other stix objects from each collection"""
            for each_collection in collections:
                collection = each_collection.strip()
                self.logger.info(f'Each Collection -->  : {collection}')
                # TODO NEED TO UPDATE THIS
                temp_ioc_objects, other_objs = self.get_stix_objects(collection, args,
                                                                     limit, ioc_type,
                                                                     confidence)

                stix_ioc_objects.extend(temp_ioc_objects)
                other_objects.update(other_objs)
                if len(stix_ioc_objects) >= limit:
                    break

            """Enrich IOCs by adding Identity and Marking Information if available"""
            if stix_ioc_objects:
                """
                if other_objects:
                    stix_ioc_objects = self.enrich_iocs(stix_ioc_objects, other_objects)
                else:
                    for ioc in stix_ioc_objects:
                        ioc.update({'source_confidence': self.source_confidence, 'user_verdict': self.user_verdict})
                        ioc.pop("collection_url")
                """
        else:
            raise Exception("Either failed to retrieve the collections or they do not exist")

        return status, stix_ioc_objects[:limit]

    def push_stix_objects(self, params): # Not tested
        collection_url = params.get('url')
        iocs = params.get('iocs')
        unpushed_iocs = []
        status = True

        if not (collection_url and iocs):
            raise Exception("Collection url or indicators not found")

        self.client_conn = Collection(collection_url, user=self.username, password=self.password)
        if self.client_conn:
            for each_ioc in iocs:
                tags = each_ioc.get('tags', [])
                tags.insert(0, 'malicious-activity')
                ioc_value = each_ioc.get('ioc')
                ioc_type = self.iocs2_stix_mapping.get(each_ioc.get('type'))
                if not ioc_type:
                    raise Exception(f"IOC type {each_ioc.get('type')} not supported")
                stix_object = Indicator(
                    name="Deployed from Strikeready",
                    indicator_types=tags,
                    pattern=f"[{ioc_type}'{ioc_value}']",
                    pattern_type="stix")
                each_indicator = json.loads(stix_object.serialize())
                results = self.client_conn.add_objects(each_indicator)
                if results.status != 'complete':
                    unpushed_iocs.append(ioc_value)
            if len(unpushed_iocs) == len(iocs):
                raise Exception("Unable to pushed stix")
            elif unpushed_iocs:
                self.comment = f"Unable to push these stix {unpushed_iocs}"

        else:
            raise Exception(f'No read access is allowed to the provided collection'
                                              f' url {collection_url}')
        return status, {}
