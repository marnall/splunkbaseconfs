import json
import requests
from splunk.rest import BaseRestHandler

class ApiKeyValidator(BaseRestHandler):
    def handle_POST(self):
        # Get the API key from the request payload
        api_key = self.payload.get('api_key')

        # Check if the API key is provided and has the correct length
        if not api_key or len(api_key) != 32:
            self.error_response("API Key must be exactly 32 characters long.")
            return

        # Define the endpoint URL to validate the API key
        validation_url = "https://api.xposedornot.com/v1/domain-breaches/"

        # Make a POST request to the API endpoint with the API key
        headers = {"Authorization": f"Bearer {api_key}"}
        try:
            response = requests.post(validation_url, headers=headers)

            # Check if the response status code is 200 (OK)
            if response.status_code == 200:
                # If valid, return a success response
                self.success_response()
            else:
                # If not valid, return an error response
                self.error_response("Invalid API Key")

        except requests.RequestException as e:
            # Handle any request exceptions (e.g., connection errors)
            self.error_response(f"Error validating API Key: {str(e)}")

    def success_response(self):
        # Function to handle successful validation
        self.response.write(json.dumps({"status": "success", "message": "API Key is valid"}))
        self.response.setStatus(200)

    def error_response(self, message):
        # Function to handle errors in validation
        self.response.write(json.dumps({"status": "error", "message": "API key is Invalid"}))
        self.response.setStatus(400)
