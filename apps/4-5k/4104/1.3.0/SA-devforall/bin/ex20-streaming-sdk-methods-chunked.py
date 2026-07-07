#!/usr/bin/env python
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

import datetime, time
import json
import csv
import codecs, sys
from cexc import BaseChunkHandler


def RaiseError(errormsg, metadata={ "finished": "finished"}):
  test=[{"ERROR": errormsg}]
  return (
          {'finished': metadata['finished']}, test
          
      )
class DoubleData(BaseChunkHandler):

    def _parse_arguments(self, args):
        
      setattr(self, "field", False)
      self.numTokens = 0
      for token in args:
        if not '=' in token:
          self.field = token
          self.numTokens += 1
          
          # single word: possible but not used/supported by urlparser
          continue
    
        (k,v) = token.split('=', 1)
        # urlparser only consider those 3 arguments.
        if k in ["not-used-in-this-command-but-kept-around-for-your-convenience---add-parameters-you-want-here"]:
          setattr(self, k, v)

      if self.field == False:
        raise Exception("No field found -- please specify the field you want to analyze") 
      
    # metadata is a dict with the parsed JSON metadata payload.
    # data is a list of dicts, where each dict represents a search result.
    def handler(self, metadata, data):

        # The first chunk is a "getinfo" chunk.
        if metadata['action'] == 'getinfo':
          try:
            args = metadata['searchinfo']['args']
          except:
            args = []

          self._parse_arguments(args)
          
          return {'type': 'streaming', 'required_fields':[ self.field ]}


	if self.field == False:
		raise Exception("No field found -- please specify the field you want to analyze") 
	if self.numTokens > 1:
		raise Exception("More than one field found -- we only analyze one field at a time") 



# Now let's actually analyze our data
	for record in data:
		try:
			record.update({"doubled": int(record[self.field]) * 2 })
		except ValueError:
			record.update({"doubled": ""})

	return (
							{'finished': metadata['finished']},
							data
					)


if __name__ == "__main__":
    DoubleData().run()