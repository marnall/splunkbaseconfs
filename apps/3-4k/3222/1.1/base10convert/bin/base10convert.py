import math
import csv
import sys
import re
import time
import splunk.Intersplunk
 
def digit_to_char(digit):

    if digit < 10: 
        return chr(ord('0') + digit)
    else: 
        # 10 in hexadecimal would be A
        # 11 in hexadecimal would B - i.e ord('a') + 11-10
        return chr(ord('a') + digit - 10).upper()


def str_base(number,base):
    
    # divmod returns a tuple = (quotient, remainder)  # very handy!
    (d,m) = divmod(number,base)
    if d:
        return str_base(d,base) + digit_to_char(m)
    else:
        # base case (only remainder is left)
        return digit_to_char(m)

  # A basic shell for any custom streaming command. Just pass the events to it
def customcommand(splunk_field, base, results, settings):
   try:
 
     # Set a default return value
     splunk_field_value = "Field does not exist"
     base_value = int(base)
 
     # If the parameter provided exists as a field in the event, run the entropy math on its value
     for result in results:
       # If field exists in event
       if splunk_field in result:
         # Get the field's actual value
         splunk_field_value = int(result[splunk_field])
         # Create the new field we'll place into the events
       newfield = splunk_field + "_base_" + base
         # Finally, run the math on the field's value and place it into the newfield we just created
       result[newfield] = str_base(splunk_field_value,base_value)
 
     # Let the modified events flow back into the search results
     splunk.Intersplunk.outputResults(results)
 
   except:
     import traceback
     stack =  traceback.format_exc()
 
 
 
 #####Start######
 
 # Get the events from splunk
results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
 # Send the events to be worked on
results = customcommand(sys.argv[1], sys.argv[2], results, settings)
