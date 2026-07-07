import sys
import os
import hashlib
import datetime
import requests
import json

API_URL = "https://statsapi.web.nhl.com/api/v1"

def reqApi(path,url=API_URL):
    full_req = url + path
    try:
        r = requests.get(full_req,timeout=60)
        if r.status_code != 200:
            raise Exception("Received status code" + str(r.status_code))
    except:
        exit("Error making request to: " + full_req)
    return r.text

def handleKVUpdate(helper,key,val):
    try:
        if val is None:
            helper.log_debug = "No KV found for '" + str(key) + "''. setting to: " + str(val) 

        helper.save_check_point(key,val)
    except Exception as e:
        exit(e)

def getGamesToBePlayed(helper,val_date_pointer):
    uri_path = "/schedule?startDate=" + val_date_pointer + "&endDate=" + val_date_pointer
    date_games = []

    resp = reqApi(uri_path)
    jScores = json.loads(resp)
    allDates = jScores["dates"]
    for gDate in allDates:
        for game in gDate["games"]:
            date_games.append(game['gamePk'])

    return date_games

def incrementDatePointer(helper,key,val):
    try:
        next_day = datetime.datetime.strptime(val,'%Y-%m-%d') + datetime.timedelta(hours=24)
        next_day_str = str(next_day.strftime('%Y-%m-%d'))
        handleKVUpdate(helper,key,next_day_str)

    except Exception as e:
        print(e)
        exit(e)

def pullScoresById(helper,ew,gamePk,bDetail=1):
    endpoint = "/game/%s/feed/live" % str(gamePk)
    resp = reqApi(endpoint)
    gamesCompleted = ingestGame(helper,ew,resp,bDetail)
    return gamesCompleted

def ingestGame(helper,ew,resp,bDetail):
    jGame = json.loads(resp)
    if jGame["gameData"]["status"]["codedGameState"] not in ["7","6"]:
        return None
    
    # Game Data
    gDate = jGame["gameData"]["datetime"]["dateTime"]
    seasonId = str(jGame["gameData"]["game"]["season"])
    gType = jGame["gameData"]["game"]["type"]
    gId = jGame["gameData"]["game"]["pk"]

    gState = str(jGame["gameData"]["status"]["codedGameState"])

    gLast = jGame["liveData"]["linescore"]["currentPeriod"]
    gSH ="F"
    gOT = "F"
    gWinner = ""
    gLoser = ""

    if gLast==5:
        gSH = "T"
        gOT = "T"
    elif gLast==4:
        gSH = "F"
        gOT = "T"
    
    # Teams and Scores
    gHId = jGame["gameData"]["teams"]["home"]["id"]
    gHTeam = jGame["gameData"]["teams"]["home"]["name"]
    gHScore = jGame["liveData"]["linescore"]["teams"]["home"]["goals"]
    gHSOG = jGame["liveData"]["linescore"]["teams"]["home"]["shotsOnGoal"]

    gAId = jGame["gameData"]["teams"]["away"]["id"]
    gATeam = jGame["gameData"]["teams"]["away"]["name"]
    gAScore = jGame["liveData"]["linescore"]["teams"]["away"]["goals"]
    gASOG = jGame["liveData"]["linescore"]["teams"]["away"]["shotsOnGoal"]

    
    if int(gAScore)<int(gHScore):
        gWinner = gHId
        gLoser = gAId
    elif int(gAScore)>int(gHScore):
        gWinner = gAId
        gLoser = gHId
    else:
        gWinner = -1
        gLoser = -1

    game_event = "%s FEED_TYPE=\"Scores\" SEASON_ID=\"%s\" GAME_TYPE=\"%s\" GAME_ID=\"%d\" HOME_TEAM_ID=\"%d\" HOME_TEAM_NAME=\"%s\" HOME_TEAM_SCORE=\"%d\" HOME_TEAM_SOG=\"%d\" AWAY_TEAM_ID=\"%d\" AWAY_TEAM_NAME=\"%s\" AWAY_TEAM_SCORE=\"%d\" AWAY_TEAM_SOG=\"%d\" OVER_TIME=\"%s\" SHOOT_OUT=\"%s\" WINNER_TEAM_ID=\"%d\" LOSER_TEAM_ID=\"%d\"" \
                    % (gDate,seasonId,gType, gId, gHId, gHTeam, gHScore, gHSOG, gAId, gATeam, gAScore, gASOG,gOT,gSH, gWinner, gLoser)

    event = helper.new_event(game_event,index=helper.get_output_index(), sourcetype="hockey:score")
    ew.write_event(event)

    if bDetail == 1:
        acceptedEventTypes = ["Faceoff","MissedShot","Hit","Goal","Takeaway","BlockedShot","Shot","Giveaway","Penalty", \
                                "FACEOFF","MISSED_SHOT","HIT","GOAL","TAKEAWAY","SHOT","BLOCKED_SHOT","GIVEAWAY","PENALTY"]
        
        ignoreEventTypes = ["GameScheduled","PeriodReady","PeriodStart","Stop","PeriodEnd", \
                            "PeriodOfficial","GameEnd","ShootoutComplete","EarlyIntEnd","EarlyIntStart", \
                            "EmergencyGoaltender","GameOfficial","Challenge","PeriodOfficial","PeroidEnd", \
                            "PeroidReady","GAME_END","PERIOD_OFFICIAL","PERIOD_END","GAME_SCHEDULED","PERIOD_READY", \
                            "PERIOD_START","STOP","PERIOD_END","PERIOD_OFFICIAL","GAME_END","SHOOTOUT_COMPLETE", \
                            "EARLY_INT_END","EARLY_INT_START","EMERGENCY_GOALTENDER","GAME_OFFICIAL","CHALLENGE"]
        for play in jGame["liveData"]["plays"]["allPlays"]:
            detail_msg = ""
            msg = ""

            dTime = str(play["about"]["dateTime"])
            dPeriod = play["about"]["period"]
            dEventType = str(play["result"]["eventTypeId"]).replace("gamecenter","")
            dId = play["about"]["eventId"]

            try:
                dXCoord = play["coordinates"]["x"]
                dYCoord = play["coordinates"]["y"]
            except:
                dXCoord = -1
                dYCoord = -1

            try:
                if play["team"] is not None:
                    dTeamId = play["team"]["id"]
                    dTeamName = str(play["team"]["name"])
            except:
                dTeamId = -1
                dTeamName = "N/A"

            dDescription = str(play["result"]["description"])

            if dEventType not in acceptedEventTypes and dEventType not in ignoreEventTypes:
                msg = " NOT FOUND EVENT_TYPE=%s" % (str(play["result"]["eventTypeId"] ))
            elif dEventType in ignoreEventTypes:
                continue
            elif dEventType == "Faceoff" or dEventType == "FACEOFF":
                dFWinnerId = -1
                dFLoserId = -1
                dFWinnerName = ""
                dFLoserName = ""
                for player in play["players"]:
                    if player["playerType"] == "Winner":
                        dFWinnerId = player["player"]["id"]
                        dFWinnerName = player["player"]["fullName"]
                    elif player["playerType"] == "Loser":
                        dFLoserId = player["player"]["id"]
                        dFLoserName = player["player"]["fullName"]

                msg = " FACEOFF_WINNER_ID=\"%d\" FACEOFF_WINNER_NAME=\"%s\" FACEOFF_LOSER_ID=\"%d\" FACEOFF_LOSER_NAME=\"%s\"" % (dFWinnerId, dFWinnerName, dFLoserId, dFLoserName)

            elif dEventType == "Hit" or dEventType == "HIT":
                dHitterId = -1
                dHitteeId = -1
                dHitterName = ""
                dHitteeName = ""

                for player in play["players"]:
                    if player["playerType"] == "Hitter":
                        dHitterId = player["player"]["id"]
                        dHitterName = player["player"]["fullName"]
                    elif player["playerType"] == "Hittee":
                        dHitteeId = player["player"]["id"]
                        dHitteeName = player["player"]["fullName"]

                msg = " HITTER_ID=\"%d\" HITTER_NAME=\"%s\" HITTEE_ID=\"%d\" HITTEE_NAME=\"%s\"" % (dHitterId, dHitterName, dHitteeId, dHitteeName)

            elif dEventType == "MissedShot" or dEventType=="MISSED_SHOT":
                dMShooterId = play["players"][0]["player"]["id"]
                dMShooterName = play["players"][0]["player"]["fullName"]
                msg = " SHOOTER_ID=\"%d\" SHOOTER_NAME=\"%s\"" % (dMShooterId, dMShooterName)

            elif dEventType == "Takeaway" or dEventType=="TAKEAWAY":
                dTakeId = play["players"][0]["player"]["id"]
                dTakeName = play["players"][0]["player"]["fullName"]
                msg = " TAKEAWAY_PLAYER_ID=\"%d\" TAKEAWAY_PLAYER_NAME=\"%s\"" % (dTakeId, dTakeName)

            elif dEventType == "Shot" or dEventType=="SHOT":
                dShooterId = -1
                dShooterName = ""
                dGoalieId = -1
                dGoalieName = ""
                try:
                    dShotType = str(play["result"]["secondaryType"])
                except:
                    dShotType = "Unknown"

                for player in play["players"]:
                    if player["playerType"] == "Shooter":
                        dShooterId = player["player"]["id"]
                        dShooterName = player["player"]["fullName"]
                    elif player["playerType"] == "Goalie":
                        dGoalieId = player["player"]["id"]
                        dGoalieName = player["player"]["fullName"]

                msg = " SHOT_TYPE=\"%s\" SHOOTER_ID=\"%d\" SHOOTER_NAME=\"%s\" GOALIE_ID=\"%d\" GOALIE_NAME=\"%s\"" % (dShotType, dShooterId, dShooterName, dGoalieId, dGoalieName)

            elif dEventType == "BlockedShot" or dEventType=="BLOCKED_SHOT":
                dBShooterId = -1
                dBShooterName = ""
                dBShooterTeamId = -1
                dBBlockerId = -1
                dBBlockerName = ""

                for player in play["players"]:
                    if player["playerType"] == "Shooter":
                        dBShooterId = player["player"]["id"]
                        dBShooterName = player["player"]["fullName"]
                    if player["playerType"] == "Blocker":
                        dBBlockerId = player["player"]["id"]
                        dBBlockerName = player["player"]["fullName"]
                if gHId == dTeamId:
                    dBShooterTeamId = gAId
                else:
                    dBShooterTeamId = gHId

                msg = " SHOOTER_TEAM_ID=\"%d\" SHOOTER_ID=\"%d\" SHOOTER_NAME=\"%s\" BLOCKER_ID=\"%d\" BLOCKER_NAME=\"%s\"" % (dBShooterTeamId,dBShooterId, dBShooterName, dBBlockerId, dBBlockerName)
            elif dEventType == "Goal" or dEventType=="GOAL":
                dGScorerId = -1
                dGScorerName = ""
                dGAssistId_1 = -1
                dGAssistName_1 = ""
                dGAssistId_2 = -1
                dGAssistName_2 = ""

                try:
                    dGStrength = str(play["result"]["strength"]["code"])
                except:
                    dGStrength = "N/A"

                try:
                    dGShotType = str(play["result"]["secondaryType"])
                except:
                    dGShotType = "N/A"

                for player in play["players"]:
                    if player["playerType"] == "Scorer":
                        dGScorerId = player["player"]["id"]
                        dGScorerName = player["player"]["fullName"]
                    elif player["playerType"] == "Assist":
                        if dGAssistId_1 == -1:
                            dGAssistId_1 = player["player"]["id"]
                            dGAssistName_1 = player["player"]["fullName"]
                        else:
                            dGAssistId_2 = player["player"]["id"]
                            dGAssistName_2 = player["player"]["fullName"]

                msg = " STRENGTH=\"%s\" SCORER_ID=\"%d\" SCORER_NAME=\"%s\"" % (dGStrength,dGScorerId, dGScorerName)
                if dGAssistId_1 is not None or dGAssistId_1 != -1:
                    msg += " ASSIST_ID_1=\"%d\" ASSIST_NAME_1=\"%s\"" % (dGAssistId_1,dGAssistName_1)                    
                if dGAssistId_2 is not None or dGAssistId_2 != -1:
                    msg += " ASSIST_ID_2=\"%d\" ASSIST_NAME_2=\"%s\"" % (dGAssistId_2,dGAssistName_2)

            elif dEventType == "Giveaway" or dEventType=="GIVEAWAY":
                dGiveId = play["players"][0]["player"]["id"]
                dGiveName = play["players"][0]["player"]["fullName"]
                msg = " GIVEAWAY_PLAYER_ID=\"%d\" GIVEAWAY_PLAYER_NAME=\"%s\"" % (dGiveId, dGiveName)
            elif dEventType == "Penalty" or dEventType=="PENALTY":
                
                dPenOnId = -1
                dPenOnName = ""
                dPenDrewId = -1
                dPenDrewName = ""
                dPenServeId = -1
                dPenServeName = ""
                dPenTeam = ""
                try:
                    for player in play["players"]:
                        if player["playerType"] == "PenaltyOn":
                            dPenOnId = player["player"]["id"]
                            dPenOnName = str(player["player"]["fullName"])
                        elif player["playerType"] == "DrewBy":
                            dPenDrewId = player["player"]["id"]
                            dPenDrewName = str(player["player"]["fullName"])
                        elif player["playerType"] == "ServedBy":
                            dPenServeId = player["player"]["id"]
                            dPenServeName = str(player["player"]["fullName"])
                except:
                    if str(play["result"]["secondaryType"]) == "Too many men on the ice":
                        dPenOnId = dTeamId
                        dPenOnName = dTeamName
                    else:
                        pass

                dPenType = str(play["result"]["secondaryType"])
                msg = " PENALTY_TYPE=\"%s\" PENALTY_ON_ID=\"%d\" PENALTY_ON_NAME=\"%s\"" % (dPenType,dPenOnId,dPenOnName)
                if dPenDrewId != -1:
                    msg += " PENALTY_DREWBY_ID=\"%d\" PENALTY_DREWBY_NAME=\"%s\"" % (dPenDrewId,dPenDrewName)
                if dPenServeId != -1:
                    msg += " PENALTY_SERVEDBY_ID=\"%d\" PENALTY_SERVEDBY_NAME=\"%s\"" % (dPenServeId,dPenServeName)

            detail_msg = "%s FEED_TYPE=\"Detailed Event\" SEASON_ID=\"%s\" GAME_ID=\"%d\" GAME_TYPE=\"%s\" PERIOD=\"%d\" EVENT_ID=\"%d\" EVENT_TYPE=\"%s\" X_COORD=\"%d\" Y_COORD=\"%d\" TEAM_ID=\"%d\" TEAM_NAME=\"%s\" EVENT_DESCRIPTION=\"%s\"" % (dTime,seasonId,gId,gType,dPeriod,dId,dEventType,dXCoord,dYCoord,dTeamId,dTeamName,dDescription)

            detail_msg += msg
            detail_event = helper.new_event(detail_msg,index=helper.get_output_index(), sourcetype="hockey:event")
            ew.write_event(detail_event)
        
    return jGame['gamePk']


def hwCollect(helper,ew):
    helper.set_log_level(helper.get_log_level())
    helper.log_debug("Collecting...")

    # Get KV keys
    opt_start_date      = helper.get_arg('start_date')
    opt_input_name      = helper.get_input_stanza_names()
    checkpoint_md5      = hashlib.md5()
    checkpoint_md5.update(opt_input_name)
    key                 = checkpoint_md5.hexdigest()
    key_date_pointer    = key + "__date_pointer"
    key_games_finished  = key + "__games_finished"
    key_date_games      = key + "__date_games"

    # Get KV values
    helper.log_debug("Getting initial pointers")
    val_date_pointer    = helper.get_check_point(key_date_pointer)
    val_games_finished  = helper.get_check_point(key_games_finished)
    val_date_games      = helper.get_check_point(key_date_games)
    helper.log_debug("completed initial pointers")

    log_level           = helper.get_log_level()
    current_date        = str(datetime.date.today())

    # If values are null, initialize them
    

    if val_date_pointer is None or "[]" in val_date_pointer:
        handleKVUpdate(helper,key_date_pointer,opt_start_date)
        val_date_pointer = helper.get_check_point(key_date_pointer)
    else:
        helper.log_debug("Value found for date_pointer: " + str(val_date_pointer))

    if val_date_games is None:
        helper.log_debug("No games for day found, updating to date: " + opt_start_date)
        val_date_games = getGamesToBePlayed(helper,opt_start_date)
        handleKVUpdate(helper,key_date_games,val_date_games)
    else:
        helper.log_debug("Value found for date_games: " + str(val_date_games))

    if val_games_finished is None:
        handleKVUpdate(helper,key_games_finished,val_games_finished)
        val_games_finished = helper.get_check_point(key_games_finished)
    else:
        helper.log_debug("Value found for games_finished: " + str(val_games_finished))

    # Ingestion loop, while date is current
    hasRun = False
    while val_date_pointer <= current_date:
        # Update variables
        val_date_pointer    = helper.get_check_point(key_date_pointer)
        val_games_finished  = helper.get_check_point(key_games_finished)

        # if no games are finished
        games_finished      = val_games_finished
        if games_finished is None:
            games_finished = []
            

        val_date_games      = helper.get_check_point(key_date_games)
    
        # If all games are ingested for the current day, update kv store
        if len(games_finished) == len(val_date_games):
            incrementDatePointer(helper,key_date_pointer,val_date_pointer)
            val_date_pointer = helper.get_check_point(key_date_pointer)
            new_games = getGamesToBePlayed(helper,helper.get_check_point(key_date_pointer))
            handleKVUpdate(helper,key_date_games,new_games)
            handleKVUpdate(helper,key_games_finished,None)

        # If there are games left to ingest, check for completed games
        elif len(games_finished) < len(val_date_games):

            # Get game IDs which have yet to be ingested
            games_not_completed = list(set(val_date_games)-set(games_finished))
     
            # For each of those games, attempt to ingest and update KV.
            for game in games_not_completed:
                if pullScoresById(helper,ew,game) is None:
                    continue
                else:
                    games_finished.append(int(game))
            
            # Update games_finished value with any new completed game IDs
            handleKVUpdate(helper,key_games_finished,games_finished)

        if val_date_pointer == current_date and hasRun==False:
            hasRun = True
            continue
        elif val_date_pointer == current_date and hasRun==True:
            sys.exit()

