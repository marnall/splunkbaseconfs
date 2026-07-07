from schema import Schema, And, Optional
import re

def is_url_valid(url, ssl_only=False):
    if ssl_only:
        http_regex = r'^https://'
    else:
        http_regex = r'^(?:http)s?://'
    regex = re.compile(
        r'%s(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?$' % http_regex # optional port
        , re.IGNORECASE)
    return re.match(regex, url) is not None

def https_validator(url):
    return is_url_valid(url, ssl_only=True)

def http_validator(url):
    return is_url_valid(url)

def tags_validator(tags):
    if tags:
        tags = tags.replace(', ', ',').split(',')
        tag_pattern = re.compile('^[A-Za-z0-9\-\_]+$')
        for tag in tags:
            if not tag_pattern.match(tag):
                return False
        return True
    return False

# TODO fix pattern and use
def search_templates_validator(search_templates):
    if search_templates:
        search_templates = search_templates.replace(', ', ',').split(',')
        search_templates_pattern = re.compile('^[A-Za-z0-9\-\_\/]+$')
        for search_template in search_templates:
            if not search_templates_pattern.match(search_template):
                return False
        return True
    return False

server_schema = Schema({
    'name': And(str, len, error='Invalid name value'),
    'mgmt_scheme_host_port': And(str, len, https_validator, error='Invalid mgmt_scheme_host_port value'),
    Optional('splunk_web_uri', default=''): And(str, len, http_validator, error='Invalid splunk_web_uri value'),
    'username': And(str, len, error='Invalid username'),
    Optional('tags', default=''): And(str, len, tags_validator, error='Invalid tags value'),
    Optional('password_link_alternate', default=''): And(str, len, error='Invalid password_link_alternate'),
    Optional('search_template_link_alternates', default=''): And(str, len, error='Invalid search_templates value'),
    Optional('hec_url', default=''): And(str, len, error='Invalid hec_url value'),
    Optional('hec_token', default=''): And(str, len, error='Invalid hec_token value')
})

SERVER_FIELDS = ['name', 'mgmt_scheme_host_port', 'splunk_web_uri', 'username', 'tags', 'hec_url', 'hec_token','password_link_alternate', 'enable_metrics_search', 'poller_metrics_earliest_time', 'search_template_link_alternates']

auth_schema = Schema({
    'password': And(str, len, error='Invalid password'),
})

AUTH_FIELDS = ['password']

# Supported POST request arguments
ALL_FIELDS = list(set(SERVER_FIELDS + AUTH_FIELDS) - set(['name']))
OPTIONAL_FIELDS = list(set(SERVER_FIELDS + AUTH_FIELDS) - set(['name', 'username', 'mgmt_scheme_host_port']))
