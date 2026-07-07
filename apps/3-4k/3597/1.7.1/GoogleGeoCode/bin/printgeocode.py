import splunk.Intersplunk
import requests
import splunk
import os, sys
import logging, logging.handlers
import splunk.entity as entity

def setup_logger(level):
   logger = logging.getLogger('GoogleGeoCode')
   logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
   logger.setLevel(level)

   file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/googlegeocode.log', maxBytes=25000000, backupCount=5)
   formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
   file_handler.setFormatter(formatter)
   
   logger.addHandler(file_handler)
    
   return logger


def getCredentials():
   myapp = 'GoogleGeoCode'
   entities = entity.getEntities(['admin','passwords'], namespace=myapp, owner='nobody',sessionKey=sessionKey)
   # return first set of credentials
   for i,c in entities.items():
      username=c['username']
      password=c['clear_password']
      return password
   
def geocode(string):
   logger.info("In Geocode function, address to convert is: '%s'",string)
   address=string
  # API_KEY From Google, to be added in appsetup.conf file
   api_key_val=getCredentials()
   #logger.info("API KEY: '%s'", api_key_val)
   lat=None
   lon=None
   url='https://maps.googleapis.com/maps/api/geocode/json'
   params={'sensor':'false','address':address,'key':api_key_val}
   r=requests.get(url,params=params)
   status=r.json()['status']
   if status == 'OK':
      logger.info("Status from Google GeoCoding API is OK")
      d=dict(r.json())
      loc=d['results'][0]['geometry']['location']
      lat,lon=loc['lat'],loc['lng']
      logger.info("Successful conversion of address->lat,lon. Returned: (%f,%f)",lat,lon)
   else:
      logger.info("Something is not write, please see status: %s",status)
      logger.info("Returning lat,lon as blank")
      lat=None
      lon=None
   return status,lat,lon

def reverse_geocode(lat,lon):
   api_key_val=getCredentials()
   #logger.info("API KEY: '%s'", api_key_val)
   # Reverse Geocoding
   base='https://maps.googleapis.com/maps/api/geocode/json?'
   params="latlng={lat},{lon}&sensor={sen}&key={key}".format(
   lat=lat,
   lon=lon,
   sen='false',
   key=api_key_val
   )
   logger.info("In Reverse Geocode function, (lat,lon) to convert is: '%f,%f'",lat,lon)
   url="{base}{params}".format(base=base,params=params)
   r=requests.get(url)
   #logger.info(r.json())
   status=r.json()['status']
   if status == 'OK':
      logger.info("Status from Google Reverse GeoCoding API is OK")
      d=dict(r.json())
      address=d['results'][0]['formatted_address']
      logger.info("Successful conversion of (lat,lon)-> Address. Returned: (%s)",address)
   else:
      logger.info("Something is not write, please see status: %s",status)
      logger.info("Returning address as blank")
      address=None
   return status,address  

 # A basic shell for any custom streaming command. Just pass the events to it
def customcommand(results, settings):
   
   try:
      fields, argvals = splunk.Intersplunk.getKeywordsAndOptions()
      Type = argvals.get('type',None)
      address = argvals.get('address',None)
      lat = argvals.get('latfield',None)
      lon = argvals.get('lonfield',None)
    
    # Missing arguments validation
      if Type == None:
         splunk.Intersplunk.generateErrorResults("'type' argument required, such as type=geocode or type=reverse")
         exit(0)
      if Type == "geocode":
         if(address == None):
            splunk.Intersplunk.generateErrorResults("String 'address' argument required")
            exit(0)
         if Type == "reverse":
            if lat == None or lon == None:
               splunk.Intersplunk.generateErrorResults("Latitude and Longitude 'latfield,lonfield' arguments required")
               exit(0)
       # If the parameter provided exists as a field in the event, run the Geocode math on its value
   
    # Based on the type field, decide whether it's address to lat,long or reverse.
      for result in results:
         if Type == "geocode":
            newfield1 = "geolocation_lat"
            newfield2 = "geolocation_lon"
            status_field = "geolocation_status"
            
            address_value = result[address]
            status,lat,lng = geocode(address_value)
            if status == 'OK':
               result[status_field]=status
               result[newfield1]=lat
               result[newfield2]=lng
            
            else:
               result[status_field]=status
               result[newfield1]="NA"
               result[newfield2]="NA"
         if Type == "reverse":
            newfield = "geolocation_addr"
            lat_value = result[lat]
            lon_value = result[lon]
            status_field = "geolocation_status"
            status,address=reverse_geocode(lat_value,lon_value)
            if status == 'OK':
               result[newfield] = address
               result[status_field]=status
            else:
               result[newfield] = None
               result[status_field]=status
           
    # Let the modified events flow back into the search results
      splunk.Intersplunk.outputResults(results)
   except:
      import traceback
      stack =  traceback.format_exc()
 
 # Get the events from splunk
logger = setup_logger(logging.INFO)
results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
 # Send the events to be worked on
sessionKey = settings.get("sessionKey")
results = customcommand(results, settings)
