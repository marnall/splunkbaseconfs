#add your custom response handler class to this module
import json
import datetime
from datetime import datetime,timedelta


#the default handler , does nothing , just passes the raw output directly to STDOUT
class DefaultResponseHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        cookies = response_object.cookies
        if cookies:
            req_args["cookies"] = cookies        
        print_xml_stream(raw_response_output)


#template
class MyResponseHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):        
        print_xml_stream("foobar")

class ApplianceListXMLResponseHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        
        from xml.etree import ElementTree

        try:
            e = ElementTree.fromstring(raw_response_output)
            for entity in e.findall('./RESPONSE/APPLIANCE_LIST/APPLIANCE'):
                print_xml_stream(ElementTree.tostring(entity).decode()) 
        except:
            pass

class XMLResponseHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        
        from xml.etree import ElementTree
        e = ElementTree.fromstring(raw_response_output)
        for entity in e.findall('entity'):
            print_xml_stream(ElementTree.tostring(entity).decode())       
               

class RollOutCSVHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None): 
        import csv,io
        reader_list = csv.DictReader(io.StringIO(raw_response_output))
        for row in reader_list:    
            print_xml_stream(json.dumps(row))
        

'''various example handlers follow'''
        
class BoxEventHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if response_type == "json":        
            output = json.loads(raw_response_output)
            if not "params" in req_args:
                req_args["params"] = {}
            if "next_stream_position" in output:    
                req_args["params"]["stream_position"] = output["next_stream_position"]
            for entry in output["entries"]:
                print_xml_stream(json.dumps(entry))   
        else:
            print_xml_stream(raw_response_output)  

class QualysGuardActivityLog:
    '''Response handler for QualysGuard activity log.'''

    def __init__(self,**args):
        pass

    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if not "params" in req_args:
            req_args["params"] = {}
        date_from = (datetime.datetime.now() - datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        req_args["params"]["date_from"] = date_from
        print_xml_stream(raw_response_output) 

class SendGridHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if response_type == "json":
            output = json.loads(raw_response_output)
            latest_date =  datetime.strptime(req_args["params"]["start_date"], '%Y-%m-%d')
            for entry in output:
                print_xml_stream(json.dumps(entry))
                event_date = datetime.strptime(entry["date"], '%Y-%m-%d')
                if (event_date > latest_date):
                   latest_date = event_date 

            req_args["params"]["start_date"] = latest_date.strftime('%Y-%m-%d');

        else:
            print_xml_stream(raw_response_output)  

class ZipFileResponseHandler:

    def __init__(self,**args):
        self.csv_file_to_index = args['csv_file_to_index']

    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        import zipfile,io,re
        file = zipfile.ZipFile(BytesIO(response_object.content))
        for info in file.infolist():
            if re.match(self.csv_file_to_index, info.filename):
                filecontent = file.read(info)
                print_xml_stream(filecontent)
      

class FourSquareCheckinsEventHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if response_type == "json":        
            output = json.loads(raw_response_output)
            last_created_at = 0
            for checkin in output["response"]["checkins"]["items"]:
                print_xml_stream(json.dumps(checkin)) 
                if "createdAt" in checkin:
                    created_at = checkin["createdAt"]
                    if created_at > last_created_at:
                        last_created_at = created_at
            if not "params" in req_args:
                req_args["params"] = {}
            
            req_args["params"]["afterTimestamp"] = last_created_at
                      
        else:
            print_xml_stream(raw_response_output) 
            
class ThingWorxTagHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if response_type == "json":        
            output = json.loads(raw_response_output)
            for row in output["rows"]:
                print_xml_stream(json.dumps(row))                      
        else:
            print_xml_stream(raw_response_output) 
            
class FireEyeEventHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if response_type == "json":        
            output = json.loads(response_object.content)
            last_display_id = -1
            for alert in output["alerts"]:
                print_xml_stream(json.dumps(alert))  
                if "displayId" in alert:
                    display_id = alert["displayId"]
                    if display_id > last_display_id:
                        last_display_id = display_id
            if not "params" in req_args:
                req_args["params"] = {}
            
            if last_display_id > -1:
                req_args["params"]["offset"] = last_display_id

        else:
            print_xml_stream(raw_response_output) 
              
        

class CallIdentifierHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if response_type == "json":        
            output = json.loads(raw_response_output)
            
            for call in output["plcmCallList"]:
                del call["atomLinkList"]
                del call["destinationDetails"]
                del call["originatorDetails"]
                print_xml_stream(json.dumps(call))   
        else:
            print_xml_stream(raw_response_output)

class ExampleHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if response_type == "json":        
            output = json.loads(raw_response_output)
            
            for item in output["data"]:
                print_xml_stream(json.dumps(item))   
        else:
            print_xml_stream(raw_response_output)

class MyCustomHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        
        req_args["data"] = 'What does the fox say'   
         
        print_xml_stream(raw_response_output)
                               

class TwitterEventHandler:

    def __init__(self,**args):
        pass

    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):       
            
        if response_type == "json":        
            output = json.loads(raw_response_output)
            last_tweet_indexed_id = 0
            for twitter_event in output:
                print_xml_stream(json.dumps(twitter_event))
                if "id_str" in twitter_event:
                    tweet_id = twitter_event["id_str"]
                    if tweet_id > last_tweet_indexed_id:
                        last_tweet_indexed_id = tweet_id
            
            if not "params" in req_args:
                req_args["params"] = {}
            
            req_args["params"]["since_id"] = last_tweet_indexed_id
                       
        else:
            print_xml_stream(raw_response_output)
     

class PostDateHandler:

    def __init__(self,**args):
        pass

    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):       
        
        #PSEUDO CODE ONLY TO GUIDE YOU , ADJUST AS NECESSARY

        #index HTTP response 
        print_xml_stream(raw_response_output)

        #get POST data
        if not "data" in req_args:
            post_data = {}
        else:
            post_data = json.loads(req_args["data"])

        #set new date to something
        new_from_date = "2018-09-05 00:00:00"
        new_to_date = "2018-10-05 00:00:00"
        post_data["fromDate"] = new_from_date
        post_data["toDate"] = new_to_date

        #update POST data
        req_args["data"] = json.dumps(post_data)


                
class AutomaticEventHandler:

    def __init__(self,**args):
        pass

    #process the received JSON array     
    def process_automatic_response(data):
    
        output = json.loads(data)
        last_end_time = 0
                    
        for event in output:
            #each element of the array is written to Splunk as a seperate event
            print_xml_stream(json.dumps(event))
            if "end_time" in event:
                #get and set the latest end_time
                end_time = event["end_time"]
                if end_time > last_end_time:
                    last_end_time = end_time
        return last_end_time

    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):       
            
        if response_type == "json":
            last_end_time = 0
            
            #process the response from the orginal request
            end_time = process_automatic_response(raw_response_output)
            
            #set the latest end_time
            if end_time > last_end_time:
                last_end_time = end_time
             
            #follow any pagination links in the response    
            next_link = response_object.links["next"] 
                   
            while next_link:
                next_response = requests.get(next_link)       
                end_time = process_automatic_response(next_response.text)  
                #set the latest end_time 
                if end_time > last_end_time:
                    last_end_time = end_time  
                next_link = next_response.links["next"]
                        
            if not "params" in req_args:
                req_args["params"] = {}
            
            #set the start URL attribute for the next request
            #the Mod Input will persist this to inputs.conf for you
            req_args["params"]["start"] = last_end_time
                       
        else:
            print_xml_stream(raw_response_output)
            
class AirTableEventHandler2:
 
     def __init__(self,**args):
         pass
 
     def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
         if response_type == "json":
             output = json.loads(raw_response_output)
             
             #first response
             for record in output["records"]:
                 print_xml_stream(json.dumps(record))
            
             offset = output["offset"]   
             #pagination loop    
             while offset is not None:
                 
                 next_url = response_object.url+'?offset='+offset
                 next_response = requests.get(next_url)
                 output = json.loads(next_response.text)
                 #print out results from pagination looping
                 for record in output["records"]:
                     print_xml_stream(json.dumps(record))
                 #hopefully (guessing) at the end of the pagination , there will be
                 #no more "offset" values in the JSON response , so this will cause the while
                 #loop to exit   
                 if "offset" in output:
                     offset = output["offset"]
                 else:
                     offset = None 
                 
                 
 
         else:
             print_xml_stream(raw_response_output)


class CNMaestroResponseHandler:
 
     def __init__(self,**args):
         pass
 
     def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):

         import requests

         if response_type == "json":
             output = json.loads(raw_response_output)

             #get paging metadata out of the response JSON
             offset = output["paging"]["offset"]
             total = output["paging"]["total"]  
             number_records_retrieved = len(output["data"])
             #next offset 
             offset = offset + number_records_retrieved

             #update current request params
             if not "params" in req_args:
                req_args["params"] = {}
            
             #update the offset
             req_args["params"]["offset"] = offset
             
             #roll out data array items to Splunk as individual events
             for data in output["data"]:
                 print_xml_stream(json.dumps(data))
            
              
             #pagination loop  
             while offset < total:
                 
                 next_response = oauth2.get(endpoint,**req_args)

                 output = json.loads(next_response.text)
                 offset = output["paging"]["offset"]
                 number_records_retrieved = len(output["data"]) 
                 #next offset
                 offset = offset + number_records_retrieved
                 
                 #update the offset for next pagination loop
                 req_args["params"]["offset"] = offset

                 #print out results from pagination looping
                 for data in output["data"]:
                     print_xml_stream(json.dumps(data))
                 
                 #not sure what the logic is when the pagination is finished , does offset reset to zero  ?

             #rest the offset for next run
             req_args["params"]["offset"] = 0
                 
                 
 
         else:
             print_xml_stream(raw_response_output)

                        
            
class OpenstackTelemetryHandler:

    def __init__(self,**args):
        pass

    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):       
            
        if response_type == "json":        
            output = json.loads(raw_response_output)
            timestamp = 0
            for counter in output:
                print_xml_stream(json.dumps(counter))
                if "timestamp" in counter:
                    temp_timestamp = counter["timestamp"]
                    if temp_timestamp > timestamp:
                        timestamp = temp_timestamp
            
            if not "params" in req_args:
                req_args["params"] = {}
            
            req_args["params"]["q.value"] = timestamp
                       
        else:
            print_xml_stream(raw_response_output)

class SmartTabHandler:

    def __init__(self,**args):
        pass

    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if response_type == "json":
            output = json.loads(raw_response_output)

            #split out JSON array elements into individual events
            for entry in output:
                print_xml_stream(json.dumps(entry))
            
            if not "params" in req_args:
                req_args["params"] = {}
            
            #increment the date parameters by 1 day. These will get automagically persisted
            #back to inputs.conf for you
            req_args["params"]["dateStart"] = increment_one_day(req_args["params"]["dateStart"])
            req_args["params"]["dateEnd"] = increment_one_day(req_args["params"]["dateEnd"])
            
        else:
            print_xml_stream(raw_response_output)
            
    def _increment_one_day(self,date_str):

        date = datetime.strptime(date_str,'%Y-%m-%d')
        date += timedelta(days=1)
        return datetime.strftime(date,'%Y-%m-%d')

class HPEResponseHandler:

    def __init__(self,**args):
        #self.date_format = args['date_format']
        self.date_format = "%Y-%m-%dT%H:%M:%S.%f"
        pass

    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        from datetime import datetime
        
        if response_type == "json":
            output = json.loads(raw_response_output)
            new_watermark = None
            #split out each event and keep track of latest update time for new watermark value
            for event in output["event_list"]["event"]:
                time_changed =  datetime.strptime(event["time_changed"][:23], self.date_format)
                if new_watermark is None or time_changed > new_watermark:
                    new_watermark = time_changed
                print_xml_stream(json.dumps(event))
                
            if not "params" in req_args:
                req_args["params"] = {}
            
            #set watermark value for next request
            req_args["params"]["watermark"] = datetime.strftime(new_watermark,self.date_format)
            
        else:
            print_xml_stream(raw_response_output)
                       
class JSONArrayHandler:

    def __init__(self,**args):
        pass

    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if response_type == "json":
            output = json.loads(raw_response_output)

            for entry in output:
                print_xml_stream(json.dumps(entry))
        else:
            print_xml_stream(raw_response_output)
            
class MyJSONArrayHandler:

    def __init__(self,**args):
        self.somekey = args['somekey']
        pass

    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if response_type == "json":
            output = json.loads(raw_response_output)

            for entry in output['value']:
                entry['somekey'] = self.somekey
                print_xml_stream(json.dumps(entry))
        else:
            print_xml_stream(raw_response_output)

class MyCustomRecordHandler:

    def __init__(self,**args):
        pass

    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if response_type == "json":
            output = json.loads(raw_response_output)

            for record in output['result']['records']:
                print_xml_stream(json.dumps(record))
        else:
            print_xml_stream(raw_response_output)
            


class GithubHandler:
 
     def __init__(self,**args):
         pass
 
     def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):

         import requests

         if response_type == "json":
             output = json.loads(raw_response_output)
             
             #iterate over each item from first response JSON
             for record in output:
                 #fire off request for each URL in first response
                 next_response = requests.get(record["url"]) 
                 next_output = json.loads(next_response.text)
                 #index response
                 print_xml_stream(json.dumps(next_output))
 
         else:
             print_xml_stream(raw_response_output)

class JoesResponseHandler:

    def __init__(self,**args):
        pass

    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if response_type == "json":
            output = json.loads(raw_response_output)
            last_id = 0
            for entry in output['entries']:
                print_xml_stream(json.dumps(entry))
                if "EntryId" in entry:
                    this_id = entry["EntryId"]
                    if this_id > last_id:
                        last_id = this_id
            
            if not "params" in req_args:
                req_args["params"] = {}
            
            req_args["params"]["pageStart"] = last_id
        else:
            print_xml_stream(raw_response_output)
            
class YourJSONArrayHandler:

    def __init__(self,**args):
        pass

    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if response_type == "json":
            raw_json = json.loads(raw_response_output)
            column_list = []
            for column in raw_json['columns']:
                column_list.append(column['name'])
            for row in raw_json['rows']:
                i = 0;
                new_event = {}
                for row_item in row:          
                    new_event[column_list[i]] = row_item
                    i = i+1
                print(print_xml_stream(json.dumps(new_event)))

        else:
            print_xml_stream(raw_response_output)       
                                      
            
    
class FlightInfoEventHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if response_type == "json":        
            output = json.loads(raw_response_output)
            for flight in output["FlightInfoResult"]["flights"]:
                print_xml_stream(json.dumps(flight)) 
                
                      
        else:
            print_xml_stream(raw_response_output) 
            
class AlarmHandler:
    
    def __init__(self,**args):
        pass
        
    def __call__(self, response_object,raw_response_output,response_type,req_args,endpoint,oauth2=None):
        if response_type == "xml": 
            import xml.etree.ElementTree as ET
            alarm_list = ET.fromstring(encodeXMLText(raw_response_output))
            for alarm in alarm_list:
                alarm_xml_str = ET.tostring(alarm, encoding='utf8', method='xml')
                print_xml_stream(alarm_xml_str)               
                      
        else:
            print_xml_stream(raw_response_output) 
                                                                                         
#HELPER FUNCTIONS
    
# prints XML stream
def print_xml_stream(s):
    print("<stream><event unbroken=\"1\"><data>%s</data><done/></event></stream>" % encodeXMLText(s))



def encodeXMLText(text):
    text = text.replace("&", "&amp;")
    text = text.replace("\"", "&quot;")
    text = text.replace("'", "&apos;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = text.replace("\n", "")
    return text