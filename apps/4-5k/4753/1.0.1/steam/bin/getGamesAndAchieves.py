
import requests as r, json as j, datetime, sys, os
from splunk.clilib import cli_common as cli
from HTMLParser import HTMLParser; h = HTMLParser()

def getAuth(key):
    endpoint = 'https://localhost:8089/servicesNS/nobody/' + app + '/storage/passwords/:steamAPI:'
    head = {'Authorization':''}
    head['Authorization'] = 'Splunk ' + key
    response = r.get( endpoint, headers=head, verify=False )
    start    = response.text.find( 'clear_password' )
    start    = start + 16
    end      = response.text.find( '</s:key>', start )
    clear    = response.text[start:end]
    purty    = h.unescape(clear);
    return purty

def getIntegrationDetails(stanza):
    whereAmI    = os.path.dirname(os.path.dirname(__file__))
    defaultPath = os.path.join(whereAmI, "default", "steam.conf")
    defaultConf = cli.readConfFile(defaultPath)
    localPath   = os.path.join(whereAmI, "local", "steam.conf")
    if os.path.exists(localPath):
       localConf = cli.readConfFile(localPath)
       for name, content in localConf.items():
           if name in defaultConf:
              defaultConf[name].update(content)
           else:
              defaultConf[name] = content
    return defaultConf[stanza]

def log(msg):
    f = open(os.path.join(os.environ["SPLUNK_HOME"], "etc", "apps", app, "log", "getGamesAndAchieves.log"), "a")
    print >> f, '\n', str(datetime.datetime.now().isoformat()), msg
    f.close()

now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
app = 'steam'
raw = sys.stdin.read()
key = getAuth(raw)
who = getIntegrationDetails('userNames')
who = str(who)
who = j.loads(who.replace("'", '"'))
who = who['userNames'].split(',');

#log('- STDIN was:   ' + raw)
#log('- API KEY was: ' + key)
#log('- STANZA was:  ' + str(who))
#log('- USERS were:  ' + str(who))

for id in who:
      user = id
      name = user
      endpointID = 'http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key=' + key + '&vanityurl=' + user
      rawID = r.get(endpointID)
      if rawID.status_code == 200:
         if 'steamid' in rawID.text:
            jsonID = j.loads(rawID.text)
            user   = jsonID['response']['steamid']
      endpointSummary = 'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key=' + key + '&steamids=' + user
      rawSummary = r.get(endpointSummary)
      jsonSummary = j.loads(rawSummary.text)
      endpointRecent='http://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/?key=' + key + '&steamid=' + user
      rawRecent = r.get(endpointRecent)
      jsonRecent = j.loads(rawRecent.text)
      endpointGames = 'http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key=' + key + '&steamid=' + user + '&include_appinfo=true'
      rawGames = r.get(endpointGames)
      jsonGames = j.loads(rawGames.text)
      idxGames = 0
      while idxGames < len(jsonGames['response']['games']):
            gameEvent = ''
            gameEvent = gameEvent + 'Event_Time="' + now + '"'
            gameEvent = gameEvent + ' User_ID=' + user
            gameEvent = gameEvent + ' User_Name=' + name
            gameEvent = gameEvent + ' User_Persona=' + jsonSummary['response']['players'][0]['personaname']
            gameEvent = gameEvent + ' User_Last_Logoff=' + str(jsonSummary['response']['players'][0]['lastlogoff'])
            gameEvent = gameEvent + ' User_URL_Profile=' + jsonSummary['response']['players'][0]['profileurl']
            gameEvent = gameEvent + ' User_URL_Avatar_Small=' + jsonSummary['response']['players'][0]['avatar']
            gameEvent = gameEvent + ' User_URL_Avatar_Medium=' + jsonSummary['response']['players'][0]['avatarmedium']
            gameEvent = gameEvent + ' User_Created=' + str(jsonSummary['response']['players'][0]['timecreated'])
            if 'realname' in jsonSummary['response']['players'][0]:
               gameEvent = gameEvent + ' User_Name_Real=' + jsonSummary['response']['players'][0]['realname']
            if 'loccountrycode' in jsonSummary['response']['players'][0]:
               gameEvent = gameEvent + ' User_Country=' + jsonSummary['response']['players'][0]['loccountrycode']
            gameEvent = gameEvent + ' Game_ID=' + str(jsonGames['response']['games'][idxGames]['appid'])
            gameEvent = gameEvent + ' Game_Name="' + jsonGames['response']['games'][idxGames]['name'] + '"'
            gameEvent = gameEvent + ' Game_Minutes_Played_All_Time=' + str(jsonGames['response']['games'][idxGames]['playtime_forever'])
            if 'games' in jsonRecent['response']:
               if jsonGames['response']['games'][idxGames]['name'] in str(jsonRecent['response']['games']):
                  for game in jsonRecent['response']['games']:
                      if jsonGames['response']['games'][idxGames]['name'] in str(game):
                         gameEvent = gameEvent + ' Game_Minutes_Played_Two_Weeks=' + str(game['playtime_2weeks'])
               else:
                  gameEvent = gameEvent + ' Game_Minutes_Played_Two_Weeks=0'
            else:
               gameEvent = gameEvent + ' Game_Minutes_Played_Two_Weeks=0'
            gameEvent = gameEvent + ' Game_URL_Icon=' + jsonGames['response']['games'][idxGames]['img_icon_url']
            gameEvent = gameEvent + ' Game_URL_Logo=' + jsonGames['response']['games'][idxGames]['img_logo_url']
            achievesAvail = 0
            achievesAchieved = 0
            achievesAchievedNames = '"'
            if jsonGames['response']['games'][idxGames]['playtime_forever'] > 0:
               endpointAchieve = 'http://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/?appid=' + str(jsonGames['response']['games'][idxGames]['appid']) + '&key=' + key + '&steamid=' + user
               rawAchieves = r.get(endpointAchieve)
               if rawAchieves.status_code == 200 and 'achievements' in rawAchieves.text:
                  jsonAchieves = j.loads(rawAchieves.text)
                  idxAchieves = 0
                  achievesAvail = len(jsonAchieves['playerstats']['achievements'])
                  while idxAchieves < achievesAvail:
                        if jsonAchieves['playerstats']['achievements'][idxAchieves]['achieved'] == 1:
                           achievesAchieved += 1
                           achievesAchievedNames = achievesAchievedNames + jsonAchieves['playerstats']['achievements'][idxAchieves]['apiname'] + ':' + str(jsonAchieves['playerstats']['achievements'][idxAchieves]['unlocktime']) + ','
                        idxAchieves += 1
            gameEvent = gameEvent + ' Achievements_Available=' + str(achievesAvail)
            gameEvent = gameEvent + ' Achievements_Achieved=' + str(achievesAchieved)
            if achievesAchievedNames != '"':
               gameEvent = gameEvent + ' Achievements_Names=' + achievesAchievedNames[0:-1] + '"'
            else:
               gameEvent = gameEvent + ' Achievements_Names=None'
            print(str(gameEvent))
            idxGames += 1
# Thanks for playing!

