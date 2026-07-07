import logging
import os
import splunk.Intersplunk
import inspect
import shutil
    
logger = logging.getLogger('splunk.saviynt')
'''
    Setup Boto library if it does not exist to enable the user to establish connection
'''

def copyDirectory(src, dest):
    try:
        shutil.copytree(src, dest)
    except shutil.Error as e:
        logger.info('Directory not copied. Error: %s' % e)
    except OSError as e:
        logger.info('Directory not copied. Error: %s' % e)
        
def copyPackage(dirName):
    try:
        botoPath = os.path.join("site-packages",dirName)
        logger.info("botoPath :" + botoPath)
        pythonPath = inspect.getfile(os)
        logger.info("os path: "+ pythonPath)
        pos = pythonPath.rfind(os.sep)
        basePath = pythonPath[0:pos]
        
        dest = os.path.join(basePath,botoPath)
        logger.info("dest : "+dest)
        src = os.path.join(".",dirName)
        logger.info("src : "+src)
        copyDirectory(src, dest)
        
    except Exception,ex:
        logger.info(ex)
