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

from __future__ import absolute_import, division, print_function, unicode_literals

import sys
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
def add_to_sys_path(paths, prepend=False):
    for path in paths:
        if prepend:
            if path in sys.path:
                sys.path.remove(path)
            sys.path.insert(0, path)
        elif not path in sys.path:
            sys.path.append(path)

def add_python_version_specific_paths():
    '''
        Adds extra paths for libraries specific to Python2 or Python3,
        determined at a runtime
    '''
    # We should not rely on core enterprise packages:
    if sys.version_info >= (3, 0):
        add_to_sys_path([make_splunkhome_path(['etc', 'apps', 'SA-devforall', 'lib', 'py3'])], prepend=True)
    else:
        add_to_sys_path([make_splunkhome_path(['etc', 'apps', 'SA-devforall', 'lib', 'py2'])], prepend=True)
    # Common libraries like future
    add_to_sys_path([make_splunkhome_path(['etc', 'apps', 'SA-devforall', 'lib', 'py23'])], prepend=True)
    from six.moves import reload_module
    try:
        if 'future' in sys.modules:
            import future
            reload_module(future)
    except Exception:
        '''noop: future was not loaded yet'''
add_to_sys_path([make_splunkhome_path(['etc', 'apps', 'SA-devforall', 'lib', 'py23', 'splunklib'])], prepend=True)
add_python_version_specific_paths()


from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import sys
import json
import csv
import codecs
from itertools import tee


def RaiseError(errormsg, metadata={ "finished": "finished"}):
	test=[]
	test.append({"ERROR": errormsg})
	return (
          {'finished': metadata['finished']}, test
          
      )

@Configuration()
class DoublingCommand(StreamingCommand):
    """ Counts the number of non-overlapping matches to a regular expression in a set of fields.

    ##Syntax

    .. code-block::
        countmatches fieldname=<field> pattern=<regular_expression> <field-list>

    ##Description

    A count of the number of non-overlapping matches to the regular expression specified by `pattern` is computed for
    each record processed. The result is stored in the field specified by `fieldname`. If `fieldname` exists, its value
    is replaced. If `fieldname` does not exist, it is created. Event records are otherwise passed through to the next
    pipeline processor unmodified.

    ##Example

    Count the number of words in the `text` of each tweet in tweets.csv and store the result in `word_count`.

    .. code-block::
        | inputlookup tweets | countmatches fieldname=word_count pattern="\\w+" text

    """

  #      setattr(self, "resetbaseline", False)
#    setattr(self, "debug", False)
#    setattr(self, "extradebug", False)
#    setattr(self, "incrementbaseline", False)
#    setattr(self, "analyze", False)
#    setattr(self, "savebaseline", False)
#    setattr(self, "baseline", False)
#    setattr(self, "casesensitive", False)
#    setattr(self, "field", False)
    field = Option(
        doc='''
        **Syntax:** **field=***<field>*
        **Description:** Name of the field that will hold the match count''',
        require=True, validate=validators.Fieldname())

    def stream(self, records):
        self.logger.debug('DoublingCommand: %s', self)  # logs command line
        for record in records:
            try:
                record['doubled'] = int(record[self.field]) * 2 
            except ValueError:
                record['doubled'] = "" 
            yield record
        

dispatch(DoublingCommand, sys.argv, sys.stdin, sys.stdout, __name__)
