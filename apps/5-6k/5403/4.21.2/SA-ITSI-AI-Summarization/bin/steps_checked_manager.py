
from typing import Dict, Any, List, Union
from constants import *
from util.context_logging import get_context_logger
from util import setup_logging
import sys
class StepsCheckedManager:
    """
    Steps Checked Manager

    This module provides a centralized class to manage steps_checked metadata for ITSI summarization.
    It handles the tracking of various data checked steps and episode information.
    """

    def __init__(self):
        """Initialize the StepsCheckedManager."""
        logger = setup_logging.get_logger()
        self.logger = get_context_logger(logger)
        
        # Store all steps_checked_metadata including episode information per summarization_id
        # Structure: {
        #   summarization_id: {
        #     "steps_checked": {
        #         "checked_impacted_items": [],
        #         "checked_alerts": {"status": 0},
        #         "checked_summary_data": {"status": 0},
        #         "checked_topology_data": {"status": 0},
        #         "custom_queries_data": [{"status": 0}, ...]
        #     },
        #     "num_of_alerts": 0,
        #     "episode_start_time": 0,
        #     "episode_end_time": 0
        #   }
        # }
        self._metadata_by_summarization_id = {}
    # Track the function execution result
    # status: -1 = success (response is not None)
    #          0 = failure (failed to get the response, or the response is empty)
    @staticmethod
    def get_result_status(r):
        # If it is None, we consider it a failure(status = 0)
        if r is None:
            return 0
        # For tuple results like (results, additional_info), 
        # we check whether first element is empty or None
        # Used in get_kpi_and_entity_ts
        if isinstance(r, tuple): 
            if r[0]: # success with non-empty dict
                return -1
            else: # fail with empty dict
                return 0
        # Empty list is considered a failure
        if isinstance(r, list):
            if r: # success
                return -1
            else: # failure
                return 0

        # Empty string is considered a failure
        # Used in get_and_clean_alerts
        if isinstance(r, str):
            if r.strip() == "":
                return 0 # failure
            else:
                return -1 # success
        if isinstance(r, dict):
            return -1 if r else 0
        return 0 # failure by default
    
    def get_or_initialize_metadata(self, summarization_id: str) -> Dict[str, Any]:
        """
        Get or initialize steps_checked metadata for a specific summarization_id.
        
        Args:
            summarization_id: The ID of the summarization process
            
        Returns:
            Dict containing the complete metadata structure for the summarization_id
        """
        if summarization_id not in self._metadata_by_summarization_id:
            self._metadata_by_summarization_id[summarization_id] = {
                STEPS_CHECKED: {
                    CHECKED_IMPACTED_ITEMS: [], 
                    CHECKED_ALERTS: {STATUS: 0},
                    CHECKED_SUMMARY_DATA: {STATUS: 0},
                    CHECKED_TOPOLOGY_DATA: {STATUS: 0},
                    CHECKED_SERVICE_IMPACT_ANALYSIS: {STATUS: 0},
                    CUSTOM_QUERIES_DATA: []
                },
                "num_of_alerts": 0,
                "episode_start_time": 0,
                "episode_end_time": 0
            }
        return self._metadata_by_summarization_id[summarization_id]
    
    def _record_function_status_for_steps_checked(self, summarization_id: str, result):
        """
        Tracking and recording function execution status for steps_checked.
        Automatically detects the calling function name using sys._getframe().
        
        Args:
            summarization_id: The summarization ID
            result: the returned result from the function to be tracked.
        """
        # Get the name of the calling function automatically using sys._getframe()
        func_name = sys._getframe(1).f_code.co_name
        
        # Map function names to steps_checked fields
        function_field_mapping = {
            'get_and_clean_alerts': CHECKED_ALERTS,
            'get_kpi_and_entity_ts': CHECKED_SUMMARY_DATA,
            'get_services_topology': CHECKED_TOPOLOGY_DATA,
            'collect_service_impact_analysis': CHECKED_SERVICE_IMPACT_ANALYSIS,
        }
        
        field_name = function_field_mapping.get(func_name)
        # status: The result status from the function execution: 0 means failure; -1 means success.
        status = StepsCheckedManager.get_result_status(result)
        if field_name:
            log_func = self.logger.error if status == 0 else self.logger.debug
            log_func(
                f"Function {func_name} for summarization_id {summarization_id}: "
                f"check result for StepsCheckedManager: result={result}"
                f"{'Failed to call or got empty result' if status == 0 else 'Succeeded'}"
            )
            
            self.update_steps_checked_field(
                summarization_id,
                field_name,
                {STATUS: status}
            )
        else:
            # If function name is not in the mapping, log a warning
            self.logger.warning(f"Function {func_name} is not configured for tracking in steps_checked")
 
    def update_episode_time(self, summarization_id: str, start_time: int, end_time: int):
        """
        Update episode start and end times for a summarization_id.
        
        Args:
            summarization_id: The ID of the summarization process
            start_time: Episode start time (Unix timestamp)
            end_time: Episode end time (Unix timestamp)
        """
        metadata = self.get_or_initialize_metadata(summarization_id)
        metadata["episode_start_time"] = start_time
        metadata["episode_end_time"] = end_time
        self.logger.info(f"Updated episode time in steps_checked metadata: start={start_time}, end={end_time}")
    
    def update_num_alerts(self, summarization_id: str, num_of_alerts: int):
        """
        Update the number of alerts for a summarization_id.
        
        Args:
            summarization_id: The ID of the summarization process
            num_of_alerts: Number of alerts found
        """
        metadata = self.get_or_initialize_metadata(summarization_id)
        metadata["num_of_alerts"] = num_of_alerts
        self.logger.info(f"Updated number of alerts in steps_checked metadata: {num_of_alerts}")
        
    def update_steps_checked_field(self, summarization_id: str, field: str, data: Union[List[str], Dict[str, Any]]):
        """
        Update a specific field in steps_checked for a summarization_id.
        
        Args:
            summarization_id: The ID of the summarization process
            field: The field name to update
            data: The data to set for the field
        """
        metadata = self.get_or_initialize_metadata(summarization_id)
        
        # Check if field exists in steps_checked metadata
        if field not in metadata[STEPS_CHECKED]:
            self.logger.warning(
                f"update_steps_checked_field: Invalid field '{field}'"
                f"Field does not exist in steps_checked metadata. "
                f"Available fields in steps_checked metadata: {list(metadata[STEPS_CHECKED].keys())}"
            )
            return
        
        # Check if field has data in a list type
        if field in [CHECKED_IMPACTED_ITEMS, CUSTOM_QUERIES_DATA]:
            if isinstance(data, list):
                metadata[STEPS_CHECKED][field] = data
                self.logger.debug(
                    f"update_steps_checked_field: Successfully updated list field '{field}' for summarization_id: {summarization_id}. "
                    f"Updated {len(data)} items. New data: {data}"
                )
            else:
                self.logger.error(
                    f"update_steps_checked_field: Invalid data type for field '{field}' for summarization_id: {summarization_id}. "
                    f"Field '{field}' requires list data type, but received {type(data).__name__}. "
                    f"Expected: list, Actual: {type(data)}. Received data: {data}"
                )
            return
        
        # Check if field has data in a dict type
        # Validate data structure - must be a dict and contain STATUS
        if not isinstance(data, dict) or STATUS not in data:
            self.logger.error(
                f"update_steps_checked_field: Invalid data structure for field: '{field}'. "
                f"Data must be a dictionary and contain '{STATUS}' key. Received data: {data}"
            )
            return
        
        # Validate STATUS value
        valid_status_values = [-1, 0]  # Based on get_result_status method
        if data[STATUS] not in valid_status_values:
            self.logger.error(
                f"update_steps_checked_field: Unexpected status value, field: '{field}'. "
                f"Status: {data[STATUS]}. Expected values: {valid_status_values} (-1=success, 0=failure)"
            )
            return
        
       
        # Update the field
        metadata[STEPS_CHECKED][field] = data
        
        # Enhanced logging with more context
        status_description = "success" if data[STATUS] == -1 else "failure"
        self.logger.debug(
            f"update_steps_checked_field: Successfully updated field '{field}' for summarization_id: {summarization_id}. "
            f"Status: {data[STATUS]} ({status_description}). "
            f"New data: {data}"
        )
    
    def get_steps_checked_with_descriptions(self, summarization_id: str) -> Dict[str, Any]:
        """
        Get steps_checked data with auto-generated descriptions based on episode metadata.
        
        Args:
            summarization_id: The ID of the summarization process
            
        Returns:
            Dict containing steps_checked data with descriptions
            Example: 
            {
                "checked_impacted_items": ["services", "kpis"], 
                "checked_alerts": {"description": "...", "status": ...},
                "checked_summary_data": {"description": "...", "status": ...},
                "checked_topology_data": {"description": "...", "status": ...},
                "service_impact_analysis": {"description": "...", "status": ...},
                "custom_queries_data": [{"description": "...", "types": [...],"status": ...}],
            }
        """
        metadata = self.get_or_initialize_metadata(summarization_id)
        
        # Fill description based on the field type and it corresponding function status
        # Field                               | Description
        # ------------------------------------|------------------------------------------------
        # checked_impacted_items              |    N/A 
        # checked_alerts                      | " when checking X notable events in the episode between the time range of y and z."
        # checked_summary_data                | " when checking service health and KPIs."
        # checked_topology_data               | " when checking relationships between services and service impact analysis."
        # checked_service_impact_analysis     | " when checking service impact analysis."
        # custom_queries_data                 | the description field from the custom_queries data returned by the ITSI get_custom_queries API + Issues found/No issues found.

        # The process to generated descriptions based on field type and its status here is intentionally designed to work with the SCS endpoint implemented in the summarization-service repo.
        # 1. Here we generate partial descriptions starting with " when checking..."
        # 2. The SCS endpoint complete the description with "No issues found" or "Issues found" based on the its status generated by LLM.
        #    - Status 1 (success) → "Issues found when checking..."
        #    - Status 0 (failure)  → "No issues found when checking..."
        # 
        # Final Output Examples:
        # - "No issues found when checking 5 notable events in the episode between the time range of ..."
        # - "Issues found when checking service health and KPIs."       
        metadata[STEPS_CHECKED][CHECKED_ALERTS][DESCRIPTION_KEY] = f" when checking {metadata['num_of_alerts']} notable events in the episode between the time range of {START_UNIX_TIMESTAMP}{metadata['episode_start_time']}{END_UNIX_TIMESTAMP} and {START_UNIX_TIMESTAMP}{metadata['episode_end_time']}{END_UNIX_TIMESTAMP}."
        metadata[STEPS_CHECKED][CHECKED_SUMMARY_DATA][DESCRIPTION_KEY] = " when checking service health and KPIs."
        metadata[STEPS_CHECKED][CHECKED_TOPOLOGY_DATA][DESCRIPTION_KEY] = " when checking relationships between services."
        metadata[STEPS_CHECKED][CHECKED_SERVICE_IMPACT_ANALYSIS][DESCRIPTION_KEY] = " when checking service impact analysis."
        return metadata[STEPS_CHECKED]
    
    
    def cleanup_metadata(self, summarization_id: str):
        """
        Remove all metadata for a specific summarization_id.
        
        This should be called when a summarization task is completed successfully or failed.
        
        Args:
            summarization_id: The ID of the summarization process to clean up
        """
        if summarization_id in self._metadata_by_summarization_id:
            del self._metadata_by_summarization_id[summarization_id]
            self.logger.info(f"Cleaned up all steps_checked_metadata for {summarization_id}")
        else:
            self.logger.info(f"Steps_checked_metadata for {summarization_id} was already cleaned.")
    
