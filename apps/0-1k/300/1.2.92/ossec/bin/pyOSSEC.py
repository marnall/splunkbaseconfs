#!/opt/splunk/bin/python
############################################################
#
# Python abstraction library for OSSEC Agent Management
#
# Written as part of Splunk for OSSEC,
# Copyright (c) 2010-2012, Paul Southerington
#
############################################################
import sys
import os
import fcntl
import socket
import logging

sys.path.append('../3rdparty/pexpect-2.3')
sys.path.append('./3rdparty/pexpect-2.3')
if 'SPLUNK_HOME' in os.environ:
        sys.path.append(os.environ['SPLUNK_HOME'] + '/etc/apps/ossec/3rdparty/pexpect-2.3')
import pexpect







######################################################################
# Wrapper for audit logging, for future use.
#    (may eventually be rolled into core pyOSSEC library)
######################################################################

class Log():
    """
    Logging wrapper for scripts that use pyOSSEC. Handling logging from
    the calling scripts is simpler, but eventually this may be wrapped
    into the pyOSSEC class itself.
    """
    def __init__(self, appname='Splunk for OSSEC', filename="../log/pyossec.log"):
                self.logger = logging.getLogger(appname)
                self.logger.setLevel(logging.DEBUG)

                fh = logging.FileHandler(logfile)
                fh.setLevel(logging.DEBUG)

                format  = "%(asctime)s - %(name)s - %(levelname)s - "
                format += self.username + " - "
                format += " - %(message)s"

                formatter = logging.Formatter(format)
                fh.setFormatter(formatter)
                self.logger.addHandler(fh)

                self.logger.debug("Logging subsystem initialized.")

    def info(self, message):
        return self.logger.info(message)





######################################################################
# Utility functions. These are not really part of core OSSEC support
# but are used across multiple search commands. In the future, they
# will likely be removed, possibly to a separate utility library.
#######################################################################

def parse_args(argv, default_args = {}, allow_other_args = False):
    """
    Read in allowed command-line arguments.
    By default, expected arguments will be included (with defaults if
    no value is specified) and other arguments will be ignored.
    """
    args = default_args
    for arg in sys.argv[1:]:
            kv = arg.split('=')
            if len(kv) == 2:
                    k = kv[0].lower().strip()
                    v = kv[1].strip()

            for i in default_args:
                if i == k:
                    args[k] = v.strip('\'"')
    return args





######################################################################
# More utility functions, specifically for working with config files.
######################################################################

def to_bool(v):
    """
    Convert an arbitrary value to a boolean. Defaults to False.
    """
    try:
        if v[0].upper() == 'F':
            return False
        elif v[0].upper() == 'T':
            return True
        else:
            return bool(v)
    except:
        return False


def parse_config():
    """
    Parse all of the default config files.
    """
    cfg = parse_config_file('../default/ossec_servers.conf')
    cfg = parse_config_file('../local/ossec_servers.conf', cfg)

    # Remove disabled stanzas from the merged config. We need to do
    # this here, else we would not be able to disable a host in local
    # after it had been defined in default.
    disabled_stanzas = []
    for sectionName in cfg:
        if 'DISABLED' in cfg[sectionName]:
            if cfg[sectionName]['DISABLED']:
                disabled_stanzas.append(sectionName)
    for sectionName in disabled_stanzas:
        del cfg[sectionName]
    
    return cfg


def parse_config_file(config_file, config = {}):
    """
    Parse the app's config file for information about OSSEC servers.
    
    Returns a dictionary of dictionaries, keyed first by ossec_server and
    then by configuration key name.

    If an existing config is provided, it newly read configurations will take
    precedence, while existing settings that are not overridden will be
    preserved. The existing config is assumed to already conform to the 
    correct structure.

    Attempts to parse a non-existing config file will result in an
    empty/unmodified config being returned.

    Disabled stanzas are not de-activated here.
    """
    BOOL_FIELDS = [ 'DISABLED' ]

    try:
        f = open(config_file, 'r')
    except:
        return config
    
    
    sectionName = ''
    if '' in config:
        section = config['']
    else:
        section = {}

    for line in f:
        line = line.strip()
        if len(line) == 0: continue
        if line[0] == '#': continue

        if line[0] == '[':
            # Start of new host configuration
            config[sectionName] = section
    
            sectionName = line.strip('[]')
            if sectionName  == '_local':
                sectionName = socket.gethostname().split('.')[0]

            if sectionName in config:
                # Load any pre-existing configuration entries
                section = config[sectionName]
            else:
                section = {}

        else:
            eq = line.find('=')
            if eq >= 0:
                k = line[:eq].strip().strip('"').upper()
                v = line[eq+1:].strip()
                if len(v) == 0:
                    if k in section: del section[k]
                else:
                    v = v.strip('"')
                    if k in BOOL_FIELDS:
                        v = to_bool(v)
                    section[k] = v

    config[sectionName] = section

    if len(config['']) == 0:
        del config['']

    f.close()
    return config


def dump_config(config):
    for host in config:
        print '[' + host + ']'
        for key in config[host]:
            print key, '=', config[host][key]
        print





######################################################################
# Exception classes
######################################################################

class OSSECError(Exception):
    """Base class for exceptions in this module"""
    pass

class OSSECNotConfiguredError(OSSECError):
    """Raised when trying to perform an operation that requires configuration"""
    pass

class OSSECNamingConflictError(OSSECError):
    """Raised when trying to use a duplicate name or ID"""
    pass

class OSSECInvalidNameError(OSSECError):
    """Raised when trying to use a name or ID that is not in a valid format"""
    pass

class OSSECNotFoundError(OSSECError):
    """Raised when trying to perform an operation on a non-existent name or ID"""
    pass

class OSSECTimeoutError(OSSECError):
    """Raised when a timeout occurs"""
    pass

class OSSECPasswordError(OSSECError):
    """
    Raised when an unexpected password prompt is encountered,
    or when trying to use an invalid password.
    """
    pass



######################################################################
# OSSEC Server Interface
######################################################################

class OSSECServer():
    """
    Basic interface to OSSEC server for agent management. Access to
    remote servers is usable via SSH and pexpect.

    At present, this just wraps the OSSEC manage_agents command. For
    local OSSEC installations, this isn't nearly as efficient as
    accessing the agents file directly, but this approach facilitates
    operation over SSH and when using sudo. If and when OSSEC gets
    a native RPC interface, we'll switch to that.

    Rudimentary locking is included, but only applies to processes
    accessing the backend through this object. The underlying agents
    file is not locked.

    Between method calls, the manage_Agent process should always be
    waiting at the 'Choose your action' prompt.
    """

    def __init__(self, ossec_server, username='-'):
        """
        Establish the connection to the OSSEC manage_agents process.

        COMMAND is the command required to run manage_agents, and may
        include prefixes for ssh and/or sudo execution.
        """
        self.connected = False
        self.username  = username
        self.lockname  = str(ossec_server) + '.lock'
        self.lockfile  = None
        self.read_config_entry(ossec_server)
    
    def __del__(self):
        """
        Close down the connection to the OSSEC management process.
        """
        try:
            if self.connected:
                self.c.sendline('Q')
            self.unlock()
        except:
            pass


    def lock(self):
        """
        Rudimentary concurrency protection. We don't want to allow
        more than one search to access the OSSEC backend at a time.
        """
        self.lockfile = open(self.lockname, 'wb')
        fcntl.flock(self.lockfile, fcntl.LOCK_EX)
        
    def unlock(self):
        """
        Release lock on OSSEC manage_agent operations.
        """
        if self.lockfile != None:
            fcntl.flock(self.lockfile, fcntl.LOCK_UN)
        try:
            os.unlink(self.lockname)
        except:
            pass
        
    def agent_status(self):
        """
        Checks the agent status. Uses 'agent_control' instead of
        'manage_agents'.
        """
        if 'AGENT_CONTROL' not in self.cfg:
            raise OSSECNotConfiguredError('AGENT_CONTROL not configured for this server')
        cmd = self.cfg['AGENT_CONTROL']

        # Temp - For backwards compatibility, check for an remove an extra '-l' parameter
        cmd = cmd.strip().rstrip('-l')

        cmd += ' -l'
        p = pexpect.spawn(cmd, timeout=30)
        z = p.expect([ 'ID:(.*)List of agentless devices:', '(?i)password' ] )
        if z == 1:
            p.close()
            raise OSSECPasswordError('Error: Password prompt encountered. Aborting.')

        buf = p.match.groups()[0]
        buf = buf.split('ID:')

        results = []
        for line in buf:
            #parts = line.split(',')
            #if len(parts) == 4:
                        #        agent_id = parts[0].strip()
                        #        agent_name = parts[1][7:].strip()
                        #        agent_ip = parts[2][4:].strip()
            #    agent_status = parts[3].strip()
            #results.append ( (agent_id, agent_name, agent_ip, agent_status) )
            results.append('ID: ' + line.strip())

        p.expect(pexpect.EOF)
        p.close()
        return results


    def connect(self):
        """
        Connect to the manage_agents process.
        """
        if 'MANAGE_AGENTS' not in self.cfg:
            raise OSSECNotConfiguredError('No manage agents process defined for this server')
        if self.cfg['MANAGE_AGENTS'] == '':
            raise OSSECNotConfiguredError('No manage agents process defined for this server')
        self.lock()
        self.c = pexpect.spawn(self.cfg['MANAGE_AGENTS'], timeout=30)
        
        # Check for common connection problems
        try:
            firstLine = self.c.readline()
        except pexpect.TIMEOUT:
            raise OSSECError('Timeout occurred waiting for first line of connection response.')
            
        l = firstLine.lower().strip()
        if l.find('password') >= 0:
            raise OSSECPasswordError(firstLine)
        elif l.find('ssh') >= 0 or l.find('sudo') >= 0:
            raise OSSECError(firstLine)
            
        try:
            z = self.c.expect_exact(['Choose your action:','password','Password'], 20)
        except pexpect.TIMEOUT:
            raise OSSECTimeoutError('Timed out: ' + str(firstLine))
        
        if z == 0:
            # Normal/expected result
            self.connected = True
            self.cache_agents()
            return
        elif z == 1:
            raise OSSECNotConfiguredError('Password prompt encountered (possibly ssh password)')
        elif z == 2:
            raise OSSECNotConfiguredError('Password prompt encoutnered (possibly sudo password)')
            

    def cache_agents(self):
        """
        Get a local copy of the list of agents. Among other things, this
        allows performing sanity checks before sending commands.
        """
        if not self.connected:
            self.connect()

        self.agents = []
        self.c.sendline('L')

        z = self.c.expect(['Available agents:\s+(.*)\s+\*\* Press ENTER', 'No agent available'], 5)
        if z == 1:
            self.c.sendline('')
            return []

        buf = self.c.match.groups()[0]
        buf = buf.split('ID:')
        for line in buf:
            parts = line.split(',')
            if len(parts) == 3:
                agent_id = parts[0].strip()
                agent_name = parts[1][7:].strip()
                agent_ip = parts[2][4:].strip()
                self.agents.append( (agent_id, agent_name, agent_ip) )

        self.c.sendline('')
        self.c.expect_exact('Choose your action')

        self.agent_ids = []
        self.agent_names = []
        for agent in self.agents:
            self.agent_ids.append(agent[0])
            self.agent_names.append(agent[1].lower())


    def agent_detail(self, id, raw=False):
        """
        Get extended agent information.
        """
        if 'AGENT_CONTROL' not in self.cfg:
            raise OSSECNotConfiguredError('AGENT_CONTROL not configured for this server')

        if not raw:
            raise NotImplementedError('Agent info is only implemented for raw output mode.')
        
        cmd = self.cfg['AGENT_CONTROL']
        # Temp - For backwards compatibility, check for an remove an extra '-l' parameter
        cmd = cmd.replace('-l', '').strip()
        cmd += ' -s -i ' + str(id)
        output = pexpect.run(cmd)
        
        firstLine = output.split('\n')[0].strip()
        fields = firstLine.split(',')
        if fields[0] != agent_id:
            raise OSSECError('Unexpected output from agent_control')

        return firstLine
            
        
    def extract_key(self, agent_id):
        """
        For a given agent, extract the OSSEC key.
        """
        if not self.connected:
            self.connect()

        self.c.sendline('E')
        self.c.expect_exact('Provide the ID of the agent')
        self.c.sendline(agent_id)

        z = self.c.expect_exact(['Agent key information', 'ID is not present'])
        if z == 1:
            self.c.sendline('\q')
            raise OSSECNotFoundError( 'Agent ID not found. (' + str(agent_id) + ')' )

        self.c.expect(':')
        self.c.expect('(\S+)')
        key = self.c.match.groups()[0]

        self.c.expect('Press ENTER')
        self.c.sendline('')

        return key
        

    def find_agent_ids(self, agent_name):
        """
        Given an agent name, return a list of all matching agent IDs
        """
        if not self.connected:
            self.connect()

        results = []
        for (xid, xname, xip) in self.agents:
            if agent_name.lower() == xname:
                results.append(xid)
        return results


    def add_agent(self, agent_name, agent_ip, agent_id=''):
        """
        Add a new agent record and return the agent ID.
        """
        if agent_id != '':
                agent_id = agent_id.rjust(3, '0')


        errmsg = None
        if agent_name == None:    errmsg = 'Invalid agent name.'
        if agent_ip == None:    errmsg = 'Invalid agent IP'
        if agent_id == None:    errmsg = 'Invalid agent ID'
        if errmsg != None:
            raise OSSECInvalidNameError('Invalid agent name.')

        if not self.connected:
            self.connect()


        self.c.sendline('A')

        # Agent Name
        self.c.expect_exact('name for the new agent:')
        z = self.c.sendline(agent_name)
        z = self.c.expect_exact(['IP Address of the new agent', 'already present', 'Invalid name'])
        if z == 1:
            self.c.sendline('\q')
            raise OSSECNamingConflictError('Duplicate agent name')
        if z == 2:
            self.c.sendline('\q')
            raise OSSECInvalidNameError('Invalid agent name.')

        # Agent IP
        self.c.sendline(agent_ip)
        z = self.c.expect_exact(['ID for the new agent', 'Invalid IP'])
        if z == 1:
            self.c.sendline('\q')
            raise OSSECInvalidNameError('Invalid IP address')

        # Agent ID
        self.c.sendline(agent_id)
        z = self.c.expect(['ID:(\d+)', 'already present', 'Invalid ID'])
        if z == 1:
            self.c.sendline('\q')
            raise OSSECNamingConflictError('Duplicate agent ID')
        elif z == 2:
            self.c.sendline('\q')
            raise OSSECInvalidNameError('Invalid agent ID')
        agent_id = self.c.match.groups()[0]

        # Confirm action, then return to menu
        self.c.sendline('Y')
        self.c.expect_exact('Choose your action:')

        self.agents.append( (agent_id, agent_name, agent_ip) )
        self.agent_ids.append(agent_id)
        self.agent_names.append(agent_name)

        return str(agent_id)



    def remove_agent(self, agent_id):
        """
        Remove an OSSEC agent record.

        Attempting to remove an agent that once existed but has been
        deleted currently trigers a bug in manage_agents and causes
        the program to crash. We cannot detect this remotely since
        the removed agents do not show up in the output of the (L)
        menu command.
        """
        agent_id = agent_id.rjust(3, '0')

        if agent_id == None:
            raise OSSECInvalidNameError('A valid agent ID is required.')

        if not self.connected:
            self.connect()

        self.c.sendline('R')
        self.c.expect_exact('Provide the ID of the agent to be removed')

        # Agent ID
        self.c.sendline(agent_id)
        z = self.c.expect_exact(['Confirm deleting it', 'ID is not present'])
        if z == 1:
            self.c.sendline('\q')
            raise OSSECNotFoundError('ID is not present')

        # Finish up and exit the program
        self.c.sendline('Y')
        self.c.expect_exact('Choose your action:')

        return 'Agent removed.'

        

    def read_config_entry(self, ossec_server):
        """
        Configure the object to manage a specific OSSEC server (local or remote).
        """
        cfg = parse_config()
        if ossec_server not in cfg:
            msg = "This OSSEC Server is not configured for agent management."
            raise OSSECNotConfiguredError(msg)

        self.cfg = cfg[ossec_server]




if __name__ == "__main__":
    if os.uname()[0] not in ('pstest'):
        print
        print 'This module is a library and not intended to be run directly.'
        print
        sys.exit()

    else:
        # Misc testing - ignore.

        server = OSSECServer('ossec_server')
        server.agent_status()

        print 'Connected to server'
        server.cache_agents()
        print 'Cached agents'

        for (agent_id, agent_name, agent_ip) in server.agents:
            print (agent_id, agent_name, agent_ip)
            print server.agent_detail(agent_id, True)

        sys.exit()
        for id in server.agent_ids:
            print id, '\t', server.extract_key(id)
        print server.agent_ids
        print server.add_agent('TestAgent2', '127.0.0.1', '100')
        print server.add_agent('TestAgent2', '127.0.0.1', '100')
        print server.add_agent('TestAgent2', '127.0.0.1', '100')
        print server.remove_agent('100')
        print server.add_agent('TestAgent2', '127.0.0.1', '100')
        server.cache_agents()
        for agent in server.agents:
            print agent


