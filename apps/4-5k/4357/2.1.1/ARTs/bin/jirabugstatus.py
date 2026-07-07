#!/usr/bin/env python
# coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from __future__ import absolute_import, division, print_function, \
    unicode_literals

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, \
    Option, validators
import sys
import re

from jira import JIRA
from jira.exceptions import JIRAError
from solnlib import credentials as cred
from solnlib.splunkenv import get_conf_key_value
import jira_consts as c
from collections import defaultdict

# Please update the default JIRA info
DEFAULT_JIRA_USER = 'jira_user'
DEFAULT_JIRA_PASSWORD = 'jira_password'
DEFAULT_JIRA_SERVER_URL = 'https://jira.crop.com'


@Configuration()
class JiraBugStatusCommand(StreamingCommand):
    """ Gets the bug status for the given JIRA bug id.

    ##Syntax

    .. code-block::
        jirabugstatus idfield=<typefield>  fields=<fields>

    ##Description

    idfield: Search the bug status for the bug id stored in `idfield` is fetched for each record processed.
    fields: the field list returned, return all fields by default

    ##Example

    Get the bug status with given jira bug id

    .. code-block::
        | index=bugs_index | jirabugstatus idfield=bug_id fields="status, summary, resolution"

    """

    idfield = Option(
        doc='''
        **Syntax:** **idfield=***<idfield>*
        **Description:** Name of the field that has the bug id''',
        require=True, validate=validators.Fieldname())

    fields = Option(
        doc='''
            **Syntax:** **fields=***<fields>*
            **Description:** list of fields returned''',
        require=False, validate=validators.List())

    def stream(self, records):
        jira_server_url = None
        jira_username = None
        jira_password = None
        enabled_jira = False

        app = self._metadata.searchinfo.app

        session_key = self._metadata.searchinfo.session_key
        enabled_jira = bool(int(get_conf_key_value(
            c.jira_conf, c.jira_settings, c.enabled_jira)))
        jira_server_url = get_conf_key_value(
            c.jira_conf, c.jira_settings, c.jira_server_url)

        if not enabled_jira:
            raise Exception('jira is not enable.')

        if jira_server_url is None:
            jira_server_url = DEFAULT_JIRA_SERVER_URL

        cred_mgr = cred.CredentialManager(session_key, app, realm=jira_server_url)

        try:
            password = cred_mgr.get_password('user')
            if password:
                user_pass = password.split(cred_mgr.SEP)
                if len(user_pass) == 1:
                    user_pass = password.split("``")

                jira_username, jira_password = user_pass

            else:
                jira_username = DEFAULT_JIRA_USER
                jira_password = DEFAULT_JIRA_PASSWORD
        except Exception:
            jira_username = DEFAULT_JIRA_USER
            jira_password = DEFAULT_JIRA_PASSWORD

        self.logger.debug('JiraBugStatusCommand: %s', self)  # logs command line
        if enabled_jira and jira_server_url and jira_username and jira_password:

            try:
                splunk_jira = JIRA(
                    options={'server': jira_server_url},
                    basic_auth=(jira_username, jira_password))

                sess_get = splunk_jira._session.get
                record_list = list(records)

                d = defaultdict(list)
                filter_bug_ids = list(
                    filter(lambda x: re.match(r'[A-Z]+-[0-9]+', x),
                           [record[self.idfield] for record in
                            record_list]))

                if self.fields is None:
                    searchfields = ['key', 'status', 'summary', 'resolution']
                else:
                    searchfields = self.fields

                if searchfields == ["*"]:
                    searchfields = 'key,status,summary,resolution,labels,assignee,updated,summary,issuetype,status,reporter,' \
                                   'creator,priority,versions,resolutiondate,project,watches,fixVersions,components'.split(
                        ',')

                search_string = 'key in (' + ','.join(
                    ['"' + item + '"' for item in filter_bug_ids]) + ')'
                try:

                    results = splunk_jira.search_issues(
                        search_string,
                        fields=','.join(searchfields))

                    for result in results:
                        d[result.key] = result


                except BaseException as e:
                    self.logger.error('JiraBugStatusCommand: %s', e)

                for record in record_list:

                    try:
                        id_value = record[self.idfield]

                        issue = None

                        if id_value in filter_bug_ids:

                            if id_value in d.keys():
                                issue = d[id_value]
                            else:
                                issue = splunk_jira.issue(id_value)

                            for search_field in searchfields:
                                record_field = 'jira_' + search_field
                                record[record_field] = None
                                if search_field == 'key':
                                    record[record_field] = issue.id
                                if issue is not None and search_field in \
                                        issue.raw[
                                            'fields']:
                                    issue_field = getattr(issue.fields,
                                                          search_field)
                                    if issue_field is None:
                                        continue;
                                    if search_field in ['versions',
                                                        'fixVersions',
                                                        'components']:
                                        record[record_field] = ','.join(
                                            [version.name for version in
                                             issue_field])
                                    elif search_field in ['assignee',
                                                          'reporter',
                                                          'creator']:
                                        record[
                                            record_field] = issue_field.displayName
                                    elif search_field in ['summary', 'updated',
                                                          'resolutiondate',
                                                          'key']:
                                        record[record_field] = issue_field
                                    elif search_field in ['labels']:
                                        record[record_field] = ','.join(
                                            sorted(issue_field,
                                                   key=lambda x: (
                                                       x.split("_")[0].lower(),
                                                       x.split('_d')[
                                                           -1].isdigit() and int(
                                                           x.split('_d')[
                                                               -1]))))
                                    elif search_field in ['project']:
                                        record[record_field] = issue_field.key
                                    elif search_field in ['watches']:
                                        record[
                                            record_field] = issue_field.watchCount
                                    else:
                                        record[record_field] = getattr(
                                            issue.fields, search_field).name

                    except BaseException as e:
                        self.logger.error('JiraBugStatusCommand: %s', e)
                    yield record

            except JIRAError as e:
                self.logger.debug('JiraBugStatusCommand: %s',e)  # logs command line
                for record in records:
                    yield record


        else:
            for record in records:
                record[self.statusfield] = None
                record[self.descfield] = None
                yield record


dispatch(JiraBugStatusCommand, sys.argv, sys.stdin, sys.stdout, __name__)
