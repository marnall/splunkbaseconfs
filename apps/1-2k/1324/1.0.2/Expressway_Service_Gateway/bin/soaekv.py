# Copyright (C) 2005-2010 Splunk Inc.  All Rights Reserved.  Version 4.0
import sys,splunk.Intersplunk
import re
import urllib
import xml.sax.saxutils as sax


def parse_XML(tag,XML):
                
   namelist = [tag]
   depth = 0
   beginposition = 0
   invocationAgentSummaryCount = -1
   invocationAgentStartCount = -1

   f.write("Begin of parse_XML ---\n" + XML + "\n----");
   while beginposition < len(XML):
      # find the < character
      position = XML.find("<",beginposition)
      if position > len(XML) -4:
         # we are at some junk
         beginposition = len(XML)
      elif XML[position+1]  == '/' :
         # we are at a closing tag
         xpath = "/"
         if beginposition != position:
            r[xpath.join(namelist)] = XML[beginposition:position]
            f.write(xpath.join(namelist) + " = " + XML[beginposition:position] + "\n")
         # move marker past this closing element
         beginposition = XML.find(">",position) + 1
         if namelist:
            deleted = namelist.pop()
         else:
            f.write("name list is empty - " + XML[beginposition:len(XML)] )
         f.write(deleted + " deleted \n")

		
      elif position >= 0: 
      # we are in an opening tag or at end of xml with other stuff at end 
         step = 0
         while XML[position+step] != '>' and XML[position+step] != ' ' and position+step < len(XML):
            step = step + 1
         name = XML[position+1:position+step]

         if name == "invocationAgentSummary":
           invocationAgentSummaryCount = invocationAgentSummaryCount + 1
           name = "invocationAgentSummary[%d]" % invocationAgentSummaryCount
         if name == "invocationAgentStart":
           invocationAgentStartCount = invocationAgentStartCount + 1
           name = "invocationAgentStart[%d]" % invocationAgentStartCount
         # ignore element that closes itself
         if name[-1] != '/':
            f.write(name + " added \n")
            namelist.append(name)
         beginposition = position+step+1 
#         r[name] = XML[position:len(XML)]
      else:
         #or at end of xml with other stuff at end
         beginposition = len(XML)


   f.write("End of parse_XML\n");

try:
    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

	
    f = open('/tmp/workfile', 'w')
    
    for r in results:
        if "_raw" in r:
            raw = r["_raw"]
            rawOut = sax.unescape( raw )
            while( rawOut != raw ):
                raw = rawOut
                rawOut = sax.unescape( raw )                
            r["_raw"] = rawOut

            parse_XML("",rawOut)

    f.close()

except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

splunk.Intersplunk.outputResults( results )
