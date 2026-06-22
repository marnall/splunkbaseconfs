import splunk.admin as admin
import splunk.rest as rest
import json
from splunk.persistconn.application import PersistentServerConnectionApplication


class ApexSetup(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        """
        Called for a simple synchronous request.
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """
        try:
            # Parse the incoming request
            request = json.loads(in_string)
            method = request.get('method', 'GET')

            if method == 'POST':
                # Extract the JSON body
                body = json.loads(request.get('payload', '{}'))
                session_key = request.get('session', {}).get('authtoken')

                # Validate required fields
                required_fields = ['hec_token_name', 'index', 'source']
                for field in required_fields:
                    if field not in body:
                        return {
                            'payload': {'error': f'Missing required field: {field}'},
                            'status': 400
                        }

                # Create the HEC token using the admin endpoint
                postargs = {
                    'hec_token_name': body['hec_token_name'],
                    'index': body['index'],
                    'source': body['source'],
                    'output_mode': 'json'
                }

                serverResponse, serverContent = rest.simpleRequest(
                    '/servicesNS/nobody/TA-viavi-apex-addon/admin/apex-setup-templates/hec-config',
                    method='POST',
                    postargs=postargs,
                    sessionKey=session_key
                )

                # Return the response
                return {
                    'payload': json.loads(serverContent),
                    'status': serverResponse.status
                }
            else:
                # Handle GET request - return current configuration
                session_key = request.get('session', {}).get('authtoken')
                serverResponse, serverContent = rest.simpleRequest(
                    '/servicesNS/nobody/TA-viavi-apex-addon/admin/apex-setup-templates/hec-config?output_mode=json',
                    method='GET',
                    sessionKey=session_key
                )

                return {
                    'payload': json.loads(serverContent),
                    'status': serverResponse.status
                }

        except Exception as e:
            return {
                'payload': {'error': str(e)},
                'status': 500
            }

    def handleStream(self, handle, in_string):
        """
        For future use
        """
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")

    def done(self):
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass