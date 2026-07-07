import sys,os,hashlib,time
import json
import shutil
  

def save_file(file,settings):
    print >> sys.stderr, "INFO Sending file with settings %s" % settings
    
    directory = settings.get('directory')
    filename_prefix = settings.get('filename_prefix')
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    
    app_name = "Scheduled Export of Indexed Data to File"
    
    try:  
        
        dstfile =  os.path.join(directory, filename_prefix + '_' + timestamp + '.csv.gz')
        shutil.copy(file, dstfile) 
    
        return True  
    except Exception as tre:  
        print >> sys.stderr, tre  
        return False  
    except:  
        e = sys.exc_info()[0]  
        print >> sys.stderr, "ERROR Error sending file: %s" % e  
        return False  
  
  
if __name__ == "__main__":  
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":  
        payload = json.loads(sys.stdin.read())
        if not save_file(payload.get('results_file'),payload.get('configuration')):
            print >> sys.stderr, "FATAL Failed trying to send file"
            sys.exit(2)
        else:
            print >> sys.stderr, "INFO file successfully sent"
    else:
        print >> sys.stderr, "FATAL Unsupported execution mode (expected --execute flag)"
        sys.exit(1)
