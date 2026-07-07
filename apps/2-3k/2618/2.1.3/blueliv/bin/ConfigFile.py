# -*- coding: utf-8 -*
try:
    import configparser as ConfigParser
except:
    import ConfigParser
import os

class ConfigFile():

    def __init__(self):
        self.config = ConfigParser.RawConfigParser(allow_no_value=True)
        self.configName = 'blueliv.cfg'
        if not os.path.isfile(self.configName):
            open(self.configName, 'a').close()
    
    def setConfigProxy(self,proxy_type,proxy_host,proxy_port, proxy_activated, proxy_needCredentials, proxy_user, proxy_pass):
        self.config.add_section('Proxy')
        self.config.set('Proxy', 'type', proxy_type)
        self.config.set('Proxy', 'host', proxy_host)
        self.config.set('Proxy', 'port', proxy_port)
        self.config.set('Proxy', 'needCredentials', proxy_needCredentials)
        self.config.set('Proxy', 'user', proxy_user)
        self.config.set('Proxy', 'pass', proxy_pass)
        self.config.set('Proxy', 'activated', proxy_activated)
    
    def setConfigAPICredentials(self, APIKey = ''):
        self.config.add_section('API')
        self.config.set('API', 'key', APIKey)
        self.config.set('API', 'url', 'https://api.blueliv.com')
        self.config.set('API', 'updatetime', '3600000')
        self.config.set('API', 'navailableupdates', '24')
        self.config.set('API_BOTS', 'updatetime', '3600000')
        
    def askForConfigs(self):
        while True:
            print ("Do you need a proxy? (0: No, 1: Yes):")
            try:
                proxy=int(raw_input())
                if proxy == 0 or proxy == 1:
                    break
                else:
                    print ("Input must be 0 (NO) or 1 (YES)")
            except ValueError:
                print ("Not a number")
                pass
        
        if proxy == 1:
            print ("Proxy host: (example: 127.0.0.1)")
            proxy_host=raw_input("Proxy Host: ")
            while True:
                print ("Proxy port: (example: 1010)")
                try:
                    proxy_port=int(raw_input("Proxy Port: "))
                    break
                except ValueError:
                    print ("Not a number")
                    pass
            while True:
                print ("Does the proxy need credentials? (0: No, 1: Yes):")
                try:
                    needCredentials=int(raw_input())
                    if needCredentials == 0 or needCredentials == 1:
                        break
                    else:
                        print ("Input must be 0 (NO) or 1 (YES)")
                except ValueError:
                    print ("Not a number")
                    pass
            if needCredentials == 1:
                proxy_user=raw_input("Proxy User: ")
                proxy_pass=raw_input("Proxy Password: ")
                self.setConfigProxy(3,proxy_host,proxy_port,True,True,proxy_user,proxy_pass)
            else:
                self.setConfigProxy(3,proxy_host,proxy_port,True,False,"","")
        else:
            self.setConfigProxy("","","", False, False, "", "")
        api_key=raw_input("API Key: ")
        self.setConfigAPICredentials(api_key)

    def get_last_updated(self):
        update = None
        self.config.read(self.configName)
        if self.config.has_section('Updates'):
            update = self.config.get('Updates', 'last')

        try:
            if self.config.has_section('Actions') and self.config.has_option('Actions','reset'):
                if self.config.getboolean('Actions', 'reset'):
                    update = None
        except:
            pass
        
        return update

    def setLastUpdated(self, updatedAt):
        if self.config.has_section('Updates'):
            self.config.set('Updates', 'last', updatedAt)
        else:
            self.config.add_section('Updates')
            self.config.set('Updates', 'last', updatedAt)

        if self.config.has_section('Actions') and self.config.has_option('Actions','reset'):
            if self.config.getboolean('Actions', 'reset'):
                 self.config.set('Actions', 'reset', False)

        self.writeConfigFile()

    def get_last_updated_bots(self):
        update = None
        self.config.read(self.configName)
        if self.config.has_section('UpdatesBots'):
            update = self.config.get('UpdatesBots', 'last')
        
        return update

    def get_last_updated_attacks(self):
        update = None
        self.config.read(self.configName)
        if self.config.has_section('UpdatesAttacks'):
            update = self.config.get('UpdatesAttacks', 'last')

        return update

    def get_last_updated_malwares(self):
        update = None
        self.config.read(self.configName)
        if self.config.has_section('UpdatesMalwares'):
            update = self.config.get('UpdatesMalwares', 'last')

        return update

    def setLastUpdatedBot(self, updatedAt):
        if self.config.has_section('UpdatesBots'):
            self.config.set('UpdatesBots', 'last', updatedAt)
        else:
            self.config.add_section('UpdatesBots')
            self.config.set('UpdatesBots', 'last', updatedAt)

        self.writeConfigFile()

    def setLastUpdatedAttacks(self, updatedAt):
        if self.config.has_section('UpdatesAttacks'):
            self.config.set('UpdatesAttacks', 'last', updatedAt)
        else:
            self.config.add_section('UpdatesAttacks')
            self.config.set('UpdatesAttacks', 'last', updatedAt)

        self.writeConfigFile()

    def setLastUpdatedMalwares(self, updatedAt):
        if self.config.has_section('UpdatesMalwares'):
            self.config.set('UpdatesMalwares', 'last', updatedAt)
        else:
            self.config.add_section('UpdatesMalwares')
            self.config.set('UpdatesMalwares', 'last', updatedAt)

        self.writeConfigFile()
    
    def writeConfigFile(self):
        with open(self.configName, 'wb') as configfile:
            self.config.write(configfile)
        
    def readProxyConfig(self):
        self.config.read(self.configName)
        if self.config.has_section('Proxy'):
            if self.config.getboolean('Proxy', 'activated'):
                type = 3
                host = self.config.get('Proxy', 'host')
                port = self.config.getint('Proxy', 'port')
                if self.config.getboolean('Proxy', 'needCredentials'):
                    user = self.config.getint('Proxy', 'user')
                    password = self.config.getint('Proxy', 'pass')
                    return Proxy(type,host,port,True,True,user,password)
                else:
                    return Proxy(type,host,port,True,False,"","")
            else:
                return Proxy("","","",False,False,"","")
        else:
            return Proxy("","","",False,False,"","")
    
    def getCredentials(self):
        key = ''
        self.config.read(self.configName)
        if self.config.has_section('API'):
            key = self.config.get('API', 'apikey')
        
        return key

    def get_api_url(self):
        url = 'https://api.blueliv.com'
        self.config.read(self.configName)
        if self.config.has_section('API') and self.config.has_option('API','url'):
            url = self.config.get('API', 'url')
        
        return url

    def get_api_access_type(self):
        access_type = 'FREE'
        self.config.read(self.configName)
        if self.config.has_section('API') and self.config.has_option('API','type'):
            access_type = self.config.get('API', 'type')
        
        return access_type

    def get_update_time(self):
        update_time = 3600000*6
        self.config.read(self.configName)
        if self.config.has_section('API') and self.config.has_option('API','updatetime'):
            try:
                update_time = int(self.config.get('API', 'updatetime'))*60*1000
            except:
                pass
        
        return update_time

    def get_update_time_botips(self):
        update_time = 10*60*1000
        self.config.read(self.configName)
        if self.config.has_section('API_BOTS') and self.config.has_option('API_BOTS','updatetime'):
            try:
                update_time = int(self.config.get('API_BOTS', 'updatetime'))*60*1000
            except:
                pass
        
        return update_time

    def get_update_time_attacks(self):
        update_time = 3 * 60 * 60 * 1000
        self.config.read(self.configName)
        if self.config.has_section('API_ATTACKS') and self.config.has_option('API_ATTACKS', 'updatetime'):
            try:
                update_time = int(self.config.get('API_ATTACKS', 'updatetime')) * 60 * 1000
            except:
                pass

        return update_time

    def get_update_time_malwares(self):
        update_time = 60 * 60 * 1000
        self.config.read(self.configName)
        if self.config.has_section('API_MALWARES') and self.config.has_option('API_MALWARES', 'updatetime'):
            try:
                update_time = int(self.config.get('API_MALWARES', 'updatetime')) * 60 * 1000
            except:
                pass

        return update_time

    def get_available_updates(self):
        available_updates = 24
        self.config.read(self.configName)
        if self.config.has_section('API') and self.config.has_option('API','navailableupdates'):
            try:
                available_updates = int(self.config.get('API', 'navailableupdates'))
            except:
                pass
        
        return available_updates

class Proxy():
    def __init__(self,type,host,port,activated,needCredentials,user,password):
        self.type = type
        self.host = host
        self.port = port
        self.needCredentials = needCredentials
        self.user = user
        self.password = password
        self.activated = activated
    
    def getHost(self):
        return self.host
    
    def getPort(self):
        return self.port
    
    def useCredentials(self):
        return self.needCredentials
    
    def getCredentials(self):
        return self.user, self.password
    
    def getUser(self):
        return self.user
        
    def getPass(self):
        return self.password
    
    def getProxy(self):
        if self.needCredentials:
            return self.user+":"+self.password+"@"+self.host+":"+str(self.port)
        else:
            return self.host+":"+str(self.port)
    
    def getType(self):
        return self.type
    
    def isActivated(self):
        return self.activated

