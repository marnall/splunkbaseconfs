'''
Custom streaming search command for looking up IP Ranges in KVStore collections

May 2021

Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Neustar
'''

from __future__ import absolute_import, division, print_function, unicode_literals
import ipaddress,os,sys

SPLUNK_HOME = os.environ['SPLUNK_HOME']

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunklib import six
from distutils.util import strtobool
import logging
from logging.handlers import TimedRotatingFileHandler
import traceback

#collections
KVSTORE_V4_COLLECTION = "geopoint_csv_ipv4" 
KVSTORE_V6_COLLECTION  = "geopoint_csv_ipv6"


#if allfields=true , all KV Store fields wll be output
#else , just these default fields will be output
DEFAULT_OUTPUT_FIELDS = ["latitude","longitude","city","continent","country","region","state"]

#don't output these KV Store fields
EXCLUDE_FIELDS = ["_key","_user"]

#all possible output fields
ALL_FIELDS = ["anonymizer","anonymizer_status","area_code","asn","carrier","city","city_cf","city_ref_id","connection_type","continent","country","country_cf","country_code","dma","end_ip_2long_1","end_ip_2long_2","end_ip_3long_1","end_ip_3long_2","end_ip_3long_3","end_ip_full","end_ip_int","end_ip_oct","end_ip_raw","end_ip_shortened","geonames_id","home","hosting_facility","ip_routing_type","isic_code","latitude","line_speed","longitude","msa","naics_code","organization","organization_type","postal_code","postal_code_cf","proxy_last_detected","proxy_last_detected = string","proxy_level","proxy_type","reg_area_code","reg_city","reg_continent","reg_country","reg_country_code","reg_dma","reg_latitude","reg_longitude","reg_msa","reg_postal_code","reg_region","reg_state","reg_time_zone","region","region_ref_id","sld","start_ip_2long_1","start_ip_2long_2","start_ip_3long_1","start_ip_3long_2","start_ip_3long_3","start_ip_full","start_ip_int","start_ip_oct","start_ip_raw","start_ip_shortened","state","state_cf","state_code","state_ref_id","time_zone","tld"];

#set up logging to this location
LOG_FILENAME = os.path.join(SPLUNK_HOME,"var","log","splunk","neustar_search_command.log")

# Set up a specific logger
logger = logging.getLogger("neustar_search_command")
logger.propagate = False

#default logging level , can be overidden in stanza config
logger.setLevel(logging.INFO)

#log format
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

# Add the daily rolling log message handler to the logger
handler = TimedRotatingFileHandler(LOG_FILENAME, when="d",interval=1,backupCount=5)
handler.setFormatter(formatter)
logger.addHandler(handler)


@Configuration()
class UltraGeoPointCommand(StreamingCommand):
    
    prefix = Option(
        doc='''
        **Syntax:** **prefix=***<string>*
        **Description:** Specify a string to prefix the field name''',
        require=False, validate=validators.Fieldname())
    
    allfields = Option(
        doc='''
        **Syntax:** **allfields=***<bool>*
        **Description:** Specifies whether to add all of the fields from the lookup to the events''',
        require=False, validate=validators.Fieldname())


    def string_to_bool(self,string):

        if self.allfields:
            return bool(strtobool(str(string)))
        else:
            return False;

    def get_output_fieldname(self,fieldname):

        if self.prefix:
            return self.prefix+"_"+fieldname
        else:
            return fieldname

    def set_empty_record(self,record,output_all_fields):

        if output_all_fields:
            for key in ALL_FIELDS:
                record[self.get_output_fieldname(str(key))] = ""
        else:
            for key in DEFAULT_OUTPUT_FIELDS:
                record[self.get_output_fieldname(str(key))] = ""

        return record


    def stream(self, records):
        
        ip_address_field = None
        output_all_fields = self.string_to_bool(self.allfields)

        v4_collection_obj = None
        v6_collection_obj = None
        


        if self.fieldnames and len(self.fieldnames[0]) > 0:
            ip_address_field = self.fieldnames[0]

        try:
            v4_collection_obj = self.service.kvstore[KVSTORE_V4_COLLECTION]
            v6_collection_obj = self.service.kvstore[KVSTORE_V6_COLLECTION]
        except:
            logger.error("Error getting KVStore Object %s " % traceback.format_exc())

        for record in records:

            record = self.set_empty_record(record,output_all_fields)
            ip_address_field_value = ""        
            ip_address = None

            if ip_address_field and (ip_address_field in record) and (v4_collection_obj or v6_collection_obj):

                try:
                    ip_address_field_value = record[ip_address_field]

                    try:
                        ip_address = ipaddress.ip_address(ip_address_field_value)
                    except:
                        logger.error("IP Address %s could not be parsed" % ip_address_field_value)
                   

                    if ip_address:
                     
                        skip_processing = False
                        #various checks for valid IP Addresses that  won't have a lookup entry
                        if not ip_address.is_global:
                            skip_processing = True
                            logger.warn("IP Address %s not allocated for public networks and won't be looked up" % ip_address_field_value)
                        elif ip_address.is_private:
                            skip_processing = True
                            logger.warn("IP Address %s is private and won't be looked up" % ip_address_field_value)
                        elif ip_address.is_loopback:
                            skip_processing = True
                            logger.warn("IP Address %s is a loopback address and won't be looked up" % ip_address_field_value)
                        elif ip_address.is_unspecified:
                            skip_processing = True
                            logger.warn("IP Address %s is unspecified and won't be looked up" % ip_address_field_value)
                        elif ip_address.is_multicast:
                            skip_processing = True
                            logger.warn("IP Address %s is a multicast address and won't be looked up" % ip_address_field_value)
                        elif ip_address.is_link_local:
                            skip_processing = True
                            logger.warn("IP Address %s is a link local address and won't be looked up" % ip_address_field_value)
                        elif ip_address.is_reserved:
                            skip_processing = True
                            logger.warn("IP Address %s is reserved and won't be looked up" % ip_address_field_value)
                        else:
                            skip_processing = False

                        if not skip_processing:

                            ip_address_int = int(ip_address)
                        

                            if ip_address.version == 4:

            
                                v4_ip_range_query = '{ "$and": [ { "end_ip_int": { "$gte": %(ip_address_int)i } }, { "start_ip_int": { "$lte": %(ip_address_int)i } } ] }' % {"ip_address_int":ip_address_int}
                                
                                query_result =v4_collection_obj.data.query(query=v4_ip_range_query,limit=1)
                                if len(query_result) == 0:
                                    logger.warn("IP Address %s could not be found in any range in the KVStore" % ip_address_field_value)

                                for qr in query_result:

                                    for key,value in qr.items():
                                        if key not in EXCLUDE_FIELDS:
                                            if output_all_fields:
                                                record[self.get_output_fieldname(str(key))] = str(value)
                                            elif key in DEFAULT_OUTPUT_FIELDS:
                                                record[self.get_output_fieldname(str(key))] = str(value)

                                    break #just get 1st item

                            if ip_address.version == 6:

                                ip_address_int_1 = (ip_address_int >> 72) & 0xffffffffffffff
                                ip_address_int_2 = (ip_address_int >> 16) & 0xffffffffffffff
                                ip_address_int_3 = ip_address_int  & 0xffff

                                v6_ip_range_query = '{ "$and": [ { "end_ip_3long_1": { "$gte": %(ip_address_int_1)i } },{ "end_ip_3long_2": { "$gte": %(ip_address_int_2)i } },{ "end_ip_3long_3": { "$gte": %(ip_address_int_3)i } },{ "start_ip_3long_1": { "$lte": %(ip_address_int_1)i } },{ "start_ip_3long_2": { "$lte": %(ip_address_int_2)i } },{ "start_ip_3long_3": { "$lte": %(ip_address_int_3)i } } ] }' % {"ip_address_int_1":ip_address_int_1,"ip_address_int_2":ip_address_int_2,"ip_address_int_3":ip_address_int_3}
                 
                              
                                query_result =v6_collection_obj.data.query(query=v6_ip_range_query,limit=1)
                                if len(query_result) == 0:
                                    logger.error("IP Address %s could not be found in any range in the KVStore" % ip_address_field_value)

                                for qr in query_result:

                                    for key,value in qr.items():
                                        if key not in EXCLUDE_FIELDS:
                                            if output_all_fields:
                                                record[self.get_output_fieldname(str(key))] = str(value)
                                            elif key in DEFAULT_OUTPUT_FIELDS:
                                                record[self.get_output_fieldname(str(key))] = str(value)

                                    break #just get 1st item

    
                except:
                    logger.error("Error looking up IP Address %s " % traceback.format_exc())

            yield record

dispatch(UltraGeoPointCommand, sys.argv, sys.stdin, sys.stdout, __name__)