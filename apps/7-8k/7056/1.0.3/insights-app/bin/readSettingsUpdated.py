import os
import sys
import json
import splunk.Intersplunk
from helper.log_helper import LoggerClass

class SettingsReaderUpdated:
    def readJson(self, logger):
        results = []
        result={}        
        try:  
            logger.info("Reading settings")     
            base_folder = os.environ['SPLUNK_HOME']        
            path = os.path.join(base_folder, "etc", "apps", "insights-app","local", "settings")  
            isExist = os.path.exists(path)           
            if not isExist: 
                 logger.info("Path is not found: " + path)    
                 
            filePath = os.path.join(path, "settings.json")        
            output=[]
            indexes=[]
           
            
            with open(filePath) as handle:
                result = json.load(handle)
                indexes = result['indexes']
                          
                for ind in indexes:                     
                    output.append(ind)              
                splunk.Intersplunk.outputResults(output)  
        except:
            import traceback
            stack =  traceback.format_exc()
            logger.critical("Error 399: Traceback: " + str(stack))
            results = splunk.Intersplunk.generateErrorResults("Error Code: "+ str(399))
            
            splunk.Intersplunk.outputResults( results )

     
if __name__ == "__main__":
    loggerObj = LoggerClass()  
    logger = loggerObj.setup_logging()
    file_reader_object= SettingsReaderUpdated()
    file_reader_object.readJson(logger)
    
    