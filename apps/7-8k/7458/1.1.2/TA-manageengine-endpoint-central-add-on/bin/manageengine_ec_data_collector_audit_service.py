from manageengine_ec_utils import *
from Constants import *
from urllib.parse import urlencode, urljoin
import json
import requests
from datetime import datetime
import traceback
import time


def fetchAuditData(helper, event_writer, startTime, endTime, audit_api):
    nextPageAvailable = True
    currentPage = DEFAULT_PAGE
    helper.log_info("------------ Starting to fetch Audit data --------------")
    try:
        while nextPageAvailable:
            helper.log_info(
                f"Fetching Audit Data for the time range: {startTime} to {endTime} for page: {currentPage}"
            )

            url = construct_url(helper, AUDIT_API)
            params = {
                START_TIME: startTime,
                END_TIME: endTime,
                PAGE: currentPage
            }
            action_log_url = urljoin(url, '?' + urlencode(params))


            response = construct_endpoint(
                helper=helper,
                url=action_log_url,
                method=METHOD_GET
            )

            try:
                response_content = json.loads(response.content.decode())

                # Handle application-level errors from JSON body
                if "errormsg" in response_content or "errorMsg" in response_content:
                    error_code = response_content.get("errorCode", response_content.get("errorcode", "UNKNOWN_CODE"))
                    error_url = response_content.get("url", "UNKNOWN_URL")
                    error_msg = response_content.get("errorMsg", response_content.get("errormsg", "UNKNOWN_ERROR"))

                    helper.log_error(f"API Error Response Detected:")
                    helper.log_error(f"  URL        : {error_url}")
                    helper.log_error(f"  Error Code : {error_code}")
                    helper.log_error(f"  Message    : {error_msg}")

                    return FAILURE, error_msg

            except json.JSONDecodeError as e:
                helper.log_error(f"JSON decode error: {str(e)}")
                helper.log_error(traceback.format_exc())
                return FAILURE, "Failed to decode JSON response"

            dataset = response_content.get("messageResponse", [])
            if not dataset:
                helper.log_info(f"No data found in the response for the given time range --> {startTime} to {endTime}")
                time2 = int(time.time())
                return SUCCESS,time2

            totalPages = response_content.get("metadata", {}).get("totalPages", 0)

            if totalPages > currentPage:
                currentPage += 1
            else:
                nextPageAvailable = False

            helper.log_info(f"Total Pages: {totalPages} Current Page: {currentPage}")

            for json_data in dataset:
                formattedTime = json_data.get("eventTime", None)
                if formattedTime:
                    formattedTime = datetime.fromtimestamp(int(formattedTime) / 1000)
                else:
                    formattedTime = datetime.now()

                json_string = json.dumps(json_data)

                event = helper.new_event(
                    data=json_string,
                    time=formattedTime,
                    sourcetype=get_source_type(AUDIT_MODULE_ID)
                )
                helper.log_info(formattedTime)
                helper.log_info(get_source_type(AUDIT_MODULE_ID))
                helper.log_info(event)
                event_writer.write_event(event)
                helper.save_check_point(START_TIME,endTime)      
        time1 = int(time.time())        
        status, remark = SUCCESS, time1
        helper.log_info(remark)
        return status, remark

    except requests.exceptions.ConnectionError as e:
        helper.log_error(f"Connection error occurred: {str(e)}")
        helper.log_error(traceback.format_exc())
        return FAILURE, "Connection error occurred while trying to reach the server."

    except requests.exceptions.Timeout as e:
        helper.log_error(f"Request timed out: {str(e)}")
        helper.log_error(traceback.format_exc())
        return FAILURE, "Request timed out while trying to reach the server."

    except requests.exceptions.RequestException as e:
        helper.log_error(f"Request exception: {str(e)}")
        helper.log_error(traceback.format_exc())
        return FAILURE, "An error occurred while making the request."

    except IOError as e:
        helper.log_error(f"I/O error: {str(e)}")
        helper.log_error(traceback.format_exc())
        return FAILURE, "I/O error occurred while processing the response."

    except Exception as e:
        helper.log_error(f"Unexpected error: {str(e)}")
        helper.log_error(traceback.format_exc())
        return FAILURE, "An unexpected error occurred."
