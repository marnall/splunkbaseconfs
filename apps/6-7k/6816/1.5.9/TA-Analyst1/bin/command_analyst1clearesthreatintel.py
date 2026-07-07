"""
Splunk custom generating command to clear Analyst1 ES threat intelligence from KV store.

This command removes all Analyst1 threat indicators from Enterprise Security collections.
It operates with safety mechanisms including dry-run mode by default and explicit confirmation
requirements for actual deletions.
"""
import ta_analyst1_declare  # noqa: F401

import sys
import json
import traceback
from datetime import datetime
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option
from solnlib.utils import is_true
from analyst1_logging import get_logger
from analyst1_helpers.kvstore import CollectionManager, KVStoreUnavailbleError


# ES collections that store Analyst1 threat intelligence
ES_COLLECTIONS = [
    "analyst1_es_ip_intel",
    "analyst1_es_file_intel",
    "analyst1_es_email_intel",
    "analyst1_es_http_intel"
]


@Configuration(generating=True)
class Analyst1ClearESThreatIntel(GeneratingCommand):
    """
    Generating command to clear Analyst1 threat intelligence from ES collections.

    Usage:
        | analyst1clearesthreatintel                          # Dry-run mode (default)
        | analyst1clearesthreatintel confirm=true             # Execute deletion
        | analyst1clearesthreatintel confirm=true verbose=true  # Execute with detailed output

    Options:
        dry_run: Preview mode without actual deletion (default: true)
        confirm: Explicit confirmation required for deletion (default: false)
        verbose: Enable detailed output messages (default: false)
    """

    dry_run = Option(name="dry_run", default=True, require=False)
    confirm = Option(name="confirm", default=False, require=False)
    verbose = Option(name="verbose", default=False, require=False)

    def _write_error(self, msg):
        """Log error message to Splunk UI."""
        self.logger.error(msg)
        self.write_error(f"{msg}. See ta_analyst1_clearesthreatintel.log for more details.")

    def _validate_permissions(self):
        """
        Validate user has access to all ES collections.

        Returns:
            tuple: (success: bool, error_message: str or None)
        """
        missing_collections = []

        try:
            for collection_name in ES_COLLECTIONS:
                try:
                    mgr = CollectionManager(
                        collection_name=collection_name,
                        service=self.service
                    )
                    # Test access by checking if collection exists
                    _ = mgr.collection
                except Exception as e:
                    self.logger.warning(
                        f"message=collection_access_check | Collection may not exist or is inaccessible: "
                        f"collection={collection_name} error={str(e)}"
                    )
                    missing_collections.append(collection_name)

            if missing_collections:
                return False, f"Cannot access collections: {', '.join(missing_collections)}"

            return True, None

        except Exception as e:
            return False, f"Permission validation failed: {str(e)}"

    def _get_deletion_stats(self):
        """
        Get count of indicators that would be deleted from each collection.

        Returns:
            dict: Mapping of collection_name to count of matching records
        """
        stats = {}
        query = {"threat_key": {"$regex": "^analyst1_"}}

        for collection_name in ES_COLLECTIONS:
            try:
                mgr = CollectionManager(
                    collection_name=collection_name,
                    service=self.service
                )

                # Query to count matching records
                query_json = json.dumps(query)
                results = mgr.collection.data.query(query=query_json)
                count = len(results)
                stats[collection_name] = count

                if self.verbose_mode:
                    self.logger.info(
                        f"message=deletion_stats | Found indicators: "
                        f"collection={collection_name} count={count}"
                    )

            except Exception as e:
                self.logger.error(
                    f"message=stats_collection_error | Failed to get stats: "
                    f"collection={collection_name} error={str(e)}"
                )
                stats[collection_name] = -1  # Error indicator

        return stats

    def _perform_deletion(self, collection_name):
        """
        Execute deletion of Analyst1 indicators from a single collection.

        Args:
            collection_name: Name of the collection to clear

        Returns:
            tuple: (success: bool, count: int, error_message: str or None)
        """
        try:
            mgr = CollectionManager(
                collection_name=collection_name,
                service=self.service
            )

            # Query to match only Analyst1 threat keys
            query = {"threat_key": {"$regex": "^analyst1_"}}

            # Get count before deletion
            query_json = json.dumps(query)
            results = mgr.collection.data.query(query=query_json)
            count = len(results)

            if count == 0:
                self.logger.info(
                    f"message=no_records_to_delete | No records to delete: collection={collection_name}"
                )
                return True, 0, None

            # Perform deletion
            mgr.delete_batch(query)

            self.logger.info(
                f"message=deletion_success | Deleted records: "
                f"collection={collection_name} count={count}"
            )

            return True, count, None

        except KVStoreUnavailbleError as e:
            error_msg = f"KVStore unavailable: {str(e)}"
            self.logger.error(
                f"message=kvstore_unavailable | collection={collection_name} error={error_msg}"
            )
            return False, 0, error_msg

        except Exception as e:
            error_msg = f"Deletion failed: {str(e)}"
            self.logger.error(
                f"message=deletion_error | collection={collection_name} error={traceback.format_exc()}"
            )
            return False, 0, error_msg

    def _generate_output(self, collection_name, action, count, status, message=None):
        """
        Generate output event for the command results.

        Args:
            collection_name: Name of the collection
            action: Action performed (would_delete or deleted)
            count: Number of indicators affected
            status: Status of the operation (success or error)
            message: Optional detailed message

        Returns:
            dict: Event dictionary for Splunk output
        """
        event = {
            "collection": collection_name,
            "action": action,
            "count": count,
            "status": status,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        if message:
            event["message"] = message

        return event

    def generate(self):
        """
        Main entry point for the generating command.

        Yields:
            dict: Events containing deletion statistics or results
        """
        try:
            # Initialize logger
            self.session_key = self.search_results_info.auth_token
            self.logger = get_logger("ta_analyst1_clearesthreatintel")

            # Parse boolean options
            self.dry_run_mode = is_true(self.dry_run)
            self.confirm_mode = is_true(self.confirm)
            self.verbose_mode = is_true(self.verbose)

            # Log command start
            mode = "DRY-RUN" if self.dry_run_mode else "PRODUCTION"
            self.logger.info(
                f"message=command_start | Starting ES threat intelligence cleanup: "
                f"mode={mode} confirm={self.confirm_mode} verbose={self.verbose_mode}"
            )

            # Validate permissions
            if self.verbose_mode:
                self.logger.info("message=validating_permissions | Validating access to ES collections")

            valid, error_msg = self._validate_permissions()
            if not valid:
                error_message = f"Permission validation failed: {error_msg}"
                self.logger.error(f"message=permission_error | {error_message}")
                yield self._generate_output(
                    collection_name="ALL",
                    action="validation",
                    count=0,
                    status="error",
                    message=error_message
                )
                return

            # Safety check: require confirm=true for actual deletion
            if not self.dry_run_mode and not self.confirm_mode:
                error_message = (
                    "Deletion requires explicit confirmation. "
                    "Use: | analyst1clearesthreatintel confirm=true"
                )
                self.logger.warning(f"message=confirmation_required | {error_message}")
                yield self._generate_output(
                    collection_name="ALL",
                    action="confirmation_required",
                    count=0,
                    status="error",
                    message=error_message
                )
                return

            # Get deletion statistics
            if self.verbose_mode:
                self.logger.info("message=gathering_stats | Gathering deletion statistics")

            stats = self._get_deletion_stats()
            total_indicators = sum(count for count in stats.values() if count >= 0)

            if self.verbose_mode:
                self.logger.info(
                    f"message=total_stats | Total indicators to process: count={total_indicators}"
                )

            # Dry-run mode: return statistics without deletion
            if self.dry_run_mode:
                self.logger.info("message=dry_run_mode | Running in dry-run mode (no actual deletion)")

                for collection_name, count in stats.items():
                    if count < 0:
                        # Error getting stats
                        yield self._generate_output(
                            collection_name=collection_name,
                            action="would_delete",
                            count=0,
                            status="error",
                            message="Failed to retrieve statistics"
                        )
                    else:
                        yield self._generate_output(
                            collection_name=collection_name,
                            action="would_delete",
                            count=count,
                            status="success",
                            message=f"Would delete {count} indicator(s) in dry-run mode"
                        )

                # Summary event
                yield self._generate_output(
                    collection_name="SUMMARY",
                    action="would_delete",
                    count=total_indicators,
                    status="success",
                    message=f"Dry-run complete. Use confirm=true to execute deletion of {total_indicators} indicator(s)"
                )

                self.logger.info(
                    f"message=dry_run_complete | Dry-run complete: total_indicators={total_indicators}"
                )
                return

            # Production mode: perform actual deletion
            self.logger.warning(
                f"message=production_deletion | Starting PRODUCTION deletion: "
                f"total_indicators={total_indicators} collections={len(ES_COLLECTIONS)}"
            )

            deletion_results = {}
            total_deleted = 0
            errors = []

            for collection_name in ES_COLLECTIONS:
                if self.verbose_mode:
                    self.logger.info(
                        f"message=deleting_collection | Processing deletion: collection={collection_name}"
                    )

                success, count, error_msg = self._perform_deletion(collection_name)
                deletion_results[collection_name] = (success, count, error_msg)

                if success:
                    total_deleted += count
                    yield self._generate_output(
                        collection_name=collection_name,
                        action="deleted",
                        count=count,
                        status="success",
                        message=f"Successfully deleted {count} indicator(s)"
                    )
                else:
                    errors.append(collection_name)
                    yield self._generate_output(
                        collection_name=collection_name,
                        action="deleted",
                        count=0,
                        status="error",
                        message=error_msg
                    )

            # Summary event
            if errors:
                summary_message = (
                    f"Deletion completed with errors. "
                    f"Deleted {total_deleted} indicator(s). "
                    f"Failed collections: {', '.join(errors)}"
                )
                summary_status = "partial_success"
            else:
                summary_message = f"Successfully deleted {total_deleted} indicator(s) from all collections"
                summary_status = "success"

            yield self._generate_output(
                collection_name="SUMMARY",
                action="deleted",
                count=total_deleted,
                status=summary_status,
                message=summary_message
            )

            self.logger.info(
                f"message=command_complete | Deletion complete: "
                f"total_deleted={total_deleted} errors={len(errors)}"
            )

        except KVStoreUnavailbleError as e:
            error_message = f"KVStore unavailable: {str(e)}"
            self.logger.error(f"message=kvstore_unavailable | {error_message}")
            self._write_error(error_message)
            yield self._generate_output(
                collection_name="ALL",
                action="error",
                count=0,
                status="error",
                message=error_message
            )

        except Exception as e:
            error_message = f"Command execution failed: {str(e)}"
            self.logger.error(
                f"message=command_error | {error_message}\n{traceback.format_exc()}"
            )
            self._write_error(error_message)
            yield self._generate_output(
                collection_name="ALL",
                action="error",
                count=0,
                status="error",
                message=error_message
            )


dispatch(Analyst1ClearESThreatIntel, sys.argv, sys.stdin, sys.stdout, __name__)
