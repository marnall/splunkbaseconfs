import os
import sys
import splunk.Intersplunk
from helper.log_helper import LoggerClass

class FileListReader:
    def getListOfiles(self, logger):
        results = []   
        output =[]           
        try:
            logger.info("listing Analysis")              
            base_folder = os.environ['SPLUNK_HOME']     
            data_folder = sys.argv[1]    
            logger.info("User:  " + data_folder)     
            path = os.path.join(base_folder,"etc", "apps", "insights-app", "local", "saved_analysis", data_folder)            
            isExist = os.path.exists(path)           
            if not isExist:
                logger.info("Path is not found: " + path)
                                
            dir_list = os.listdir(path)  
            i = 0
            for l in dir_list:
                output.append({i:dir_list[i]})
                i = i + 1
            splunk.Intersplunk.outputResults(output)           
        except:
            import traceback
            stack =  traceback.format_stack
            logger.critical("Error 365: Traceback: " + str(stack))
            results = splunk.Intersplunk.generateErrorResults("Error Code: "+ str(365))            
            splunk.Intersplunk.outputResults( results )
   
if __name__ == "__main__":
    loggerObj = LoggerClass()  
    logger = loggerObj.setup_logging()
    file_reader_object= FileListReader()
    file_reader_object.getListOfiles(logger)
    
    