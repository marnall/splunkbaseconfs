import splunk.Intersplunk
from future.moves.urllib import request
from future.moves.urllib.error import HTTPError, URLError
from ta_bigpanda.logging_helper import get_logger
from bp_utils import disable_proxy, disable_ssl_verification, normalize_url
from splunkenv import get_conf_key_value

logger = get_logger("bigpanda_action_manager")


if __name__ == "__main__":
    updated_results = []
    bp_action = "bigpanda_alert"
    try:
        results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
        logger.info(f"Processing {len(results)} result(s).")

        actions = ""
        headers = {"Authorization": f"Splunk {str(settings.get('sessionKey'))}"}
        use_proxy = get_conf_key_value("ta_bigpanda_settings.conf", "action_manager", "use_proxy")
        use_proxy = str(use_proxy).strip().lower() in ["true", "1", "yes"] if use_proxy else False
        # Add the bigpanda alert action to each result
        for result in results:
            if result.get('actions'):
                actions = result.get('actions')
            # Get the saved search URL
            search_url = result.get('id')
            # Modify Actions to add the BigPanda action
            if bp_action not in actions:
                actions = f"{actions},{bp_action}" if actions else bp_action
            result['actions'] = actions
            result["action.bigpanda_alert"] = "1"
            # Normalize the url to save to localhost
            url = normalize_url(search_url, actions)
            if not url:
                logger.error(f"Unable to add {bp_action} to saved search: {url}")
                continue
            # Disable proxy usage
            if not use_proxy:
                disable_proxy()
            # Create an SSL context to disable certificate verification
            ssl_context = disable_ssl_verification()
            try:
                logger.info(f"Adding {bp_action} action to saved search: {url}")
                # Send updated request to Splunk
                req = request.Request(url, b"", headers)
                res = request.urlopen(req, context=ssl_context)
                logger.info(f"Response received: {res.getcode()}")
            except HTTPError as e:
                logger.error(f"ERROR Error sending BigPanda request: {e}")
            except URLError as e:
                logger.error(f"ERROR Error sending BigPanda request: {e}")
            except ValueError as e:
                logger.error(f"ERROR Invalid URL: {e}")
            # Append result for output
            updated_results.append(result)
    except KeyError as e:
        logger.error(f"ERROR Missing configuration key: {e}")
    except Exception as e:
        logger.error(f"ERROR Unexpected error: {e}")
    # Send updated results back to the UI
    splunk.Intersplunk.outputResults(updated_results)
    logger.info(f"Enabled action.{bp_action} on {len(updated_results)} saved searches.")
