'''
Apius SSHFS Modular Input Script

Copyright (C) 2014 APIUS Technologies

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.


'''

import os,sys,logging,time,re,subprocess,threading,tempfile,signal,errno
import xml.sax.saxutils as xmlutils
import xml.dom.minidom as xml
import splunk.entity as entity

APPNAME = 'sshfs'
logger = logging.getLogger('splunk.' + APPNAME + ' ')

SCHEME = """<scheme>
    <title>SSHFS</title>
    <description>SSHFS input to mount remote filesystem</description>
    <streaming_mode>xml</streaming_mode>
    <use_external_validation>true</use_external_validation>
    <use_single_instance>false</use_single_instance>
    <endpoint>
        <args>
            <arg name="user">
                <title>Remote system username</title>
                <description>Set the username for SSH connection</description>
            </arg>
            <arg name="address">
                <title>Remote host address</title>
                <description>IP or hostname for SSH connection</description>
            </arg>
            <arg name="port">
                <title>Remote host port</title>
                <description>Port number for connection (default 22)</description>
                <required_on_create>false</required_on_create>
                <data_type>number</data_type>
                <validation>is_port('port')</validation>
            </arg>
            <arg name="dir">
                <title>Remote chroot directory</title>
                <description>Set the root directory (default /) to mount</description>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="auth">
                <title>Select private key type</title>
                <description>Set the type of private key. Ignore it if you set password. Allowed values: DES, RSA, ECDSA</description>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="password">
                <title>Password for ssh</title>
                <description>Set the ssh password. It will be immediately encrypted after saving and enabling source</description>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="privkey">
                <title>Priate key for ssh</title>
                <description>Set the ssh private key (without spaces, in one line). It will be immediately encrypted after saving and enabling source</description>
                <required_on_create>false</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def do_scheme():
    print SCHEME

def get_validation_config():
    val_data = {}
    sessID = '0'
    root = xml.parseString(sys.stdin.read()).documentElement
    logging.debug("XML: found items")
    try:
        sessID = root.getElementsByTagName("session_key")[0].childNodes[0].nodeValue
    except:
        pass
    try:
        item_node = root.getElementsByTagName("stanza")[0]
    except:
        item_node = root.getElementsByTagName("item")[0]
    if item_node:
        logging.debug("XML: found item")
        name = item_node.getAttribute("name")
        val_data["stanza"] = name
        params_node = item_node.getElementsByTagName("param")
        for param in params_node:
            name = param.getAttribute("name")
            logging.debug("Found param %s" % name)
            if name and param.firstChild and param.firstChild.nodeType == param.firstChild.TEXT_NODE:
                val_data[name] = param.firstChild.data
    return val_data, sessID

STOREDSIGNATURE = '<stored>'

def split_by_n( seq, n ):
    while seq:
        yield seq[:n]
        seq = seq[n:]

def storeSecrets(name, password, privkey, sessID):
    password = password if STOREDSIGNATURE!=password else None
    privkey = privkey if STOREDSIGNATURE!=privkey else None
    if not (password or privkey):
        logger.warning("No password and private key - can't store secrets")
        return
    try:
        # delete old entries, if exist
        try:
            for i in range(1,16):
                entity.deleteEntity('/storage/passwords/', ':' + name + str(i) + ':', APPNAME, "nobody", sessionKey=sessID)
        except Exception, e:
            pass
        # create new entries
        sdata = privkey if privkey else password
        ent = entity.getEntity('/storage/passwords/','_new', sessionKey=sessID)
        ent.namespace = APPNAME
        for i in range(1,16):
            ent['name'] = name + str(i)
            ent['password'] = sdata[:250]
            entity.setEntity(ent, sessionKey=sessID)
            sdata = sdata[250:]
            if not sdata:
                break
        logger.info("Stored secrets")
    except Exception, e:
        raise Exception(str(e))

def getSecrets(name, sessID):
    # get secrets
    entities = entity.getEntities(['admin', 'passwords'], namespace=APPNAME, owner='nobody', sessionKey=sessID)
    # hide secrets
    try:
        ent = entity.getEntity('/data/inputs/' + APPNAME + '/', name, sessionKey=sessID)
        ent.namespace = APPNAME
        if ent.get('auth') in ['ECDSA', 'RSA', 'DSA']:
            privkey = ent.get('privkey')
            if STOREDSIGNATURE != privkey:
                ent['privkey'] = STOREDSIGNATURE
                ent['password'] = ''
                entity.setEntity(ent, sessionKey=sessID, filterArguments='disabled')
                logger.info("Private key is hidden")
        else:
            password = ent.get('password')
            if (password!=STOREDSIGNATURE):
                ent['password'] = STOREDSIGNATURE
                ent['privkey'] = ''
                entity.setEntity(ent, sessionKey=sessID, filterArguments='disabled')
                logger.info("Password is hidden")
    except Exception, e:
        logger.error("Error - can not hide secrets")
        raise Exception("Can't hide password or public key")
    val = ''
    try:
        for i in range(1,16):
            v = entities[':' + name + str(i) + ':']['clear_password']
            val += v
    except:
        pass
    return val

def validate_and_get(val):
    try:
        config, sessID = get_validation_config()
        name = re.sub('^.*://',"", config.get("stanza"))
        address = config.get("address")
        port = config.get("port")
        user = config.get("user")
        directory = config.get("dir")
        auth = config.get("auth")
        password = config.get("password")
        privkey = config.get("privkey")
        if not port:
            port = '22'
        if not directory:
            directory = '/'
        if val:
            logger.debug("Validate input")
            if (privkey and password):
                print "<error><message>Enter either password or private key, not both.</message></error>"
                sys.exit(2)
            if (privkey or password) and (password != STOREDSIGNATURE or privkey != STOREDSIGNATURE):
                logger.info("Storing secrets")
                storeSecrets(name, password, privkey, sessID)
        else:
            secret = getSecrets(name, sessID)
            if auth in ['ECDSA', 'RSA', 'DSA']:
                privkey = secret
            else:
                password = secret
        return name, address, port, user, directory, auth, password, privkey, sessID
    except Exception, e:
        raise e

def launch_ssh(p, inp):
    try:
        if inp:
            out,err = p.communicate(input=("%s\n" % inp))
        else:
            out,err = p.communicate()
        logger.error(err)
    except Exception, e:
        logger.error("Got an exception: " + e)
        pass

def w8(p, pid):
    while True:
        try:
            os.kill(p, 0)
            os.kill(pid, 0)
        except OSError as err:
            # process was killed - we can exit
            if err.errno == errno.ESRCH:
                return
        time.sleep(3)

def umount(sshfspath, env):
    try:
        subprocess.Popen(['fusermount', '-u', sshfspath], shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE, env=env).communicate()
        logger.info("Unmounted previous instance")
    except:
        pass

def run():
    name, address, port, user, directory, auth, password, privkey, sessID = validate_and_get(False)
    env = os.environ
    sshfspath = env['SPLUNK_HOME'] + '/etc/apps/'+APPNAME+'/mountpoints/' + name
    # fix for not compatible OpenSSL(and other) library versions
    del env['LD_LIBRARY_PATH']
    # umount previous entry if script was killed
    umount(sshfspath, env)
    # mount
    try:
        os.mkdir(sshfspath)
        logger.debug("Made new directory - new input")
    except:
        pass
    if auth in ['ECDSA', 'RSA', 'DSA']:
        # create temp file with public key. Is there a better way to do it?
        handle, fname = tempfile.mkstemp()
        # don't use 1024bit RSA
        pktype = "EC" if auth=='ECDSA' else auth
        os.write(handle,'-----BEGIN ' + pktype + ' PRIVATE KEY-----\n')
        for r in split_by_n(privkey, 64):
            os.write(handle, r + '\n')
        os.write(handle,'-----END ' + pktype + ' PRIVATE KEY-----\n')
        os.close(handle)
        logger.debug("Privkey written")
        # call mount
        cmd = ['sshfs', '%s@%s:%s' % (user, address, directory), sshfspath, '-o', 'ro', '-f', '-p', port, '-o', 'workaround=rename', '-o', 'IdentityFile=%s' % fname, '-o', 'NumberOfPasswordPrompts=0']
        try:
            p = subprocess.Popen(cmd, shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE, env=env)
            threading.Thread(target=launch_ssh, args=(p, None)).start()
            # delete public key
            # we don't know when file is read and can delete it; 5secs should be OK for estabilishing ssh connection
            time.sleep(5)
            os.unlink(fname)
            logger.debug("Privkey removed")
        except:
            logger.error("Error - sshfs failed. Check if input data is correct")
    elif password:
        # call mount
        cmd = ['sshfs', '%s@%s:%s' % (user, address, directory), sshfspath, '-o', 'ro', '-f', '-p', port, '-o', 'workaround=rename', '-o', 'password_stdin' ]
        try:
            p = subprocess.Popen(cmd, shell=False, stderr=subprocess.PIPE, stdout=subprocess.PIPE, stdin=subprocess.PIPE, env=env)
            threading.Thread(target=launch_ssh, args=(p, password)).start()
        except:
            logger.error("Error - sshfs failed. Check if input data is correct")
    # wait until parrent process (shell) exit
    ppid = os.getppid()
    if ppid > 1:
        w8(p.pid, ppid)
    logger.debug("Process detached - input was disabled or removed")
    # shut down launched sshfs process. Is it necessary?
    try:
        p.send_signal(signal.SIGINT)
    except:
        logger.warning("sshfs already ended")
    # unmount endpoint
    try:
        umount(sshfspath, env)
    except:
        pass
    # delete secrets if input was deleted
    try:
        ent = entity.getEntity('/data/inputs/' + APPNAME + '/', name, sessionKey=sessID)
        logger.debug("Input was not deleted")
    except:
        # it was deleted now - delete secrets
        logger.info("Input was deleted")
        try:
            for i in range(1,16):
                entity.deleteEntity('/storage/passwords/', ':' + name + str(i) + ':', APPNAME, "nobody", sessionKey=sessID)
        except:
            pass
        # and delete mountpoint
        try:
            os.rmdir(sshfspath)
        except:
            logger.debug("Could not remove mountpoint. Not empty?")
            pass
    # and force exit
    logger.debug("Done")
    os._exit(0)

if __name__ == '__main__':
    logger.debug("Started")
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            validate_and_get(True)
    else:
        run()
    sys.exit(0)
