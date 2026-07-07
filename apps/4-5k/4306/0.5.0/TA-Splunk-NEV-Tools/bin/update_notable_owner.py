import os, splunk.Intersplunk,splunk.rest, logging as logger, json

def updateNotableEvents(sessionKey, comment, status=None, urgency=None, owner=None, eventIDs=None, searchID=None):
    """
    Update some notable events.

    Arguments:
    sessionKey -- The session key to use
    comment -- A description of the change or some information about the notable events
    status -- A status (only required if you are changing the status of the event)
    urgency -- An urgency (only required if you are changing the urgency of the event)
    owner -- A nowner (only required if reassigning the event)
    eventIDs -- A list of notable event IDs (must be provided if a search ID is not provided)
    searchID -- An ID of a search. All of the events associated with this search will be modified unless a list of eventIDs are provided that limit the scope to a sub-set of the results.
    """
    try :
        # Make sure that the session ID was provided
        if sessionKey is None:
            raise Exception("A session key was not provided")

        # Make sure that rule IDs and/or a search ID is provided
        if eventIDs is None and searchID is None:
            raise Exception("Either eventIDs of a searchID must be provided (or both)")
            return False

        # These the arguments to the REST handler
        args = {}
        args['comment'] = comment

        if status is not None:
            args['status'] = status

        if urgency is not None:
            args['urgency'] = urgency

        if owner is not None:
            args['newOwner'] = owner

        # Provide the list of event IDs that you want to change:
        if eventIDs is not None:
            args['ruleUIDs'] = eventIDs

        # If you want to manipulate the notable events returned by a search then include the search ID
        if searchID is not None:
            args['searchID'] = searchID

        # Perform the request
        serverResponse, serverContent = splunk.rest.simpleRequest('/services/notable_update', sessionKey=sessionKey,
                                                                  postargs=args)

        # Make sure the request was successful
        if serverResponse['status'] != '200':
            raise Exception("Error Running Command %s" % serverContent)
            return False

        if serverResponse['status'] == '400':
            raise Exception("Error Running Command %s" % serverContent)
            return False
        # Return the information about the request
        response_info = json.loads(serverContent)
    except Exception, e:
        raise Exception("Error Running Command %s" % e)
        return False
    return response_info


def run_command():
    try:
        keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
        results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
        sessionKey = settings.get("sessionKey")
        outputField = "status"
        eventIDField = options.get('eventIDField', "event_id")
        newOwnerField = options.get('newOwnerField', None)
        newOwnerValueInputTime = options.get('newOwner', None)
       
        num_keywords = len(keywords)
        #if num_keywords < 2:
            #return splunk.Intersplunk.generateErrorResults("Need to an input Event ID Field and new owner for event")

        #if num_keywords > 2:
            #return splunk.Intersplunk.generateErrorResults("Too many arugments provided")

        if results:
            eventIDList = []
            for result in results:
                #Bundle up ID Values
                if (newOwnerField is None):
                    newOwnerValue = newOwnerValueInputTime
                else:
                    newOwnerValue = result[newOwnerField]
                    if (newOwnerValue is None):
                        raise Exception("Error Unable to determine user with newOwneValue as %s and NewOwnerValueField as %s" % {newOwnerValue,newOwnerField})
                        return False
                result[outputField] = updateNotableEvents(sessionKey,"Auto Updating Notable Event Owner",eventIDs=result[eventIDField], owner=newOwnerValue)
    
        splunk.Intersplunk.outputResults(results)

    except Exception, e:
        import traceback
        stack = traceback.format_exc()
        splunk.Intersplunk.generateErrorResults(str(e))


run_command()
