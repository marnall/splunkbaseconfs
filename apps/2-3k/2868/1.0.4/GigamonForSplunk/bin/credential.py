"""credentialsFromSplunk.py
    Credentials Stored in Splunk Credentials Class file
	https://github.com/georgestarcher/Splunk-Alert/blob/master/credentialsFromSplunk.py

The MIT License (MIT)

Copyright (c) 2014 George Starcher

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

class credential:
    """ Credential object:
        Attributes:
            app: the Splunk app storing the credential
            realm: the system needing the credential
            username: the username for the credential
            password: the credential's password or key
        access the credentials in /servicesNS/nobody/<myapp>/storage/passwords
    """

    def __init__(self, app, realm, username):   
        self.app = app
        self.realm = realm
        self.username = username
        self.password = "" 

    def __str__(self):
        """Function Override: Print credential object
        """
        
        return 'App:%s Realm:%s Username:%s Password:%s\r\n'% (self.app,self.realm,self.username,self.password)

    def getPassword(self, sessionkey):
        import splunk.entity as entity
        import urllib

        if len(sessionkey) == 0:
            raise Exception, "No session key provided"
        if len(self.username) == 0:
            raise Exception, "No username provided"
        if len(self.app) == 0:
            raise Exception, "No app provided"
        
        try:
            entities = entity.getEntities(['admin', 'passwords'], namespace=self.app, owner='nobody', sessionKey=sessionkey)
        except Exception, e:
            raise Exception, "Could not get %s credentials from splunk. Error: %s" % (self.app, str(e))

        for i, c in entities.items():
            if (c['realm'] == self.realm and c['username'] == self.username):
                self.password = c['clear_password']
                return self.password

        raise Exception, "No credentials have been found: SessionKey: %s Username:%s App:%s Realm: %s"%(sessionkey,self.username,self.app,self.realm)
