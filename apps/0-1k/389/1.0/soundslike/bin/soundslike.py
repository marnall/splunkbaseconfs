"""
SOUNDSLIKE for Splunk by Marinus van Aswegen (mvanaswegen AT gmail.com) v0.1 
 
adds a new command to the search language that allows you to filter events according to
how similar a field (or a token) in the event sounds to a keyword.

imagine you has a log with the names of administrators, you cannot remember the name of
the person you are looking for but it sounds like darren or dannen. you can now filter a 
search based on something sounding like darren.

* | soundslike word=darren field=user_name 
* | soundslike word=darren               (defaults, to _raw, will breakup the event into tokens)
* | soundslike word=darren range=2       (less restrictive matching, give me more)

the matching routing is based soundex and is similar to 'like' in SQL

Usage
	soundslike word=xyz [field=_raw] [range=1]
  
  
Copyright 2010 Marinus van Aswegen. All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice, this list of
      conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright notice, this list
      of conditions and the following disclaimer in the documentation and/or other materials
      provided with the distribution.

THIS SOFTWARE IS PROVIDED BY MARINUS VAN ASWEGEN ``AS IS'' AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL MARINUS VAN ASWEGEN OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those of the
authors and should not be interpreted as representing official policies, either expressed
or implied, of Marinus van Aswegen.

"""

import splunk.Intersplunk
import sys
import math
import os
from itertools import groupby

def soundex(word): 
	""" from http://rosettacode.org/wiki/Soundex#Python """
	
	codes = ("bfpv","cgjkqsxz", "dt", "l", "mn", "r") 
	soundDict = dict((ch, str(ix+1)) for ix,cod in enumerate(codes) for ch in cod) 
	cmap2 = lambda kar: soundDict.get(kar, '9') 
	sdx =  ''.join(cmap2(kar) for kar in word.lower()) 
	sdx2 = word[0].upper() + ''.join(k for k,g in list(groupby(sdx))[1:] if k!='9') 
	sdx3 = sdx2[0:4].ljust(4,'0') 
	
	return sdx3

def match(field, word, range):
	
	word = soundex(word)
	word_c = word[0]
	word_val = int(word[1:])
	
	for token in field.split():
		token_sd = soundex(token)
		token_c = token_sd[0]
		token_val = int(token_sd[1:])
		
		if token_c == word_c:
			delta = abs(token_val-word_val)
			if delta <= range:
				return delta
	
	return -1
	
try:   
	keywords,options = splunk.Intersplunk.getKeywordsAndOptions()
		
	if not options.has_key('word'):
		splunk.Intersplunk.generateErrorResults("word not specified")
		exit(0)

	word = options.get('word', None)
	field = options.get('field', '_raw')
	range = int(options.get('range', '1'))
	
	results,unused1,unused2 = splunk.Intersplunk.getOrganizedResults()
	
	new_results = []
	
	for result in results:
			r = match(result[field],word, range)
			if r >= 0:
				new_results.append(result)

	splunk.Intersplunk.outputResults(new_results)
	
except Exception, e:
	results = splunk.Intersplunk.generateErrorResults(str(e))

