import splunk
import json


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

    # If you want to manipulate the notable events returned by a search then
    # include the search ID
    if searchID is not None:
        args['searchID'] = searchID

    # Perform the request
    serverResponse, serverContent = splunk.rest.simpleRequest('/services/notable_update', sessionKey=sessionKey, postargs=args)

    # Make sure the request was successful
    if serverResponse['status'] != '200':
        raise Exception("Server response indicates that the request failed")

    # Return the information about the request
    response_info = json.loads(serverContent)
    return response_info


if __name__ == "__main__":

    #
    # Get a session ID and make a function for outputting the results for the examples below
    #
    import splunk.entity as entity
    from splunk import auth
    import sys

    print("username: %s" % str(sys.argv[1]))
    print("password: %s" % str(sys.argv[2]))
    print("hostPath: %s" % str(sys.argv[3]))
    print("eventId: %s" % str(sys.argv[4]))
    print("comment: %s" % str(sys.argv[5]))
    print("tag: %s" % str(sys.argv[6]))
    print("status: %s" % str(sys.argv[7]))

    username = str(sys.argv[1])
    password = str(sys.argv[2])
    hostPath = str(sys.argv[3])
    eventIDs = [str(sys.argv[4])]
    comment = str(sys.argv[5])
    tag = str(sys.argv[6])
    status = str(sys.argv[7])

    # sessionKey = auth.getSessionKey(username='admin', password='changeme')
    sessionKey = auth.getSessionKey(username=username, password=password, hostPath=hostPath)

    def printResultMessage(response_info):

        if not response_info['success']:
            print "The operation was not successful"

        if 'failure_count' in response_info and response_info['failure_count'] > 0:
            print "Some failures were noted: " + str(response_info['failure_count'])

        print response_info['message']

    printResultMessage(updateNotableEvents(sessionKey=sessionKey, comment=comment, status=status, eventIDs=eventIDs))
    print("Notable events successfully updated: %s" % eventIDs)
