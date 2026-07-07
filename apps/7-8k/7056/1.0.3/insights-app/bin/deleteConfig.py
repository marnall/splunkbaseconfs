import os
import sys

import splunk.Intersplunk
from helper.log_helper import LoggerClass

class ConfigDeleter:
    def deleteConfig(self, logger):
        results = []
        result={}        
        try:  
            logger.info("Deleting Config")           
            base_folder = os.environ['SPLUNK_HOME']         
            config_name = sys.argv[2]   
            logger.info(config_name)
            config_name_fields = config_name.split("_")
            config_name_fields.sort()
            config_name_sorted=config_name_fields[0] + "_" + config_name_fields[1]   
            data_folder = sys.argv[1]          
            path = os.path.join(base_folder,"etc","apps","insights-app", "local", data_folder)  
            filePath = os.path.join(path, config_name_sorted +".json")     
            isExist = os.path.exists(filePath)                
            if not isExist: 
                logger.info("Path is not found: " + filePath) 
            else: 
                os.remove(filePath) 
            
                
              
      
        except:
            import traceback
            stack =  traceback.format_exc()
            logger.critical("Error 3667: Traceback: " + str(stack))
            results = splunk.Intersplunk.generateErrorResults("Error Code: "+ str(3667))            
            splunk.Intersplunk.outputResults( results )
     
if __name__ == "__main__":
    loggerObj = LoggerClass()  
    logger = loggerObj.setup_logging()
    file_reader_object= ConfigDeleter()
    file_reader_object.deleteConfig(logger)
    
    