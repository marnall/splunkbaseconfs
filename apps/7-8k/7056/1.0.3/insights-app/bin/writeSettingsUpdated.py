import os
import sys
import splunk.Intersplunk
from helper.log_helper import LoggerClass

class SetingsWriterUpdated:
    def writetoJson(self, logger): 
        results = []
        try:  
            logger.info("writting settings")   
            base_folder = os.environ['SPLUNK_HOME']      

            path = os.path.join(base_folder,"etc", "apps", "insights-app", "local", "settings")  
            isExist = os.path.exists(path)
            if not isExist: 
                os.makedirs(path)    
            filePath= os.path.join(path, "settings.json")              
            with open(filePath , "w") as handle:
                handle.write(sys.argv[1])
                handle.write("\n")    
        except:
            import traceback
            stack =  traceback.format_exc()
            logger.critical("Error 925 : Traceback: " + str(stack))
            results = splunk.Intersplunk.generateErrorResults("Error Code: "+ str(925))
            
            splunk.Intersplunk.outputResults( results )
  
if __name__ == "__main__":
    loggerObj = LoggerClass()  
    logger = loggerObj.setup_logging()
    file_writer_object= SetingsWriterUpdated()
    file_writer_object.writetoJson(logger)
    