"""
A Python library for accessing the FitBit API.
This library provides a wrapper to the FitBit API and does not provide storage of tokens or caching if that is required.
Most of the code has been adapted from: https://groups.google.com/group/fitbit-api/browse_thread/thread/0a45d0ebed3ebccb
5/22/2012 - JCF - Updated to work with python-oauth2 https://github.com/dgouldin/python-oauth2
10/22/2015 - JG - Removed use of oauth2 library (signing is not necessary anymore),
                  updated to use /oauth2/ authentication infrastructure to get access to more stats.
12/26/2015 - JB - Modified to receive config file parameters, and updated API call function to fit Splunk requirements.
                  Added refresh and access token write to file. Added CherryPy verifier to make OAuth access easier.
                  Added Intraday Time Series function. Added Token File gathering to clean up worker files code.
"""
import sys, os, base64
import datetime as dt
import ConfigParser
import requests, urllib
import cherrypy, threading
import json

# Setup Splunk Environment
APPNAME = 'TA-fitbit'
CONFIG = 'appconfig.conf'
SPLUNK_HOME = os.environ['SPLUNK_HOME']
TOKEN_CONFIG = '/bin/user_settings.txt'

#dynamically load in any eggs in /etc/apps/TA-fitbit/bin
EGG_DIR = SPLUNK_HOME + "/etc/apps/" + APPNAME + "/bin/"

for filename in os.listdir(EGG_DIR):
    if filename.endswith(".egg"):
        sys.path.append(EGG_DIR + filename)


tokenfile = SPLUNK_HOME + '/etc/apps/' + APPNAME + TOKEN_CONFIG

parser = ConfigParser.SafeConfigParser()

class Fitbit():

    # All information must be as on the https://dev.fitbit.com/apps page.
    # Load Settings
    parser.read(SPLUNK_HOME + '/etc/apps/' + APPNAME + '/local/' + CONFIG)
    if parser.has_section('Authentication'):
        pass
    else:
        parser.read(SPLUNK_HOME + '/etc/apps/' + APPNAME + '/default/' + CONFIG)

    CLIENT_ID = parser.get('Authentication', 'C_KEY')
    CLIENT_SECRET = parser.get('Authentication', 'C_SECRET')
    REDIRECT_URI  = parser.get('Authentication', 'REDIRECT_URI')

    # Decide which information the FitBit.py should have access to.
    # Options: 'activity', 'heartrate', 'location', 'nutrition',
    #          'profile', 'settings', 'sleep', 'social', 'weight'
    API_SCOPES    = ('activity', 'heartrate', 'location', 'nutrition', 'profile', 'settings', 'sleep', 'social', 'weight')

    # These settings should probably not be changed.
    API_SERVER    = 'api.fitbit.com'
    WWW_SERVER    = 'www.fitbit.com'
    AUTHORIZE_URL = 'https://%s/oauth2/authorize' % WWW_SERVER
    TOKEN_URL     = 'https://%s/oauth2/token' % API_SERVER

    def GetAuthorizationUri(self):

        # Parameters for authorization, make sure to select
        params = {
            'client_id': self.CLIENT_ID,
            'response_type':  'code',
            'scope': ' '.join(self.API_SCOPES),
            'redirect_uri': self.REDIRECT_URI
        }

        # Encode parameters and construct authorization url to be returned to user.
        urlparams = urllib.urlencode(params)
        return "%s?%s" % (self.AUTHORIZE_URL, urlparams)

    # Tokes are requested based on access code. Access code must be fresh (10 minutes)
    def GetAccessToken(self, access_code):

        # Construct the authentication header
        auth_header = base64.b64encode(self.CLIENT_ID + ':' + self.CLIENT_SECRET)
        headers = {
            'Authorization': 'Basic %s' % auth_header,
            'Content-Type' : 'application/x-www-form-urlencoded'
        }

        # Parameters for requesting tokens (auth + refresh)
        params = {
            'code': access_code,
            'grant_type': 'authorization_code',
            'client_id': self.CLIENT_ID,
            'redirect_uri': self.REDIRECT_URI
        }

        # Place request
        resp = requests.post(self.TOKEN_URL, data=params, headers=headers)
        status_code = resp.status_code
        resp = resp.json()

        if status_code != 200:
            raise Exception("Something went wrong exchanging code for token (%s): %s" % (resp['errors'][0]['errorType'], resp['errors'][0]['message']))

        # Strip the goodies
        token = dict()
        token['access_token']  = resp['access_token']
        token['refresh_token'] = resp['refresh_token']

        return token

    # Get new tokens based if authentication token is expired
    def RefAccessToken(self, token):

        # Construct the authentication header
        auth_header = base64.b64encode(self.CLIENT_ID + ':' + self.CLIENT_SECRET)
        headers = {
            'Authorization': 'Basic %s' % auth_header,
            'Content-Type' : 'application/x-www-form-urlencoded'
        }

        # Set up parameters for refresh request
        params = {
            'grant_type': 'refresh_token',
            'refresh_token': token['refresh_token']
        }

        # Place request
        resp = requests.post(self.TOKEN_URL, data=params, headers=headers)

        status_code = resp.status_code
        resp = resp.json()

        if status_code != 200:
            raise Exception("Something went wrong refreshing (%s): %s" % (resp['errors'][0]['errorType'], resp['errors'][0]['message']))

        # Distil
        token['access_token']  = resp['access_token']
        token['refresh_token'] = resp['refresh_token']

        return token

    # Place api call to retrieve data
    def ApiCall(self, token, apiCall='/1/user/-/activities/log/steps/date/today/1d.json'):
        # Other API Calls possible, or read the FitBit documentation for the full list
        # (https://dev.fitbit.com/docs/), e.g.:
        # apiCall = '/1/user/-/devices.json'
        # apiCall = '/1/user/-/profile.json'
        # apiCall = '/1/user/-/activities/date/2015-10-22.json'

        headers = {
            'Authorization': 'Bearer %s' % token['access_token']
        }

        final_url = 'https://' + self.API_SERVER + apiCall

        resp = requests.get(final_url, headers=headers)

        status_code = resp.status_code

        resp = resp.json()
        resp['token'] = token

        if status_code == 200:
            return resp
        elif status_code == 401:
            # print "The access token you provided has been expired let me refresh that for you."
            # Refresh the access token with the refresh token if expired. Access tokens should be good for 1 hour.
            token = self.RefAccessToken(token)
            json.dump(token, open(tokenfile, 'w'))
            self.ApiCall(token, apiCall)
        else:
            raise Exception("Something went wrong requesting (%s): %s" % (resp['errors'][0]['errorType'], resp['errors'][0]['message']))

    # CherryPy to facilitate user interaction
    @cherrypy.expose
    def index(self, code=None):
        if code:
            def query():
                yield "Copy this code into the access_generator utility: "
                yield cherrypy.request.params.get('code', None)
        self._shutdown_cherrypy()
        return query()
    index.exposed = True

    def _shutdown_cherrypy(self):
        """ Shutdown cherrypy in one second, if it's running """
        if cherrypy.engine.state == cherrypy.engine.states.STARTED:
            threading.Timer(1, cherrypy.engine.exit).start()

    def ReadToken(self):
        try:
            token = json.load(open(tokenfile))
        except IOError:
            print "Error retrieving access token. Please rerun provided access_generator.py!"
            auth_url = fit.GetAuthorizationUri()
            print "Please visit the link below and approve the app:\n %s" % auth_url
            # Set the access code that is part of the arguments of the callback URL FitBit redirects to.
            access_code = raw_input("Please enter code (from the URL you were redirected to): ")
            # Use the temporary access code to obtain a more permanent pair of tokens
            token = fit.GetAccessToken(access_code)
            # Save the token to a file
            json.dump(token, open(tokenfile,'w'))
        return token

    def TimeSeries(self, endpoint):
        if parser.has_section(endpoint):
            pass
        else:
            parser.read(SPLUNK_HOME + '/etc/apps/' + APPNAME + '/default/' + CONFIG)

        date_interval = parser.get(endpoint, 'DATE_INTERVAL')
        time_interval = parser.get(endpoint, 'TIME_INTERVAL')
        time_delay = parser.get(endpoint, 'TIME_DELAY')

        # Create start time and end time for api call
        delay = int(time_delay)
        now = dt.datetime.now()
        delta = dt.timedelta(minutes=delay)
        t = now.time()
        end_time = (t.strftime('%H:%M'))

        # Subtract x minutes from start time to provide end time
        start_time = ((dt.datetime.combine(dt.date(1, 1, 1), t) + delta).time().strftime('%H:%M'))

        time_series = {'DATE': date_interval, 'TIME': time_interval, 'START': start_time, 'END': end_time }

        return time_series
