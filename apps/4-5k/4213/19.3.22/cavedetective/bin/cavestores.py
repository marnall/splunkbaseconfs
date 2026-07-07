#==============================================================================#
# Continuous Automation and Visibility Engine                    Set Solutions #
# Collection Utility                               Engineering and Development #
#==============================================================================#


#------------------------------------------------------------------------------#
# Include Libraries and Configuration                                          #
#------------------------------------------------------------------------------#
#
#-- Library Imports and Global Variables -------------------------------------
import sys,time,re
from cavecommon import conf,spkv
from splunklib.searchcommands import dispatch,ReportingCommand,Configuration,Option,validators
#-----------------------------------------------------------------------------
#
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
# Supporting Functions                                                         #
#------------------------------------------------------------------------------#
#
#-- Collection Information ---------------------------------------------------
def spkvlist(self,records):
    necords = list()
    kvstats = dict()
    #
    # Iterate through the records enriching them with collection information
    for record in records:
        sepoch = round(time.time(),2)
        necord = dict(record.items()+({"output":[],"kvstores":[]}).items())
        #
        # Validate that the required options are present and make sense
        if self.appname is None or self.appname not in record: necord["output"].append("ERROR: Field for appname is either undefined or missing")
        if len(necord["output"]) >= 1 and re.match(r"ERROR\:\s",str().join(necord["output"])):
            necords.append(dict(necord.items()+({"runtime":"{:.2f}".format(round(abs(time.time()-sepoch),2))}).items()))
            continue
        #
        # Gather the relevant collection information and populate records
        if str(record[self.appname]) not in kvstats: kvstats.update({str(record[self.appname]):spkv(self,conf(self),str(record[self.appname]),"stats",None,None)})
        if kvstats[str(record[self.appname])]["failed"]:
            necord["output"].append("ERROR: "+kvstats[str(record[self.appname])]["reason"])
            necords.append(dict(necord.items()+({"runtime":"{:.2f}".format(round(abs(time.time()-sepoch),2))}).items()))
            continue
        try: necord.update({"kvstores":kvstats[str(record[self.appname])]["data"].keys()})
        except: necord["output"].append("ERROR: There were no collections found for the application")
        else: necord["output"].append("DEBUG: Successfully enumerated all relevant collections")
        #
        # Add the newly generated record to the list to be returned
        necords.append(dict(necord.items()+({"runtime":"{:.2f}".format(round(abs(time.time()-sepoch),2))}).items()))
    #
    # Return the newly populated list of records enriched with statistics
    return necords
#-----------------------------------------------------------------------------
#
#-- Collection Statistics ----------------------------------------------------
def spkvstat(self,records):
    necords = list()
    kvstats = dict()
    #
    # Iterate through the records enriching them with collection statistics
    for record in records:
        sepoch = round(time.time(),2)
        necord = dict(record.items()+({"output":[]}).items())
        #
        # Validate that the required options are present and make sense
        if self.appname is None or self.appname not in record: necord["output"].append("ERROR: Field for appname is either undefined or missing")
        if self.kvstore is None or self.kvstore not in record: necord["output"].append("ERROR: Field for kvstore is either undefined or missing")
        if len(necord["output"]) >= 1 and re.match(r"ERROR\:\s",str().join(necord["output"])):
            necords.append(dict(necord.items()+({"runtime":"{:.2f}".format(round(abs(time.time()-sepoch),2))}).items()))
            continue
        #
        # Gather the relevant collection statistics and populate records
        if str(record[self.appname]) not in kvstats: kvstats.update({str(record[self.appname]):spkv(self,conf(self),str(record[self.appname]),"stats",None,None)})
        if kvstats[str(record[self.appname])]["failed"]:
            necord["output"].append("ERROR: "+kvstats[str(record[self.appname])]["reason"])
            necords.append(dict(necord.items()+({"runtime":"{:.2f}".format(round(abs(time.time()-sepoch),2))}).items()))
            continue
        try: necord = dict(necord.items()+(kvstats[str(record[self.appname])]["data"][str(record[self.kvstore])]).items())
        except: necord["output"].append("ERROR: There were no statistics found for the collection")
        else: necord["output"].append("DEBUG: Successfully enriched the record with collection statistics")
        #
        # Add the newly generated record to the list to be returned
        necords.append(dict(necord.items()+({"runtime":"{:.2f}".format(round(abs(time.time()-sepoch),2))}).items()))
    #
    # Return the newly populated list of records enriched with statistics
    return necords
#-----------------------------------------------------------------------------
#
#-- Collection Retentions ----------------------------------------------------
def spkvtrim(self,records):
    necords = list()
    kvstats = dict()
    #
    # Iterate through the records enriching them with rentention output
    for record in records:
        sepoch = round(time.time(),2)
        necord = dict(record.items()+({"output":[]}).items())
        #
        # Validate that the required options are present and make sense
        if self.appname is None or self.appname not in record: necord["output"].append("ERROR: Field for appname is either undefined or missing")
        if self.kvstore is None or self.kvstore not in record: necord["output"].append("ERROR: Field for kvstore is either undefined or missing")
        if self.retention_policy is None or self.retention_policy not in record or len(str(record[self.retention_policy]).split("/")) != 2: necord["output"].append("ERROR: Field for retention_policy is either undefined, missing, or invalid")
        if self.retention_field is None or self.retention_field not in record: necord["output"].append("ERROR: Field for retention_field is either undefined, missing, or invalid")
        if self.extra_field is not None and self.extra_field not in record: necord["output"].append("ERROR: Field for extra_field is missing")
        if self.extra_value is not None and self.extra_value not in record: necord["output"].append("ERROR: Field for extra_value is missing")
        if len(necord["output"]) >= 1 and re.match(r"ERROR\:\s",str().join(necord["output"])):
            necords.append(dict(necord.items()+({"runtime":"{:.2f}".format(round(abs(time.time()-sepoch),2))}).items()))
            continue
        else: kvstats[record[self.kvstore]] = {"before","after"}
        #
        # Determine what to use for maximum age of the specified time field
        try: necord.update({"retention_maxage":conf(self)[str(record[self.retention_policy]).split("/")[0]][str(record[self.retention_policy]).split("/")[1]]})
        except: necord["output"].append("ERROR: There was no matching retention configuration found")
        else: necord["output"].append("DEBUG: Matching retention configuration was found")
        if len(necord["output"]) >= 1 and re.match(r"ERROR\:\s",str().join(necord["output"])):
            necords.append(dict(necord.items()+({"runtime":"{:.2f}".format(round(abs(time.time()-sepoch),2))}).items()))
            continue
        #
        # Gather the collection statistics for later comparison output
        try: spkvstat = spkv(self,conf(self),str(record[self.appname]),"stats",None,None)["data"][str(record[self.kvstore])]["count"]
        except: necord["output"].append("WARNING: Unable to obtain statistics prior to executing retention query")
        else:
            necord["output"].append("DEBUG: Successfully obtained statistics prior to executing retention query")
            necord.update({"count_before":spkvstat})
        #
        # Execute relevant query to remove expired entries based on maxage
        kvquery = {"query":{necord["retention_field"]:{"$lte":int(time.time()-int(necord["retention_maxage"]))}}}
        if self.extra_field is not None and self.extra_field in record and self.extra_value is not None and self.extra_value in record: kvquery = {"query":{"$and":[{necord["extra_field"]:necord["extra_value"]},kvquery["query"]]}}
        kvdelete = spkv(self,conf(self),str(record[self.appname]),"delete",str(record[self.kvstore]),kvquery)
        if kvdelete["failed"]: necord["output"].extend(["ERROR: Failed to execute the retention query to prune expired entries","ERROR: "+kvdelete["reason"]])
        else: necord["output"].append("INFO: Successfully executed the retention query to prune expired entries")
        #
        # Gather the collection statistics for later comparison output
        try: spkvstat = spkv(self,conf(self),str(record[self.appname]),"stats",None,None)["data"][str(record[self.kvstore])]["count"]
        except: necord["output"].append("WARNING: Unable to obtain statistics after executing retention query")
        else:
            necord["output"].append("DEBUG: Successfully obtained statistics after executing retention query")
            necord.update({"count_after":spkvstat})
        #
        # Add the newly generated record to the list to be returned
        necords.append(dict(necord.items()+({"runtime":"{:.2f}".format(round(abs(time.time()-sepoch),2))}).items()))
    #
    # Return the newly populated list of records enriched with statistics
    return necords
#-----------------------------------------------------------------------------
#
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
# Collection Utilities                                                         #
#------------------------------------------------------------------------------#
#
#-- Iterate Records ----------------------------------------------------------
@Configuration()
class CavestoresCommand(ReportingCommand):
    #
    # Basic options that can be used with this Splunk SPL command
    method = Option(require=True, validate=validators.Fieldname())
    appname = Option(require=False,validate=validators.Fieldname())
    kvstore = Option(require=False,validate=validators.Fieldname())
    retention_policy = Option(require=False,validate=validators.Fieldname())
    retention_field = Option(require=False,validate=validators.Fieldname())
    extra_field = Option(require=False,validate=validators.Fieldname())
    extra_value = Option(require=False,validate=validators.Fieldname())
    @Configuration()
    #
    # Perform the map and reduce functions when called to do so by Splunk
    def map(self,records): return records
    def reduce(self,records):
        #
        # Handle the various methods based on specified input options
        if self.method == "list": records = spkvlist(self,records)
        elif self.method == "stats": records = spkvstat(self,records)
        elif self.method == "prune": records = spkvtrim(self,records)
        else: raise Exception("Invalid method specified")
        #
        # Return the newly populated list of records enriched with additional data
        return records
#
# Dispatch the Splunk SDK call to the appropriate class to process the records
if __name__ == "__main__": dispatch(CavestoresCommand,sys.argv,sys.stdin,sys.stdout,__name__)
#-----------------------------------------------------------------------------
#
#------------------------------------------------------------------------------#
