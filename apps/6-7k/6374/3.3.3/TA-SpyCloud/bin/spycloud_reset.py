
import splunk
import splunk.mining.dcutils as dcu
import os
import json
import splunk.rest
import time

APP_NAME = "TA-SpyCloud"

class Reset(splunk.rest.BaseRestHandler):

    def handle_POST(self):
        logger = dcu.getLogger()
        logger.debug("spycloud_reset.py start")
        
        try:
            payload = str(self.request['payload'])

            payload = payload.split("&")
            logger.debug("payload: " + str(payload))
            
            step = payload[0].split("=")[1]
            payload.pop(0)

            iter = ""
            for i in payload:
                iter = iter + str(i.split("=")[1])

            logger.debug("iter=" + iter + " state=start step=\"" + step + "\"")

            self.response.setHeader("content-type", "text/html")

            if step=="1":
                logger.debug("iter=" + iter + " state=exec1 step=\"" + step + "\"")
                self.write("Reloading Breach Catalog")
                try:
                    self.clear_index_data_for_input("spycloud_breach_catalog/SpyCloud_Breach_Catalog", "spycloud:breach_catalog")
                    self.update_checkpoint("breach_catalog_v2_checkpoint")
                    self.trigger_modular_input_reload("spycloud_breach_catalog/SpyCloud_Breach_Catalog", 120.0)
                except (PermissionError, Exception) as e:
                    self.write_operation_aborted("OPERATION ABORTED - Subsequent steps cancelled due to permission or execution error")
                    logger.error(f"Step 1 aborted due to error: {str(e)}")
                    return
            elif step=="2":
                logger.debug("iter=" + iter + " state=exec2 step=\"" + step + "\"")
                self.write("Reloading Compass")
                try:
                    self.clear_index_data_for_input("spycloud_compass/SpyCloud_Compass", "spycloud:compass")
                    self.update_checkpoint("compass_v2_checkpoint")
                    self.trigger_modular_input_reload("spycloud_compass/SpyCloud_Compass", 120.0)
                except (PermissionError, Exception) as e:
                    self.write_operation_aborted("OPERATION ABORTED - Subsequent steps cancelled due to permission or execution error")
                    logger.error(f"Step 2 aborted due to error: {str(e)}")
                    return
            elif step=="3":
                logger.debug("iter=" + iter + " state=exec3 step=\"" + step + "\"")
                self.write("Reloading Watchlist")
                try:
                    self.clear_index_data_for_input("spycloud_watchlist/SpyCloud_Watchlist", "spycloud:watchlist")
                    self.update_checkpoint("watchlist_v2_checkpoint")
                    self.trigger_modular_input_reload("spycloud_watchlist/SpyCloud_Watchlist", 300.0)
                except (PermissionError, Exception) as e:
                    self.write_operation_aborted("OPERATION ABORTED - Subsequent steps cancelled due to permission or execution error")
                    logger.error(f"Step 3 aborted due to error: {str(e)}")
                    return
            elif step=="4":
                logger.debug("iter=" + iter + " state=exec4 step=\"" + step + "\"")
                self.write("Reloading Watchlist Identifiers")
                try:
                    self.clear_index_data_for_input("spycloud_watchlist_identifiers/SpyCloud_Watchlist_Identifiers", "spycloud:watchlist_identifiers")
                    self.update_checkpoint("watchlist_identifiers_v2_checkpoint")
                    self.trigger_modular_input_reload("spycloud_watchlist_identifiers/SpyCloud_Watchlist_Identifiers", 30.0)
                except (PermissionError, Exception) as e:
                    self.write_operation_aborted("OPERATION ABORTED - Subsequent steps cancelled due to permission or execution error")
                    logger.error(f"Step 4 aborted due to error: {str(e)}")
                    return
            else:
                logger.debug("iter=" + iter + " state=fail step=\"" + step + "\"")

            self.write("Completed")
            self.write("----------------------------------------")

            logger.debug("iter=" + iter + " state=end step=\"" + step + "\"")

        except Exception as e:
            self.write("Something's wrong" + str(e))
            logger.debug(e)

        #logger.debug("spycloud_reset.py end")

    #handle verbs, otherwise Splunk will throw an error
    handle_GET = handle_POST

    def update_checkpoint(self, kvstore_name):
        try:
            logger = dcu.getLogger()

            inputs_path = "/servicesNS/nobody/" + str(APP_NAME) + "/storage/collections/data/" + str(kvstore_name) + "/"

            response, content = splunk.rest.simpleRequest(
                inputs_path,
                method="DELETE",
                sessionKey=self.sessionKey,
                getargs={"output_mode": "json"}
            )

            if response.status == 200:
                self.write("Successfully Updated Checkpoint")
                logger.info(f"Successfully cleared KV store checkpoint: {kvstore_name}")
            else:
                self.write("Failed to update Checkpoint. May not reload all data.")
                logger.warning(f"Failed to clear KV store checkpoint: {kvstore_name}, status: {response.status}")

        except Exception as e:
            logger.error("Failed to Update Checkpoint " + str(kvstore_name) + " -- " + str(e))
            self.write("Failed To Update Checkpoint: " + str(kvstore_name) + " -- " + str(e))

    def clear_index_data(self, index_name, source_type):
        """Clear existing data from the index for the given sourcetype by attempting the delete operation"""
        try:
            logger = dcu.getLogger()

            # Create a search job to delete events with the specific sourcetype
            search_query = f'search index={index_name} sourcetype={source_type} | delete'

            # Step 1: Submit the search job (don't use blocking mode)
            search_path = "/services/search/jobs"
            search_args = {
                "search": search_query,
                "output_mode": "json"
            }

            self.write(f"Clearing index data for index={index_name} sourcetype={source_type}")
            logger.info(f"Attempting to clear index data: {search_query}")

            response, content = splunk.rest.simpleRequest(
                search_path,
                method="POST",
                sessionKey=self.sessionKey,
                postargs=search_args
            )

            # Handle HTTP status codes for job submission
            if response.status == 401:
                error_msg = f"ERROR: Authentication failed (HTTP 401). Your session may have expired. Please log in again. Operation aborted."
                self.write_error(error_msg)
                logger.error(f"Authentication error for delete operation on index: {index_name}")
                raise PermissionError(error_msg)

            elif response.status == 403:
                error_msg = f"ERROR: Insufficient permissions to run search operations (HTTP 403). Operation aborted."
                self.write_error(error_msg)
                logger.error(f"Search authorization error for delete operation on index: {index_name}")
                raise PermissionError(error_msg)

            elif response.status in [200, 201]:
                # HTTP 200 (OK) or HTTP 201 (Created) - both indicate successful job submission
                logger.info(f"Delete search job submitted successfully (HTTP {response.status})")
                # Step 2: Get the job ID and check its status for permission errors
                import json
                import time

                try:
                    job_response = json.loads(content)
                    job_id = job_response.get("sid")

                    if not job_id:
                        error_msg = f"ERROR: Could not get search job ID for delete operation. Operation aborted."
                        self.write_error(error_msg)
                        logger.error(f"No job ID returned for delete operation on index: {index_name}")
                        raise Exception(error_msg)

                    logger.info(f"Delete search job submitted with ID: {job_id}")

                    # Step 3: Wait a moment and then check the job status
                    time.sleep(10)  # Give the job time to start and potentially fail

                    job_status_path = f"/services/search/jobs/{job_id}"
                    status_response, status_content = splunk.rest.simpleRequest(
                        job_status_path,
                        method="GET",
                        sessionKey=self.sessionKey,
                        getargs={"output_mode": "json"}
                    )

                    if status_response.status in [200, 201]:
                        status_json = json.loads(status_content)
                        entry = status_json.get("entry", [{}])[0]
                        job_content = entry.get("content", {})

                        # Check job state
                        dispatch_state = job_content.get("dispatchState", "")
                        is_done = job_content.get("isDone", False)
                        is_failed = job_content.get("isFailed", False)

                        logger.info(f"Delete job status: dispatchState={dispatch_state}, isDone={is_done}, isFailed={is_failed}")

                        # Check for error messages that indicate permission failures
                        messages = job_content.get("messages", [])
                        for message in messages:
                            message_text = message.get("text", "")
                            message_type = message.get("type", "")

                            logger.info(f"Job message ({message_type}): {message_text}")

                            # Check for success patterns first - skip error checking for successful operations
                            if any(success_pattern in message_text.lower() for success_pattern in [
                                "successfully deleted", "events deleted", "delete successful", "deletion completed"
                            ]):
                                continue  # This is a success message, skip error checking

                            # Look for permission-related errors (removed generic "delete" to avoid false positives)
                            if any(keyword in message_text.lower() for keyword in [
                                "permission", "authorized", "forbidden", "capability",
                                "access denied", "not allowed", "insufficient", "delete failed",
                                "cannot delete", "unable to delete", "delete denied"
                            ]):
                                error_msg = f"ERROR: Delete operation failed due to insufficient permissions: {message_text}. Operation aborted."
                                self.write_error(error_msg)
                                logger.error(f"Permission error in delete job for index: {index_name}")
                                raise PermissionError(error_msg)

                        # If the job failed for any reason, it might be a permission issue
                        if is_failed or dispatch_state == "FAILED":
                            error_msg = f"ERROR: Delete search job failed. This may indicate insufficient permissions to delete data from index '{index_name}'. Operation aborted."
                            self.write_error(error_msg)
                            logger.error(f"Delete job failed for index: {index_name}, state: {dispatch_state}")
                            raise PermissionError(error_msg)

                        # If we get here, the job appears to have started successfully
                        self.write(f"Delete search initiated successfully for {source_type}")
                        logger.info(f"Delete search job running for index={index_name} sourcetype={source_type}")

                    else:
                        error_msg = f"ERROR: Could not check delete job status (HTTP {status_response.status}). Operation aborted."
                        self.write_error(error_msg)
                        logger.error(f"Failed to get job status for delete operation on index: {index_name}")
                        raise Exception(error_msg)

                except json.JSONDecodeError as e:
                    error_msg = f"ERROR: Could not parse delete job response. Operation aborted."
                    self.write_error(error_msg)
                    logger.error(f"JSON decode error for delete operation on index: {index_name}: {e}")
                    raise Exception(error_msg)

            else:
                error_msg = f"ERROR: Delete search submission failed with HTTP {response.status}. Operation aborted."
                self.write_error(error_msg)
                logger.warning(f"Delete search failed with status: {response.status}, content: {content[:200] if content else 'No content'}")
                raise Exception(error_msg)

        except PermissionError:
            # Re-raise permission errors to abort the operation
            raise
        except Exception as e:
            # Handle any other exceptions
            if "Operation aborted" in str(e):
                # Already handled, just re-raise
                raise
            else:
                # Unexpected error
                logger.error(f"Unexpected error clearing index data for {index_name}/{source_type}: {str(e)}")
                error_msg = f"ERROR: Unexpected error during delete operation: {str(e)}. Operation aborted."
                self.write_error(error_msg)
                raise Exception(error_msg)

    def clear_index_data_for_input(self, modular_input, source_type):
        """Clear index data for a specific input by getting the correct index name"""
        try:
            logger = dcu.getLogger()

            # Get the input configuration to find the index
            inputs_path = "/servicesNS/nobody/" + str(APP_NAME) + "/data/inputs/" + str(modular_input)

            response, content = splunk.rest.simpleRequest(
                inputs_path,
                method="GET",
                sessionKey=self.sessionKey,
                getargs={"output_mode": "json"}
            )

            if response.status == 200:
                content_json = json.loads(content)
                input_config = content_json["entry"][0]["content"]

                # Get the index from input config - REQUIRE it to be specified, no fallback to 'main'
                index_name = input_config.get("index")

                if not index_name:
                    error_msg = f"ERROR: No index configured for modular input '{modular_input}'. Cannot proceed without a valid index configuration. Operation aborted."
                    logger.error(error_msg)
                    self.write_error(error_msg)
                    raise Exception(error_msg)

                logger.info(f"Found index configuration for {modular_input}: {index_name}")
                self.write(f"Clearing data from index: {index_name}")

                # Attempt to clear index data - any permission or other errors will abort the operation
                self.clear_index_data(index_name, source_type)
            else:
                error_msg = f"ERROR: Cannot read configuration for modular input '{modular_input}' (HTTP {response.status}). Operation aborted."
                logger.error(error_msg)
                self.write_error(error_msg)
                raise Exception(error_msg)

        except Exception as e:
            # If this is already a permission error or our own configuration error, re-raise it
            if isinstance(e, PermissionError) or "Operation aborted" in str(e):
                raise

            # For any other configuration errors, abort immediately
            error_msg = f"ERROR: Failed to get index configuration for '{modular_input}': {str(e)}. Operation aborted."
            logger.error(error_msg)
            self.write_error(error_msg)
            raise Exception(error_msg)

    def trigger_modular_input(self, modular_input, delay):
        logger = dcu.getLogger()
        
        inputs_path = "/servicesNS/nobody/" + str(APP_NAME) + "/data/inputs/" + str(modular_input)

        response, content = splunk.rest.simpleRequest(
            inputs_path,
            method="GET",
            sessionKey=self.sessionKey,
            getargs={"output_mode": "json"}
        )
        
        content_json = json.loads(content)
        interval = str(content_json["entry"][0]["content"]["interval"])

        splunk.rest.simpleRequest(
            inputs_path,
            method="POST",
            sessionKey=self.sessionKey,
            postargs={"interval": "86400"},
        )

        splunk.rest.simpleRequest(
            inputs_path + "/disable",
            method="POST",
            sessionKey=self.sessionKey,
        )

        splunk.rest.simpleRequest(
            inputs_path + "/enable",
            method="POST",
            sessionKey=self.sessionKey,
        )

        time.sleep(delay)

        splunk.rest.simpleRequest(
            inputs_path,
            method="POST",
            sessionKey=self.sessionKey,
            postargs={"interval": interval},
        )

        logger.debug("Successfully Set Modular Input Interval: "+ str(interval) + " -- " + str(modular_input))
        logger.debug("Successfully Reloaded SpyCloud Database: " + str(modular_input))

        self.write("Successfully Set Modular Input Interval: "+ str(interval))
        self.write("Successfully Reloaded SpyCloud Database")

    def trigger_modular_input_reload(self, modular_input, delay):
        """Trigger modular input with force_reload parameter for reload mode"""
        logger = dcu.getLogger()

        inputs_path = "/servicesNS/nobody/" + str(APP_NAME) + "/data/inputs/" + str(modular_input)

        response, content = splunk.rest.simpleRequest(
            inputs_path,
            method="GET",
            sessionKey=self.sessionKey,
            getargs={"output_mode": "json"}
        )

        content_json = json.loads(content)
        interval = str(content_json["entry"][0]["content"]["interval"])

        # Temporarily set force_reload parameter and adjust interval
        splunk.rest.simpleRequest(
            inputs_path,
            method="POST",
            sessionKey=self.sessionKey,
            postargs={"interval": "86400", "force_reload": "true"},
        )

        splunk.rest.simpleRequest(
            inputs_path + "/disable",
            method="POST",
            sessionKey=self.sessionKey,
        )

        splunk.rest.simpleRequest(
            inputs_path + "/enable",
            method="POST",
            sessionKey=self.sessionKey,
        )

        time.sleep(delay)

        # Restore original settings
        splunk.rest.simpleRequest(
            inputs_path,
            method="POST",
            sessionKey=self.sessionKey,
            postargs={"interval": interval, "force_reload": "false"},
        )

        logger.debug("Successfully Set Modular Input for Reload Mode: "+ str(interval) + " -- " + str(modular_input))
        logger.debug("Successfully Triggered Reload for SpyCloud Database: " + str(modular_input))

        self.write("Successfully Set Modular Input for Reload Mode: "+ str(interval))
        self.write("Successfully Triggered Reload for SpyCloud Database")

    def write(self, msg):
        self.response.write("<p>" + str(msg) + "</p>")

    def write_error(self, msg):
        """Write an error message with red styling"""
        self.response.write('<p style="color: red; font-weight: bold;">' + str(msg) + '</p>')

    def write_operation_aborted(self, msg):
        """Write an operation aborted message with red styling and emphasis"""
        self.response.write('<p style="color: red; font-weight: bold; font-size: 1.1em; background-color: #ffe6e6; padding: 5px; border-left: 4px solid red;">' + str(msg) + '</p>')
