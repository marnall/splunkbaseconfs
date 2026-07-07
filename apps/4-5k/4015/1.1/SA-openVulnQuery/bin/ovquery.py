#!/usr/bin/env python
import sys

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from splunk.clilib import cli_common as cli

from openVulnQuery import query_client
import ovquery_consts as c

APP_NAME = 'SA-openVulnQuery'
CONF_FILE = 'ovquery_settings'
STANZA = 'ovquery_settings'

@Configuration(type='reporting')
class GenerateOpenVulnQuery(GeneratingCommand):
    """ Wrapper for connecton to Cisco's PSIRT openVuln API. Generating command.

    ##Syntax

    .. code-block::
        |ovquery

    ##Description

    Connect to Cisco's PSIRT openVuln API by providing the specific API filter (`get_by`) as seen here:
    https://github.com/CiscoPSIRT/openVulnAPI/tree/master/openVulnQuery#api-filters-required 
    Returned by default is fields of 'advisory_id', 'sir', 'first_published', 'last_updated', 'cves', 'bug_ids',
    'cvss_base_score', 'advisory_title', 'publication_url', 'cwe', 'product_names', 'summary' and possibly others
    depending on the filter, though you can specifiy only specific fields by providing a comma separated list to 
    the `fields` option. The command expects by default a `get_by` and `query` option. The `query` option will 
    depend on what the `get_by` option is set to.

    ##Example

    Get advisories for Cisco products with IOS_XE 3.7.2E

    .. code-block::
        | ovquery get_by="ios_xe" query="3.7.2E"

    """
    get_by = Option(
        require=True,
        doc='''**Syntax:** **get_by=***<string>*
        **Description:** Options are all, advisory, cve, latest, serverity, year, product, ios, ios_xe''',
        ) 	
    adv_type = Option(
        default='cvrf',
        doc='''**Syntax:** **adv_type=***<string>*
        **Description:** Options are cvrf or oval, defaults to cvrf''',
        ) 	
    query = Option(
        require=True,
        doc='''**Syntax:** **model=***<string>*
        **Description:** Query given to the get_by options, such as "3.7.2E"''',
        ) 	
    fields = Option(
        doc='''**Syntax:** **fields=***<fields>*
        **Description:** comma-seperated list of fields, enclose in quotes''',
        ) 	
    def get_credentials(self, username):
        conf = self.service.confs[CONF_FILE][STANZA]
        conf_dict = {k:v for k,v in conf.content.items()}
        storage_passwords=self.service.storage_passwords
        for credential in storage_passwords:
            if credential.content.get('username') == conf_dict[username] and credential.content.get('realm') == APP_NAME:
                clear_password = credential.content.get('clear_password')
                return conf_dict[username], clear_password

    def generate(self):
        (client_id, client_secret) = self.get_credentials(c.ovquery_username)
        client = query_client.OpenVulnQueryClient(client_id, client_secret)
        GET_BY_OPTIONS = set([
            'all', 
            'advisory', 
            'cve',
            'latest',
            'serverity',
            'year',
            'product',
            'ios',
            'ios_xe'
        ])
        record = {}
        exempted_fields = set(['filter'])
        if self.get_by in GET_BY_OPTIONS:
            if self.get_by == 'all':
                response = client.get_by_all(self.adv_type)
            elif self.get_by == 'advisory':
                response = client.get_by_advisory(self.adv_type, self.query)
            elif self.get_by == 'cve':
                response = client.get_by_cve(self.adv_type, self.query)
            elif self.get_by == 'latest':
                response = client.get_by_latest(self.adv_type, self.query)
            elif self.get_by == 'severity':
                response = client.get_by_severity(self.adv_type, self.query)
            elif self.get_by == 'year':
                response = client.get_by_year(self.adv_type, self.query)
            elif self.get_by == 'product':
                response = client.get_by_product(self.adv_type, self.query)
            elif self.get_by == 'ios':
                response = client.get_by_ios(self.adv_type, self.query)
            elif self.get_by == 'ios_xe':
                response = client.get_by_ios_xe(self.adv_type, self.query)
            if self.fields:
                fields = self.fields.split(',')
            else:
                fields = [
                    i for i in
                    dir(response[0])
                    if not i.startswith('_')
                    and i not in exempted_fields
                ]
            for i in response:
                record = {}
                for field in fields:
                    if hasattr(i, '__iter__'):
                        subfields = [
                            x for x in
                            dir(i[0])
                            if not x.startswith('_')
                        ]
                        for s in i:
                            for subfield in subfields:
                                record[field + '_' + subfield] = getattr(s, subfield)
                    else:
                        record[field] = getattr(i, field)
                yield record

dispatch(GenerateOpenVulnQuery, sys.argv, sys.stdin, sys.stdout, __name__)

