# Copyright (C) 2019 Dominique Vocat
# python 3 compatible

import splunk, base64, sys, os, time, json, re, shutil, subprocess, platform, logging, logging.handlers, time
import splunk.rest as splunk_rest
from io import open
from six.moves import range

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.clilib.cli_common import getMergedConf

app_name = "minishell"
SPLUNK_HOME = os.environ['SPLUNK_HOME']

# From here: http://dev.splunk.com/view/logging/SP-CAAAFCN
def setup_logging():
    logger = logging.getLogger("a")
    file_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, 'var', 'log', 'splunk', app_name + ".log"), mode='a', maxBytes=25000000, backupCount=2)
    formatter = logging.Formatter("%(created)f %(levelname)s pid=%(process)d %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.setLevel("INFO");
    return logger
logger = setup_logging()

logger.info('launch handler terminal')

def flatten_query_params(params):
    # Query parameters are provided as a list of pairs and can be repeated, e.g.:
    #
    #   "query": [ ["arg1","val1"], ["arg2", "val2"], ["arg1", val2"] ]
    #
    # This function simply accepts only the first parameter and discards duplicates and is not intended to provide an
    # example of advanced argument handling.
    flattened = {}
    for i, j in params:
        flattened[i] = flattened.get(i) or j
    return flattened

class req(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, in_string):
        textchars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
        is_binary_string = lambda bytes: bool(bytes.translate(None, textchars))
        debug = ""
        user = ""
        result = ""
        reason = ""
        form = {"action": "", "path": "", "param1": ""}
        logger.info( "lets go terminal.py "+str(in_string))
        try:
            conf = getMergedConf(app_name)
            in_payload = json.loads(in_string)

            user = in_payload['session']['user']
            sessionKey = in_payload['session']['authtoken']
            logger.info( sessionKey )
            server_response, server_content = splunk_rest.simpleRequest('/services/authentication/users/' + user + '?output_mode=json', sessionKey)
            #logger.info( server_response )
            #logger.info( server_content )

            userinfo = json.loads(server_content)
            email = userinfo['entry'][0]['content']['email']
            if userinfo['entry'][0]['content']['realname']:
                fullname = userinfo['entry'][0]['content']['realname']
            else:
                fullname = user #fallback if we are built in admin or some user not known to splunk really

            method = in_payload['method']
            rest_path = in_payload['rest_path']
            logger.info("checkpoint1")
            try: #set session key in env to run splunk cli with logged in user
                os.environ['SPLUNK_TOK'] = sessionKey
                logger.info('token set: '+str(os.environ['SPLUNK_TOK']))
                os.environ['GIT_AUTHOR_NAME'] = fullname
                os.environ['GIT_AUTHOR_EMAIL'] = email
                os.environ['GIT_COMMITTER_NAME'] = fullname
                os.environ['GIT_COMMITTER_EMAIL'] = email
                os.environ['HOME']= os.environ['SPLUNK_HOME']
            except Exception as e:
                logger.info('uh oh...')
                logger.info(str(e))
                pass

            if in_payload['method'] != "POST":
                return {'payload': {"message": "Webservice terminal.py is working but it must be called via POST"}, 'status': 200 }
                #return json.dumps(in_payload)
            else:
                #here we go again
                output = ''
                success = False
                logger.info("checkpoint2")

                form_params = flatten_query_params(in_payload['form'])
                logger.info("checkpoint3")
                logger.info( form_params )
                command = form_params['command']
                logger.info("checkpoint4")
                #logger.info( command )
                PWD = form_params['pwd']
                logger.info("checkpoint5")

                try: #get command whitelist, used also for tab completion
                    with open(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','minishell','appserver','static','commands.json'),'r') as f:
                        commandwhitelist = f.read()
                    commandwhitelist = json.loads(commandwhitelist)
                    logger.info( commandswhitelist )
                except:
                    logger.info("checkpoint error with whitelist")
                    pass

                logger.info("checkpoint4")
                if not command:
                    output = json.dumps(dict(success=False, payload="", pwd=PWD, command=command)) #"no command"
                    return {'success':'False','payload': output, 'status': 200}
                else:
                    #splitCommand = re.findall("(?:\".*?\"|\S)+", command) #try to split it smartly, shlex fails when there are parameters containing " etc like git commit --author="Dominique Vocat <dominique.vocat@helvetia.ch>"
                    import shlex
                    splitCommand = shlex.split(command)
                    logger.info( splitCommand )
                    os.chdir( PWD ) #set current working dir
                    logger.info("audit - user=" + user + " sends command: "+ command)
                    try:
                        if splitCommand[0] == "help":
                            logger.info('user asked for help, dump the help.txt')
                            with open(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','minishell','bin','help.txt'),'r') as f:
                                output = f.read()
                                success = True
                        elif splitCommand[0] == "debuginfo": #mostly for me
                            output = json.dumps(in_payload)
                            success = True
                        elif splitCommand[0] == "kill": #mostly for me
                            logger.info("break script to test changes...")
                            os._exit(1) #bad, bad, baaaaad
                        # - fspath
                        elif splitCommand[0] == "fspath": #second parameter is considered a path so we try to come up with suggestions for completion
                            logger.info( "path to complete: "  + form_params['fspath'] )
                            #output = "dummy"
                            #success = False
                            fspath = form_params['fspath']
                            if fspath.startswith('/'):
                                logger.info( "list from full path" )
                                results = os.listdir( os.path.dirname(fspath) ) #return dirlist results relative to current dir...
                                for idx, item in enumerate(results):
                                    results[idx] = os.path.dirname(fspath)+"/"+item
                                return {'payload':results} #json.dumps( results ) #return dirlist results relative to current dir...
                            else:
                                logger.info( "list from relative path" )
                                return {'payload':os.listdir( PWD )} #json.dumps( os.listdir( PWD ) ) #return dirlist results relative to current dir...
                        #-
                        elif splitCommand[0] == "pwd":
                            try:
                                output = PWD
                                success = True
                            except KeyError as e:
                                cherrypy.session['user']['pwd'] = os.environ['SPLUNK_HOME']
                                logger.info('no pwd was set, default to splunk_home')
                                output = 'pwd: ' + cherrypy.session['user']['pwd'] #pwd
                            logger.info('we showed the pwd')
                        elif splitCommand[0] == "cd":
                            tmpPWD = os.path.abspath(os.path.join(PWD, splitCommand[1]))
                            if os.path.isdir(tmpPWD):
                                PWD = tmpPWD
                                success = True
                                output = "" #"set current working dir to " + PWD
                            else:
                                logger.info('path does not exist, fail')
                                output = 'does not seem to be a directory that exists...'
                                success = False
                        elif splitCommand[0] == "locale":
                            returnvalue=[]
                            returnvalue.append("current filesystemencoding setting: " + str(sys.getfilesystemencoding()))
                            import locale
                            returnvalue.append("current locale setting: " +str(locale.nl_langinfo(locale.CODESET)))
                            if len(splitCommand) > 1:
                                returnvalue.append("try to set it properly to " + str(splitCommand[1]))
                                locale.setlocale(locale.LC_ALL, splitCommand[1])
                                sys.setdefaultencoding('UTF8')
                                returnvalue.append("current filesystemencoding setting: " + str(sys.getfilesystemencoding()))
                                returnvalue.append("current locale setting: " +str(locale.nl_langinfo(locale.CODESET)))
                            output = '\n'.join(returnvalue)
                            success = True
                        elif splitCommand[0] == "whoami":
                            returnvalue=[]
                            import getpass
                            returnvalue.append("we run as user: " + str(getpass.getuser()) + " in group " + str(os.getegid()) + " / in splunk we are signed in as " + fullname +" (" + user + ") ")
                            output = '\n'.join(returnvalue)
                            success = True
                        elif splitCommand[0] == "popen": #this is undocumente, m'key?
                            stdout, stderr = None, None
                            #set virtual environment to run python2 stuff
                            import venv
                            venv = os.environ.copy()
                            #venv['ansible_python_interpreter'] = "/usr/bin/python2"
                            #venv['ANSIBLE_PYTHON_INTERPRETER'] = "/usr/bin/python2"
                            venv['LD_LIBRARY_PATH'] = "/usr/lib64/python2.7/"
                            try:
                                logger.info(splitCommand)
                                stdout, stderr = subprocess.Popen(splitCommand[1:],
                                    shell=False, #shell=True
                                    env=venv, #reference python2 env, hard force system python 2.7
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    universal_newlines=True).communicate()
                                if stdout:
                                    output = "stdout: " + stdout + "stderr: " + stderr
                                    success = True
                                    
                                if stderr:
                                    output = "stderr: " + stderr #return self.render_json(dict(success=False, payload=stderr, pwd=PWD, command=command))
                                    success = False
									#payload = stdout
                                #output = str(stdout) + str(stderr)
        
                            except Exception as e:
                                pass
								#return self.render_json(dict(success=False, payload=e, pwd=PWD, command=command))
                        #-
                        elif splitCommand[0] in commandwhitelist: #pass through, no python reimplementation
                            stdout, stderr = None, None
                            #set virtual environment to run python2 stuff
                            import venv
                            venv = os.environ.copy()
                            #venv['ansible_python_interpreter'] = "/usr/bin/python2"
                            #venv['ANSIBLE_PYTHON_INTERPRETER'] = "/usr/bin/python2"
                            venv['LD_LIBRARY_PATH'] = "/usr/lib64/python2.7/"
                            try:
                                logger.info(splitCommand)
                                stdout, stderr = subprocess.Popen(splitCommand,
                                    shell=False, #shell=True
                                    env=venv, #reference python2 env, hard force system python 2.7
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    universal_newlines=True).communicate()
                                if stdout:
                                    output = stdout
                                    success = True
                                                                        #payload = stdout
                                if stderr:
                                    output = stderr #return self.render_json(dict(success=False, payload=stderr, pwd=PWD, command=command))

                            except Exception as e:
                                pass
                                                                #return self.render_json(dict(success=False, payload=e, pwd=PWD, command=command))
                        #- last
                        elif splitCommand[0] == "splunkrest":
                            logger.info("using splunkrest")
                            if len(splitCommand)>1:
                                try:
                                    if splitCommand[1] =="post" or splitCommand[1] =="POST":
                                        logger.info("POST")
                                        requestmethod="POST"
                                        url=str(splitCommand[2])
                                    else:
                                        logger.info("GET")
                                        requestmethod="GET"
                                        url=str(splitCommand[1])
                                    server_response, server_content = splunk_rest.simpleRequest(url+'?count=0&output_mode=json', sessionKey, method=requestmethod)
                                    logger.info("server response")
                                    logger.info(server_response)
                                    logger.info(server_content)
                                    output = str(server_response)+ "\n" + str(server_content)
                                    success = True
                                except Exception as e:
                                    import traceback
                                    stack =  traceback.format_exc()
                                    logger.info('exception='+str(e)+' stacktrace='+str(stack))
                                    output = str(e) #return self.render_json(dict(success=False, payload=str(e), pwd=PWD, command=command))
                                    success = False
                            else:
                                output = "no parameters specified" #return self.render_json(dict(success=False, payload="no parameters specified", pwd=PWD, command=command))
                                success = False
                        #- second last
                        else:
                            #like cat read file line by line and pass to jquery - pass it as payload
                            logger.info("try to see if there is a script matching...")
                            scriptfile = False #hackish
                            if os.path.exists(splitCommand[0]):
                                scriptfile = splitCommand[0]
                            elif os.path.exists( os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','minishell','bin','scripts',splitCommand[0]) ):
                                scriptfile = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','minishell','bin','scripts',splitCommand[0])
                            else: # last resort
                                #output = 'command ' + splitCommand[0] + ' is not supported or misspelled, try "help" for more...'
                                #return self.render_json(dict(success=False, payload=payload, pwd=PWD, command=command))
                                logger.info("didn't find any suitable command or scipt")
                                output = 'Kernel panic!!! just kidding... the command is not in the whitelist.'
                                success = False
                                #return
                            if scriptfile:
                                logger.info("run the script " +str(scriptfile))
                                with open(scriptfile) as f:
                                    regex = "\$(?P<argv>\d+)"
                                    scriptlines = []
                                    lines = f.read().splitlines()
                                    logger.info("script content:")
                                    logger.info(lines)
                                    for line in lines:
                                        tmp = re.sub(regex, lambda match: '%s' % (splitCommand[int(match.group(1))]),line)
                                        tmp = re.sub("\$email", email, tmp)
                                        tmp = re.sub("\$fullname", fullname, tmp)
                                        scriptlines.append( tmp )
                                    src = '\n'.join(scriptlines)
                                output = json.dumps(dict(success=success, payload=src, pwd=PWD, command=command, script=True))
                                return {'success': 'true','payload': output, 'status': 200}
                        #- last
                        """
                        else: # last resort
                            output = 'Kernel panic!!! just kidding...'
                            success = False
                        """
                        output = json.dumps(dict(success=success, payload=output, pwd=PWD, command=command))
                        logger.info( output )
                        return {'success': 'true','payload': output, 'status': 200}
                    except:
                        #output = "error occured..."
                        #success = False
                        import traceback
                        debug =  traceback.format_exc()
                        logger.info(debug)
                        return {'success':'False','payload': {'payload': debug, 'success': 'False', 'pwd': PWD}, 'status': 200}
                        #pass
        except:
            pass
