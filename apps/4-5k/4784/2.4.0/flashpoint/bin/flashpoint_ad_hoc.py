import sys
import logger_manager as log
import requests
import json
import splunk.rest as rest
from splunklib.searchcommands import (
    dispatch,
    StreamingCommand,
    Configuration,
)
import traceback

logger = log.setup_logging('ta_flashpoint_intelligence_ad_hoc')

    
def get_api_key(account_name, logger, session_key):
    """
    Get api_key of the account
    """
    logger.info(f"Getting API key for account: {account_name}")
    try:
        # Make a request to the Splunk REST endpoint to get the credentials
        _, content = rest.simpleRequest(
            f"/servicesNS/nobody/TA-flashpoint-intelligence/TA_flashpoint_intelligence_account/{account_name}",
            sessionKey=session_key,
            getargs={"output_mode": "json", "--cred--": 1},
            raiseAllErrors=True,
        )
    except Exception as e:
        # Handle any exceptions that occur
        logger.error(f"Could not read account settings from the rest endpoint for account '{account_name}'. Error: {str(e)}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise ValueError(f"Failed to retrieve API key for account '{account_name}': {str(e)}")

    try:
        content = json.loads(content)
        if not content or "entry" not in content or len(content["entry"]) == 0:
            logger.error(f"No entry found in response for account: {account_name}")
            raise ValueError(f"No configuration found for account '{account_name}'")
            
        response_dict = content["entry"][0]["content"]
        api_key = response_dict.get("api_key")
        
        if not api_key:
            logger.error(f"API key not found in configuration for account: {account_name}")
            raise ValueError(f"API key not configured for account '{account_name}'")
            
        logger.info(f"Successfully retrieved API key for account: {account_name}")
        return api_key
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response for account '{account_name}': {str(e)}")
        logger.error(f"Response content: {content}")
        raise ValueError(f"Invalid response format for account '{account_name}': {str(e)}")
    except KeyError as e:
        logger.error(f"Missing expected key in response for account '{account_name}': {str(e)}")
        logger.error(f"Response structure: {content}")
        raise ValueError(f"Invalid response structure for account '{account_name}': {str(e)}")


@Configuration()
class AlertDetails(StreamingCommand):
    """This class will used for custom command."""

    def _validate_input_parameters(self, record):
        """Validate and extract input parameters from record."""
        source = record.get('alert_source')
        alert_id = record.get('alert_id')
        acc_name = record.get('acc_name')
        
        if not all([source, alert_id, acc_name]):
            error_msg = f"Missing required parameters. Source: {source}, Alert ID: {alert_id}, Account: {acc_name}"
            logger.error(error_msg)
            return None, {
                'Error': error_msg
            }
        
        return source, alert_id, acc_name, None
    
    def _get_api_key_safe(self, acc_name, session_key):
        """Safely retrieve API key with error handling."""
        try:
            api_key = get_api_key(acc_name, logger, session_key)
            
            if not api_key:
                error_msg = "API key not found. Please configure the Flashpoint account."
                logger.error(error_msg)
                return None, {
                    'Error': error_msg
                }
            
            return api_key, None
        except ValueError as e:
            error_msg = f"Validation error: {str(e)}"
            logger.error(error_msg)
            return None, {
                'Error': error_msg
            }
    
    def _build_api_request(self, source, alert_id, api_key):
        """Build API request URL and headers."""
        base_url = "https://api.flashpoint.io/sources/v2"
        
        endpoint_map = {
            "communities": f"/communities/{alert_id}",
            "media": f"/media/{alert_id}",
            "marketplaces": f"/markets/{alert_id}",
            "news": f"/news/{alert_id}"
        }
        
        if source not in endpoint_map:
            error_msg = f"Unsupported alert_source: {source}. Supported sources: {list(endpoint_map.keys())}"
            logger.error(error_msg)
            return None, None, {
                'Error': error_msg,
                'Supported Sources': list(endpoint_map.keys())
            }
        
        url = base_url + endpoint_map[source]
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json"
        }
        
        return url, headers, None
    
    def _make_api_request(self, url, headers):
        """Make HTTP request with comprehensive error handling."""
        try:
            response = requests.get(url, headers=headers, timeout=60)
            return response, None
        except requests.exceptions.Timeout:
            error_msg = f"API request timeout after 60 seconds for URL: {url}"
            logger.error(error_msg)
            return None, {
                'Error': error_msg,
                'Url': url
            }
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error while calling API: {str(e)}"
            logger.error(error_msg)
            return None, {
                'Error': error_msg,
                'Url': url
            }
        except requests.exceptions.RequestException as e:
            error_msg = f"Request exception while calling API: {str(e)}"
            logger.error(error_msg)
            return None, {
                'Error': error_msg,
                'Url': url
            }
    
    def _parse_api_response(self, response):
        """Parse JSON response with error handling."""
        try:
            response_data = response.json()
            return response_data, None
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse JSON response: {str(e)}"
            logger.error(error_msg)
            return None, {
                'Error': error_msg,
                'Response Text': response.text[:200]
            }
    
    def _extract_result_data(self, source, response_data):
        """Extract result data based on source type."""
        try:
            if source == "communities":
                res = response_data.get("results")
            elif source == "media":
                res = response_data
            elif source == "marketplaces":
                results = response_data.get("results", [])
                if not results:
                    raise ValueError("No results found in marketplace response")
                res = results[0]
            elif source == "news":
                res = response_data
            
            if res is None:
                error_msg = f"No data found in response for source: {source}"
                logger.error(error_msg)
                return None, {
                    'Error': error_msg,
                    'Source': source
                }
            
            return res, None
        except (KeyError, IndexError, ValueError) as e:
            error_msg = f"Error processing response data for source '{source}': {str(e)}"
            logger.error(error_msg)
            return None, {
                'Error': error_msg,
                'Source': source
            }
    
    def _handle_api_error(self, response, url):
        """Handle API error responses."""
        error_msg = f"API call failed with status {response.status_code}"
        logger.error(f"{error_msg}, URL: {url}, Response: {response.text}")
        
        # Try to parse error response for more details
        error_details = {}
        try:
            error_json = response.json()
            error_details = error_json if isinstance(error_json, dict) else {}
        except json.JSONDecodeError:
            error_details = {'raw_response': response.text}
        
        return {
            'Error': error_msg,
            'Status Code': response.status_code,
            'Url': url,
            'Error Details': error_details,
            'Response Text': response.text[:500]
        }
    
    def _handle_unexpected_error(self, e):
        """Handle unexpected errors with logging."""
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(f"flashpoint_error: {e}")
        return {
            'Error': error_msg,
            'Exception Type': type(e).__name__
        }
    
    def _process_single_record(self, record, session_key):
        """Process a single record through the complete workflow."""
        # Validate input parameters
        validation_result = self._validate_input_parameters(record)
        if validation_result[0] is None:
            return validation_result[1], True
        
        source, alert_id, acc_name, _ = validation_result
        logger.info(f"Processing request - Source: {source}, Alert ID: {alert_id}, Account: {acc_name}")
        
        try:
            # Get API key
            api_key, api_error = self._get_api_key_safe(acc_name, session_key)
            if api_error:
                return api_error, True
            
            # Build API request
            url, headers, build_error = self._build_api_request(source, alert_id, api_key)
            if build_error:
                return build_error, True
            
            logger.info("Making API call to Flashpoint API")
            
            # Make API request
            response, request_error = self._make_api_request(url, headers)
            if request_error:
                return request_error, True
            
            # Handle response
            if response.status_code == 200:
                return self._handle_success_response(response, source, alert_id)
            else:
                return self._handle_api_error(response, url), True
                
        except ValueError as e:
            error_msg = f"Validation error: {str(e)}"
            logger.error(error_msg)
            return {
                'Error': error_msg,
            }, True
        except Exception as e:
            return self._handle_unexpected_error(e), True
    
    def _handle_success_response(self, response, source, alert_id):
        """Handle successful API response."""
        # Parse response
        response_data, parse_error = self._parse_api_response(response)
        if parse_error:
            return parse_error, True
        
        # Extract result data
        result_data, extract_error = self._extract_result_data(source, response_data)
        if extract_error:
            return extract_error, True
        
        # Return successful result
        result = json.dumps(result_data, indent=4)
        logger.info(f"Successfully processed alert id: {alert_id} for source: {source}")
        return {'Alert Information': result}, False
    
    def stream(self, records):
        """Main streaming function with reduced cognitive complexity."""
        session_key = self.search_results_info.auth_token
        
        for record in records:
            result, should_continue = self._process_single_record(record, session_key)
            yield result
            if should_continue:
                continue


if __name__ == "__main__":
    dispatch(AlertDetails, sys.argv, sys.stdin, sys.stdout, __name__)
