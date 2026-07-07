#!/usr/bin/env python
# coding=utf-8

__name__ = "trackme_rest_handler_bank_holidays_admin.py"
__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Built-in libraries
import datetime
import json
import os
import sys
import time

# splunk home
splunkhome = os.environ["SPLUNK_HOME"]

# append current directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# import libs
import import_declare_test

# set logging
from trackme_libs_logging import setup_logger

logger = setup_logger("trackme.rest.bank_holidays.admin", "trackme_rest_api_bank_holidays_admin.log")


# import rest handler
import trackme_rest_handler

# import trackme libs
from trackme_libs import trackme_audit_event, trackme_getloglevel, trackme_parse_describe_flag

# import Splunk libs
import splunklib.client as client


class TrackMeHandlerBankHolidaysAdmin_v2(trackme_rest_handler.RESTHandler):
    def __init__(self, command_line, command_arg):
        super(TrackMeHandlerBankHolidaysAdmin_v2, self).__init__(
            command_line, command_arg, logger
        )

    @staticmethod
    def safe_convert_boolean(value, default=False):
        """
        Safely convert a value to boolean, handling string booleans correctly.
        
        Args:
            value: The value to convert (bool, str, int, or None)
            default: Default value if conversion fails
            
        Returns:
            bool: The converted boolean value
        """
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            value_lower = value.lower()
            if value_lower in ("true", "1"):
                return True
            elif value_lower in ("false", "0", ""):
                return False
            else:
                # Invalid string, return default
                return default
        elif isinstance(value, int):
            return bool(value)
        else:
            return default

    @staticmethod
    def safe_create_datetime(year, month, day, hour=0, minute=0, second=0, tzinfo=None):
        """
        Safely create a datetime object, handling leap years.
        If trying to create Feb 29 in a non-leap year, falls back to Feb 28.
        
        Args:
            year: Year
            month: Month (1-12)
            day: Day of month
            hour: Hour (default 0)
            minute: Minute (default 0)
            second: Second (default 0)
            tzinfo: Timezone info (default None)
            
        Returns:
            datetime.datetime object
        """
        # Check if this is Feb 29 and the year is not a leap year
        if month == 2 and day == 29:
            # Check if year is a leap year
            is_leap_year = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
            if not is_leap_year:
                # Fall back to Feb 28 for non-leap years
                day = 28
                logger.debug(f'Leap year adjustment: Feb 29 in non-leap year {year} adjusted to Feb 28')
        
        return datetime.datetime(year, month, day, hour, minute, second, tzinfo=tzinfo)

    def create_maintenance_kdb_record(self, service, period_name, start_date, end_date, comment, username):
        """
        Helper function to create a maintenance KDB record for a bank holiday period.
        
        Args:
            service: Splunk service connection
            period_name: Name of the bank holiday period
            start_date: Start date in epoch timestamp
            end_date: End date in epoch timestamp
            comment: Comment/description
            username: Username creating the record
            
        Returns:
            tuple: (success: bool, maintenance_key: str or None, error_message: str or None)
        """
        try:
            collection_name = "kv_trackme_maintenance_kdb"
            collection = service.kvstore[collection_name]
            
            current_time = round(time.time(), 0)
            
            # Create maintenance record
            maintenance_record = {
                "tenants_scope": ["*"],  # Bank holidays apply to all tenants
                "is_disabled": False,
                "no_days_validity": 0,  # Valid forever (bank holidays don't expire)
                "reason": f"Bank Holiday: {period_name}",
                "type": "planned",  # Bank holidays are planned
                "add_info": comment or f"Bank holiday period: {period_name}",
                "src_user": username,
                "time_start": start_date,
                "time_end": end_date,
                "time_expiration": 0,  # No expiration
                "ctime": current_time,
                "mtime": current_time,
            }
            
            kv_response = collection.data.insert(json.dumps(maintenance_record))
            maintenance_key = kv_response.get("_key")
            
            logger.info(f'Created maintenance KDB record for bank holiday "{period_name}", key="{maintenance_key}"')
            return True, maintenance_key, None
            
        except Exception as e:
            error_msg = f'Failed to create maintenance KDB record, exception="{str(e)}"'
            logger.error(error_msg)
            return False, None, error_msg

    def update_maintenance_kdb_record(self, service, maintenance_key, period_name, start_date, end_date, comment, username):
        """
        Helper function to update a maintenance KDB record for a bank holiday period.
        
        Args:
            service: Splunk service connection
            maintenance_key: Key of the maintenance record to update
            period_name: Name of the bank holiday period
            start_date: Start date in epoch timestamp
            end_date: End date in epoch timestamp
            comment: Comment/description
            username: Username updating the record
            
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        try:
            collection_name = "kv_trackme_maintenance_kdb"
            collection = service.kvstore[collection_name]
            
            # Retrieve existing record
            existing_record = collection.data.query_by_id(maintenance_key)
            
            if not existing_record:
                return False, f'Maintenance KDB record with key="{maintenance_key}" not found'
            
            # Update fields
            current_time = round(time.time(), 0)
            existing_record["reason"] = f"Bank Holiday: {period_name}"
            existing_record["add_info"] = comment or f"Bank holiday period: {period_name}"
            existing_record["time_start"] = start_date
            existing_record["time_end"] = end_date
            existing_record["mtime"] = current_time
            
            # Update the record
            collection.data.update(str(maintenance_key), json.dumps(existing_record))
            
            logger.info(f'Updated maintenance KDB record for bank holiday "{period_name}", key="{maintenance_key}"')
            return True, None
            
        except Exception as e:
            error_msg = f'Failed to update maintenance KDB record, exception="{str(e)}"'
            logger.error(error_msg)
            return False, error_msg

    def _delete_maintenance_kdb_record(self, service, maintenance_key, period_name):
        """
        Helper function to delete a maintenance KDB record for a bank holiday period.
        Only deletes if the period has not passed yet.
        
        Args:
            service: Splunk service connection
            maintenance_key: Key of the maintenance record to delete
            period_name: Name of the bank holiday period (for logging)
            
        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        try:
            collection_name = "kv_trackme_maintenance_kdb"
            collection = service.kvstore[collection_name]
            
            # Retrieve existing record to check if period has passed
            existing_record = collection.data.query_by_id(maintenance_key)
            
            if not existing_record:
                # Record doesn't exist, consider it already deleted
                logger.warning(f'Maintenance KDB record with key="{maintenance_key}" not found, skipping deletion')
                return True, None
            
            # Check if the period has passed (end_date < current time)
            end_date = existing_record.get("time_end", 0)
            current_time = round(time.time(), 0)
            
            if end_date < current_time:
                # Period has passed, don't delete (as per requirements)
                logger.info(f'Maintenance KDB record for bank holiday "{period_name}" (key="{maintenance_key}") has passed, skipping deletion')
                return True, None  # Not an error, just skipped
            
            # Period hasn't passed, delete the record
            collection.data.delete(json.dumps({"_key": maintenance_key}))
            
            logger.info(f'Deleted maintenance KDB record for bank holiday "{period_name}", key="{maintenance_key}"')
            return True, None
            
        except Exception as e:
            error_msg = f'Failed to delete maintenance KDB record, exception="{str(e)}"'
            logger.error(error_msg)
            return False, error_msg

    def create_next_year_recurring_period(self, collection, service, original_record, username):
        """
        Helper function to create the next year's occurrence for a recurring bank holiday.
        
        Args:
            collection: The KVstore collection
            service: Splunk service connection (for creating maintenance KDB records)
            original_record: The original bank holiday record (dict)
            username: The username creating the record
            
        Returns:
            tuple: (success: bool, new_record: dict or None, error_message: str or None)
        """
        try:
            period_name = original_record.get("period_name", "")
            country_code = original_record.get("country_code", "")
            comment = original_record.get("comment", "")
            start_date_epoch = original_record.get("start_date")
            end_date_epoch = original_record.get("end_date")
            
            if not start_date_epoch or not end_date_epoch:
                return False, None, "Missing start_date or end_date in original record"
            
            # Parse original dates
            start_dt = datetime.datetime.fromtimestamp(start_date_epoch, tz=datetime.timezone.utc)
            end_dt = datetime.datetime.fromtimestamp(end_date_epoch, tz=datetime.timezone.utc)
            
            # Extract month/day from original dates
            start_month = start_dt.month
            start_day = start_dt.day
            start_hour = start_dt.hour
            start_minute = start_dt.minute
            
            end_month = end_dt.month
            end_day = end_dt.day
            end_hour = end_dt.hour
            end_minute = end_dt.minute
            
            # Calculate next year (year + 1)
            next_year = start_dt.year + 1
            
            # Handle year-spanning holidays (e.g., Dec 31 - Jan 1)
            if end_month < start_month or (end_month == start_month and end_day < start_day):
                # Holiday spans across years
                new_start_dt = self.safe_create_datetime(
                    next_year, start_month, start_day, start_hour, start_minute,
                    tzinfo=datetime.timezone.utc
                )
                new_end_dt = self.safe_create_datetime(
                    next_year + 1, end_month, end_day, end_hour, end_minute,
                    tzinfo=datetime.timezone.utc
                )
            else:
                # Normal holiday within the same year
                new_start_dt = self.safe_create_datetime(
                    next_year, start_month, start_day, start_hour, start_minute,
                    tzinfo=datetime.timezone.utc
                )
                new_end_dt = self.safe_create_datetime(
                    next_year, end_month, end_day, end_hour, end_minute,
                    tzinfo=datetime.timezone.utc
                )
            
            # Convert to epoch timestamps
            new_start_epoch = int(round(new_start_dt.timestamp()))
            new_end_epoch = int(round(new_end_dt.timestamp()))
            
            # Validate date range
            if new_end_epoch <= new_start_epoch:
                return False, None, f"Invalid date range for next year occurrence"
            
            # Check if period already exists (avoid duplicates)
            # Query by period_name and country_code, then check dates in Python
            query = {
                "period_name": period_name,
                "country_code": country_code,
            }
            
            existing = collection.data.query(query=json.dumps(query))
            if existing:
                # Check if any existing record has the same date pattern for next year
                pattern_start = self.safe_create_datetime(next_year, start_month, start_day, 0, 0, 0, tzinfo=datetime.timezone.utc).timestamp()
                pattern_end = self.safe_create_datetime(next_year, start_month, start_day, 23, 59, 59, tzinfo=datetime.timezone.utc).timestamp()
                
                for existing_record in existing:
                    existing_start = existing_record.get("start_date")
                    if existing_start and pattern_start <= int(existing_start) <= pattern_end:
                        # Period already exists for next year
                        logger.debug(f'Next year occurrence already exists for period_name="{period_name}", country_code="{country_code}", year={next_year}, skipping creation.')
                        return False, None, None  # Not an error, just already exists
            
            # Create new record for next year
            current_time = round(time.time(), 0)
            
            # Update comment for next year's occurrence if it contains an import reference
            # If comment is "Imported from XX for YYYY", update to next year
            updated_comment = comment
            if comment and "Imported from" in comment and "for" in comment:
                # Extract year from comment if present and update it
                import re
                year_match = re.search(r'for (\d{4})', comment)
                if year_match:
                    original_year = int(year_match.group(1))
                    updated_comment = comment.replace(f'for {original_year}', f'for {next_year}')
                else:
                    # If no year found, append next year info
                    updated_comment = f"{comment} (auto-generated for {next_year})"
            elif comment:
                # For other comments, append auto-generated note
                updated_comment = f"{comment} (auto-generated recurring occurrence)"
            
            new_record = {
                "period_name": period_name,
                "start_date": new_start_epoch,
                "end_date": new_end_epoch,
                "comment": updated_comment,
                "country_code": country_code,
                "is_recurring": True,  # Keep recurring flag
                "src_user": username,
                "time_created": current_time,
                "time_updated": current_time,
            }
            
            # Insert new record
            kv_response = collection.data.insert(json.dumps(new_record))
            new_key = kv_response.get("_key")
            new_record["_key"] = new_key
            
            # Create maintenance KDB record for next year's occurrence
            maintenance_key = None
            maintenance_success, maintenance_key, maintenance_error = self.create_maintenance_kdb_record(
                service, period_name, new_start_epoch, new_end_epoch, updated_comment, username
            )
            if maintenance_success and maintenance_key:
                # Update bank holiday record with maintenance KDB key
                new_record["maintenance_kdb_key"] = maintenance_key
                try:
                    collection.data.update(str(new_key), json.dumps(new_record))
                except Exception as e:
                    logger.warning(f'Failed to update next year bank holiday record with maintenance_kdb_key, exception="{str(e)}"')
            elif not maintenance_success:
                # Log warning but don't fail - maintenance KDB is optional
                logger.warning(f'Failed to create maintenance KDB record for next year occurrence, error="{maintenance_error}"')
            
            logger.info(f'Created next year occurrence for recurring holiday: period_name="{period_name}", year={next_year}, key={new_key}')
            return True, new_record, None
            
        except Exception as e:
            error_msg = f'Failed to create next year occurrence: {str(e)}'
            logger.error(error_msg)
            return False, None, error_msg

    def get_resource_group_desc_bank_holidays(self, request_info, **kwargs):
        response = {
            "resource_group_name": "bank_holidays/admin",
            "resource_group_desc": "The bank holidays feature allows admins to preset bank holiday periods which will prevent alerts from triggering, similar to maintenance mode. (admin operations)",
        }

        return {"payload": response, "status": 200}

    # Create a new bank holiday period
    def post_create(self, request_info, **kwargs):
        describe = False
        period_name = None
        start_date = None
        end_date = None
        comment = None
        country_code = None
        is_recurring = False
        time_format = "epochtime"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                period_name = resp_dict.get("period_name")
                start_date = resp_dict.get("start_date")
                end_date = resp_dict.get("end_date")
                comment = resp_dict.get("comment")
                country_code = resp_dict.get("country_code")
                is_recurring = resp_dict.get("is_recurring", False)
                time_format = resp_dict.get("time_format", "epochtime")
                update_comment = resp_dict.get("update_comment") or "API update"
        else:
            describe = False

        if describe:
            response = {
                "describe": "This endpoint creates a new bank holiday period. It requires a POST call with the following information:",
                "resource_desc": "Create a new bank holiday period",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/bank_holidays/admin/create" body=\'{"start_date": 1704067200, "end_date": 1704153600, "period_name": "New Year", "comment": "New Year holiday"}\'',
                "options": [
                    {
                        "start_date": "MANDATORY: start date in epoch timestamp (or datestring format if time_format=datestring)",
                        "end_date": "MANDATORY: end date in epoch timestamp (or datestring format if time_format=datestring)",
                        "period_name": "OPTIONAL: name/description for the bank holiday period",
                        "comment": "OPTIONAL: comment about the bank holiday",
                        "country_code": "OPTIONAL: country code for imported holidays (e.g., US, UK, FR)",
                        "is_recurring": "OPTIONAL: whether this holiday repeats yearly (default: false)",
                        "time_format": "OPTIONAL: time format, defaults to epochtime, alternative is datestring (YYYY-MM-DDTHH:MM)",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Validate required fields
        if not start_date or not end_date:
            return {
                "payload": {"response": "start_date and end_date are mandatory fields"},
                "status": 400,
            }

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        username = request_info.user

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        collection_name = "kv_trackme_bank_holidays"
        collection = service.kvstore[collection_name]

        # Convert dates if needed
        if time_format == "datestring":
            try:
                start_date_dt = datetime.datetime.strptime(str(start_date), "%Y-%m-%dT%H:%M")
                start_date_dt = start_date_dt.replace(tzinfo=datetime.timezone.utc)
                start_date = int(round(float(start_date_dt.timestamp())))
            except Exception as e:
                return {
                    "payload": {
                        "response": f'Exception converting start_date datestring, exception="{str(e)}"'
                    },
                    "status": 400,
                }
            try:
                end_date_dt = datetime.datetime.strptime(str(end_date), "%Y-%m-%dT%H:%M")
                end_date_dt = end_date_dt.replace(tzinfo=datetime.timezone.utc)
                end_date = int(round(float(end_date_dt.timestamp())))
            except Exception as e:
                return {
                    "payload": {
                        "response": f'Exception converting end_date datestring, exception="{str(e)}"'
                    },
                    "status": 400,
                }
        else:
            try:
                start_date = int(round(float(start_date)))
                end_date = int(round(float(end_date)))
            except Exception as e:
                return {
                    "payload": {
                        "response": f'Exception converting dates to integers, exception="{str(e)}"'
                    },
                    "status": 400,
                }

        # Validate date range
        if end_date <= start_date:
            return {
                "payload": {"response": "end_date must be after start_date"},
                "status": 400,
            }

        # Check for duplicate periods (same date range)
        # This prevents duplicates when the health manager creates periods that were auto-created
        # by create_next_year_recurring_period
        try:
            # Query for periods with overlapping date ranges
            # Check if any existing period overlaps with the new period's date range
            query = {}
            existing = collection.data.query(query=json.dumps(query))
            
            for existing_record in existing:
                existing_start = existing_record.get("start_date")
                existing_end = existing_record.get("end_date")
                
                if existing_start and existing_end:
                    # Check if date ranges overlap (same day tolerance)
                    # Convert to datetime for day-level comparison
                    existing_start_dt = datetime.datetime.fromtimestamp(existing_start, tz=datetime.timezone.utc)
                    existing_end_dt = datetime.datetime.fromtimestamp(existing_end, tz=datetime.timezone.utc)
                    new_start_dt = datetime.datetime.fromtimestamp(start_date, tz=datetime.timezone.utc)
                    new_end_dt = datetime.datetime.fromtimestamp(end_date, tz=datetime.timezone.utc)
                    
                    # Check if dates are on the same day (tolerance for time differences)
                    if (existing_start_dt.year == new_start_dt.year and
                        existing_start_dt.month == new_start_dt.month and
                        existing_start_dt.day == new_start_dt.day and
                        existing_end_dt.year == new_end_dt.year and
                        existing_end_dt.month == new_end_dt.month and
                        existing_end_dt.day == new_end_dt.day):
                        # Duplicate found - same date range
                        existing_key = existing_record.get("_key", "unknown")
                        logger.info(f'Duplicate bank holiday period detected (same date range), existing key={existing_key}, skipping creation.')
                        return {
                            "payload": {
                                "response": "A bank holiday period with the same date range already exists",
                                "existing_key": existing_key,
                            },
                            "status": 409,  # Conflict status code
                        }
        except Exception as e:
            # Log but don't fail - duplicate check is best effort
            logger.warning(f'Error checking for duplicate periods, exception="{str(e)}", proceeding with creation.')

        # Create record
        current_time = round(time.time(), 0)
        record = {
            "period_name": period_name or "",
            "start_date": start_date,
            "end_date": end_date,
            "comment": comment or "",
            "country_code": country_code or "",
            "is_recurring": self.safe_convert_boolean(is_recurring, default=False),
            "src_user": username,
            "time_created": current_time,
            "time_updated": current_time,
        }

        try:
            kv_response = collection.data.insert(json.dumps(record))
            key = kv_response.get("_key")
            record["_key"] = key
        except Exception as e:
            logger.error(f'Failed to insert bank holiday record, exception="{str(e)}"')
            return {
                "payload": {"response": f'Failed to create bank holiday period, exception="{str(e)}"'},
                "status": 500,
            }

        # Create maintenance KDB record for SLA calculations
        maintenance_key = None
        maintenance_success, maintenance_key, maintenance_error = self.create_maintenance_kdb_record(
            service, period_name or "Bank Holiday", start_date, end_date, comment, username
        )
        if maintenance_success and maintenance_key:
            # Update bank holiday record with maintenance KDB key
            record["maintenance_kdb_key"] = maintenance_key
            try:
                collection.data.update(str(key), json.dumps(record))
            except Exception as e:
                logger.warning(f'Failed to update bank holiday record with maintenance_kdb_key, exception="{str(e)}"')
        elif not maintenance_success:
            # Log warning but don't fail - maintenance KDB is optional for functionality
            logger.warning(f'Failed to create maintenance KDB record for bank holiday, error="{maintenance_error}"')

        # Record audit event
        trackme_audit_event(
            request_info.system_authtoken,
            request_info.server_rest_uri,
            "all",
            username,
            "success",
            "create bank holiday period",
            "all",
            "all",
            str(json.dumps(record, indent=1)),
            f'Bank holiday period was created successfully by user="{username}"',
            str(update_comment),
        )

        logger.info(f'Bank holiday period created, record="{json.dumps(record, indent=2)}"')

        # If recurring, create next year's occurrence immediately for consistency
        # But only if the period is for current year or past - don't create year+2 if period is already for next year
        next_year_record = None
        is_recurring_bool = self.safe_convert_boolean(is_recurring, default=False)
        if is_recurring_bool:
            # Check if this period is already for next year (or beyond)
            current_year = datetime.datetime.now(datetime.timezone.utc).year
            period_year = datetime.datetime.fromtimestamp(start_date, tz=datetime.timezone.utc).year
            
            # Only create next year's occurrence if the period is for current year or past
            # If it's already for next year, don't create year+2
            if period_year <= current_year:
                success, next_year_record, error_msg = self.create_next_year_recurring_period(
                    collection, service, record, username
                )
                if success and next_year_record:
                    logger.info(f'Created next year occurrence for recurring holiday: period_name="{period_name}", key={next_year_record.get("_key")}')
                elif error_msg:
                    logger.warning(f'Failed to create next year occurrence for recurring holiday: period_name="{period_name}", error="{error_msg}"')
            else:
                # Period is already for next year or beyond, skip auto-creating year+2
                logger.debug(f'Skipping auto-creation of next year occurrence for period already in year {period_year} (current year: {current_year})')

        # Return the original record (for backward compatibility) and optionally next_year_record
        response_payload = record.copy()
        if next_year_record:
            response_payload["next_year_record"] = next_year_record

        return {"payload": response_payload, "status": 200}

    # Update an existing bank holiday period
    def post_update(self, request_info, **kwargs):
        describe = False
        record_key = None
        period_name = None
        start_date = None
        end_date = None
        comment = None
        country_code = None
        is_recurring = None
        time_format = "epochtime"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                record_key = resp_dict.get("_key") or resp_dict.get("record_key")
                period_name = resp_dict.get("period_name")
                start_date = resp_dict.get("start_date")
                end_date = resp_dict.get("end_date")
                comment = resp_dict.get("comment")
                country_code = resp_dict.get("country_code")
                is_recurring = resp_dict.get("is_recurring")
                time_format = resp_dict.get("time_format", "epochtime")
                update_comment = resp_dict.get("update_comment") or "API update"
        else:
            describe = False

        if describe:
            response = {
                "describe": "This endpoint updates an existing bank holiday period. It requires a POST call with the following information:",
                "resource_desc": "Update an existing bank holiday period",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/bank_holidays/admin/update" body=\'{"_key": "123", "period_name": "Updated Name"}\'',
                "options": [
                    {
                        "_key": "MANDATORY: the record key of the bank holiday period to update",
                        "period_name": "OPTIONAL: updated name/description",
                        "start_date": "OPTIONAL: updated start date",
                        "end_date": "OPTIONAL: updated end date",
                        "comment": "OPTIONAL: updated comment",
                        "country_code": "OPTIONAL: updated country code",
                        "is_recurring": "OPTIONAL: updated recurring flag",
                        "time_format": "OPTIONAL: time format for dates, defaults to epochtime",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        if not record_key:
            return {
                "payload": {"response": "_key or record_key is mandatory"},
                "status": 400,
            }

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        username = request_info.user

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        collection_name = "kv_trackme_bank_holidays"
        collection = service.kvstore[collection_name]

        # Get existing record
        try:
            existing_record = collection.data.query_by_id(str(record_key))
        except Exception as e:
            logger.error(f'Failed to query bank holiday record, exception="{str(e)}"')
            return {
                "payload": {"response": f'Bank holiday period not found, key="{record_key}"'},
                "status": 404,
            }

        # Update fields if provided
        if period_name is not None:
            existing_record["period_name"] = period_name
        if comment is not None:
            existing_record["comment"] = comment
        if country_code is not None:
            existing_record["country_code"] = country_code
        if is_recurring is not None:
            existing_record["is_recurring"] = self.safe_convert_boolean(is_recurring, default=False)

        # Convert and update dates if provided
        if start_date is not None or end_date is not None:
            if time_format == "datestring":
                if start_date:
                    try:
                        start_date_dt = datetime.datetime.strptime(str(start_date), "%Y-%m-%dT%H:%M")
                        start_date_dt = start_date_dt.replace(tzinfo=datetime.timezone.utc)
                        start_date = int(round(float(start_date_dt.timestamp())))
                    except Exception as e:
                        return {
                            "payload": {
                                "response": f'Exception converting start_date datestring, exception="{str(e)}"'
                            },
                            "status": 400,
                        }
                if end_date:
                    try:
                        end_date_dt = datetime.datetime.strptime(str(end_date), "%Y-%m-%dT%H:%M")
                        end_date_dt = end_date_dt.replace(tzinfo=datetime.timezone.utc)
                        end_date = int(round(float(end_date_dt.timestamp())))
                    except Exception as e:
                        return {
                            "payload": {
                                "response": f'Exception converting end_date datestring, exception="{str(e)}"'
                            },
                            "status": 400,
                        }
            else:
                if start_date:
                    try:
                        start_date = int(round(float(start_date)))
                    except Exception as e:
                        return {
                            "payload": {
                                "response": f'Exception converting start_date, exception="{str(e)}"'
                            },
                            "status": 400,
                        }
                if end_date:
                    try:
                        end_date = int(round(float(end_date)))
                    except Exception as e:
                        return {
                            "payload": {
                                "response": f'Exception converting end_date, exception="{str(e)}"'
                            },
                            "status": 400,
                        }

            # Use existing values if not provided
            final_start = start_date if start_date is not None else existing_record.get("start_date")
            final_end = end_date if end_date is not None else existing_record.get("end_date")

            # Validate date range
            if final_end <= final_start:
                return {
                    "payload": {"response": "end_date must be after start_date"},
                    "status": 400,
                }

            if start_date is not None:
                existing_record["start_date"] = start_date
            if end_date is not None:
                existing_record["end_date"] = end_date

        existing_record["time_updated"] = round(time.time(), 0)

        # Update record
        try:
            collection.data.update(str(record_key), json.dumps(existing_record))
        except Exception as e:
            logger.error(f'Failed to update bank holiday record, exception="{str(e)}"')
            return {
                "payload": {"response": f'Failed to update bank holiday period, exception="{str(e)}"'},
                "status": 500,
            }

        # Update maintenance KDB record if it exists
        maintenance_key = existing_record.get("maintenance_kdb_key")
        if maintenance_key:
            # Get final values for maintenance update
            final_period_name = existing_record.get("period_name", "")
            final_start = existing_record.get("start_date")
            final_end = existing_record.get("end_date")
            final_comment = existing_record.get("comment", "")
            
            if final_start and final_end:
                maintenance_success, maintenance_error = self.update_maintenance_kdb_record(
                    service, maintenance_key, final_period_name, final_start, final_end, final_comment, username
                )
                if not maintenance_success:
                    # Log warning but don't fail - maintenance KDB update is optional
                    logger.warning(f'Failed to update maintenance KDB record for bank holiday, error="{maintenance_error}"')
        else:
            # No maintenance KDB record exists, create one
            final_period_name = existing_record.get("period_name", "")
            final_start = existing_record.get("start_date")
            final_end = existing_record.get("end_date")
            final_comment = existing_record.get("comment", "")
            
            if final_start and final_end:
                maintenance_success, maintenance_key, maintenance_error = self.create_maintenance_kdb_record(
                    service, final_period_name, final_start, final_end, final_comment, username
                )
                if maintenance_success and maintenance_key:
                    # Update bank holiday record with maintenance KDB key
                    existing_record["maintenance_kdb_key"] = maintenance_key
                    try:
                        collection.data.update(str(record_key), json.dumps(existing_record))
                    except Exception as e:
                        logger.warning(f'Failed to update bank holiday record with maintenance_kdb_key, exception="{str(e)}"')
                elif not maintenance_success:
                    logger.warning(f'Failed to create maintenance KDB record for bank holiday, error="{maintenance_error}"')

        # Record audit event
        trackme_audit_event(
            request_info.system_authtoken,
            request_info.server_rest_uri,
            "all",
            username,
            "success",
            "update bank holiday period",
            "all",
            "all",
            str(json.dumps(existing_record, indent=1)),
            f'Bank holiday period was updated successfully by user="{username}"',
            str(update_comment),
        )

        logger.info(f'Bank holiday period updated, record="{json.dumps(existing_record, indent=2)}"')

        return {"payload": existing_record, "status": 200}

    # Delete bank holiday period(s)
    def post_delete(self, request_info, **kwargs):
        describe = False
        record_keys = None

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                # Support both single key and list of keys
                if "_key" in resp_dict:
                    record_keys = [resp_dict["_key"]]
                elif "record_key" in resp_dict:
                    record_keys = [resp_dict["record_key"]]
                elif "record_keys" in resp_dict:
                    record_keys = resp_dict["record_keys"]
                    if isinstance(record_keys, str):
                        record_keys = [k.strip() for k in record_keys.split(",") if k.strip()]
                elif "keys" in resp_dict:
                    record_keys = resp_dict["keys"]
                    if isinstance(record_keys, str):
                        record_keys = [k.strip() for k in record_keys.split(",") if k.strip()]
                update_comment = resp_dict.get("update_comment") or "API update"
        else:
            describe = False

        if describe:
            response = {
                "describe": "This endpoint deletes bank holiday period(s). It requires a POST call with the following information:",
                "resource_desc": "Delete bank holiday period(s)",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/bank_holidays/admin/delete" body=\'{"_key": "123"}\'',
                "options": [
                    {
                        "_key": "MANDATORY: the record key of the bank holiday period to delete (or use record_keys for multiple)",
                        "record_keys": "OPTIONAL: comma-separated list of record keys to delete multiple periods",
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        if not record_keys:
            return {
                "payload": {"response": "_key or record_keys is mandatory"},
                "status": 400,
            }

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        username = request_info.user

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        collection_name = "kv_trackme_bank_holidays"
        collection = service.kvstore[collection_name]

        # Delete records
        deleted_count = 0
        failed_count = 0
        errors = []

        for key in record_keys:
            try:
                # Get record before deletion for audit and maintenance KDB cleanup
                try:
                    record = collection.data.query_by_id(str(key))
                except Exception as e:
                    errors.append(f'Record with key="{key}" not found')
                    failed_count += 1
                    continue
                
                # Delete maintenance KDB record if it exists (only if period hasn't passed)
                maintenance_key = record.get("maintenance_kdb_key")
                if maintenance_key:
                    period_name = record.get("period_name", "Bank Holiday")
                    maintenance_success, maintenance_error = self._delete_maintenance_kdb_record(
                        service, maintenance_key, period_name
                    )
                    if not maintenance_success:
                        # Log warning but don't fail - maintenance KDB deletion is optional
                        logger.warning(f'Failed to delete maintenance KDB record for bank holiday, error="{maintenance_error}"')

                collection.data.delete(json.dumps({"_key": str(key)}))
                deleted_count += 1

                # Record audit event
                trackme_audit_event(
                    request_info.system_authtoken,
                    request_info.server_rest_uri,
                    "all",
                    username,
                    "success",
                    "delete bank holiday period",
                    "all",
                    "all",
                    str(json.dumps(record, indent=1)),
                    f'Bank holiday period was deleted successfully by user="{username}"',
                    str(update_comment),
                )

                logger.info(f'Bank holiday period deleted, key="{key}"')
            except Exception as e:
                logger.error(f'Failed to delete bank holiday record, key="{key}", exception="{str(e)}"')
                errors.append(f'Failed to delete record with key="{key}": {str(e)}')
                failed_count += 1

        response = {
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "errors": errors if errors else None,
        }

        if failed_count > 0 and deleted_count == 0:
            status = 500
        elif failed_count > 0:
            status = 207  # Multi-status
        else:
            status = 200

        return {"payload": response, "status": status}

    # Delete all bank holiday periods
    def post_delete_all(self, request_info, **kwargs):
        describe = False
        update_comment = "API update"

        # Retrieve from data
        try:
            resp_dict = json.loads(str(request_info.raw_args["payload"]))
        except Exception as e:
            resp_dict = None

        if resp_dict is not None:
            describe = trackme_parse_describe_flag(request_info)
            if not describe:
                update_comment = resp_dict.get("update_comment") or "API update"
        else:
            describe = False

        if describe:
            response = {
                "describe": "This endpoint deletes all bank holiday periods. It requires a POST call with no data.",
                "resource_desc": "Delete all bank holiday periods",
                "resource_spl_example": '| trackme mode=post url="/services/trackme/v2/bank_holidays/admin/delete_all"',
                "options": [
                    {
                        "update_comment": "OPTIONAL: a comment for the update, comments are added to the audit record, if unset will be defined to: API update",
                    }
                ],
            }
            return {"payload": response, "status": 200}

        # Get service
        service = client.connect(
            owner="nobody",
            app="trackme",
            port=request_info.server_rest_port,
            token=request_info.system_authtoken,
            timeout=600,
        )

        username = request_info.user

        # set loglevel
        loglevel = trackme_getloglevel(
            request_info.system_authtoken, request_info.server_rest_port
        )
        logger.setLevel(loglevel)

        collection_name = "kv_trackme_bank_holidays"
        collection = service.kvstore[collection_name]

        deleted_count = 0
        errors = []

        try:
            # Get all records
            all_records = collection.data.query()
            
            if not all_records:
                return {
                    "payload": {"response": "No bank holiday periods found to delete", "deleted_count": 0},
                    "status": 200,
                }

            # Delete each record
            for record in all_records:
                try:
                    record_key = record.get("_key")
                    if record_key:
                        # Delete maintenance KDB record if it exists (only if period hasn't passed)
                        maintenance_key = record.get("maintenance_kdb_key")
                        if maintenance_key:
                            period_name = record.get("period_name", "Bank Holiday")
                            maintenance_success, maintenance_error = self._delete_maintenance_kdb_record(
                                service, maintenance_key, period_name
                            )
                            if not maintenance_success:
                                # Log warning but don't fail - maintenance KDB deletion is optional
                                logger.warning(f'Failed to delete maintenance KDB record for bank holiday, error="{maintenance_error}"')
                        
                        delete_payload = json.dumps({"_key": record_key})
                        collection.data.delete(delete_payload)
                        deleted_count += 1
                except Exception as e:
                    error_msg = f'Failed to delete record with key="{record.get("_key", "unknown")}": {str(e)}'
                    logger.error(error_msg)
                    errors.append(error_msg)

            # Record audit event
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                "all",
                username,
                "success" if deleted_count > 0 and len(errors) == 0 else "partial",
                "delete all bank holidays",
                "all",
                "all",
                f'deleted_count={deleted_count}, errors={len(errors)}',
                f'All bank holidays deleted by user="{username}"',
                str(update_comment),
            )

            response = {
                "response": f"Successfully deleted {deleted_count} bank holiday period(s)",
                "deleted_count": deleted_count,
                "errors": errors if errors else None,
            }

            status = 200
            if errors:
                status = 207  # Multi-status if some deletions failed

            return {"payload": response, "status": status}

        except Exception as e:
            error_msg = f'Failed to delete all bank holidays: {str(e)}'
            logger.error(error_msg)
            
            # Record audit event for failure
            trackme_audit_event(
                request_info.system_authtoken,
                request_info.server_rest_uri,
                "all",
                username,
                "failure",
                "delete all bank holidays",
                "all",
                "all",
                f'error={str(e)}',
                f'Failed to delete all bank holidays by user="{username}": {str(e)}',
                str(update_comment),
            )
            
            return {
                "payload": {"response": error_msg, "deleted_count": 0},
                "status": 500,
            }

