# Streamer class
import logging
from datetime import datetime
from typing import Union

from lumulib.defender import connect
from lumulib.constants.globals import DATE_FORMAT, LABEL_RELEVANCES

logger = logging.getLogger("LumuStreamer")

MANDATORY_EVENTS = ["NewIncidentCreated", "IncidentUpdated"]
# These events don't have timestamp. If included as events of interest, we need to attach the processing timestamp to them
NON_TIMESTAMP_EVENTS = ["IncidentMarkedAsRead", "IncidentIntegrationsResponseUpdated", "IncidentCommentAdded"]

class Streamer(object):
    def __init__(self, company_key : str, events_of_interest=MANDATORY_EVENTS, proxies=None, labels : dict = None, include_muted_updates : bool = False):
        """
        Init method

        :param company_key: `str` Lumu Defender API key
        :param events_of interest: `list` List of the events to be processed by the Streamer
        :param collect_incident_context: `bool` Indicates if the streamer must collect the incident context
        :param hash_type: `str` Hash type to be collected (if applies)
        :param proxies: `dict` Proxy configuration (default None)
        :param labels: `dict` Start labels (if already present as a checkpoint)
        :param include_muted_updates: `bool` Indicates if the app will process muted updates (default False)
        """
        self.lumu = connect(company_key=company_key, proxies=proxies)
        self.init_labels(labels)
        self.options = {
            "events_of_interest": events_of_interest,
            "include_muted_updates": include_muted_updates
        }
    
    def init_labels(self, labels : dict = None):
        """
        Init labels.

        Generate a label dictionary with detailed information to be added in updates
        """
        logger.debug("Init labels")

        if labels is None:
            logger.debug("Collecting labels because None was received")
            self.labels = {}
            # Including "Unlabeled Activity"
            self.labels[0] = {
                "name": "Unlabeled Activity",
                "relevance": LABEL_RELEVANCES.get(1, "Low")
            }
            for label in self.lumu.labels:
                self.labels[label["id"]] = {
                    "name": label["name"],
                    "relevance": LABEL_RELEVANCES.get(label["relevance"], "Low")
                }
        else:
            logger.debug("Setting internal labels to received dictionary")
            # Let's iterate over each key: value pair. Keys are received in text
            new_labels = {}
            for key, value in labels.items():
                new_labels[int(key)] = value
            self.labels = new_labels
    
    def get_labels(self):
        """
        Return labels
        """
        return self.labels

    def consult_updates(self, offset : int):
        """
        Consult updates on Lumu incidents.

        :param offset: `int` Offset to consult updates
        :return: `tuple` New offset, dict with updates
        """
        # This methods calls the Consult updates endpoint to return the tuple
        logger.debug(f"Consulting updates with offset: { offset }")
        result = self.lumu.incident_updates.get(offset=offset)

        # The updates need to be processed based on the message type
        updates = self.process_updates(result["updates"])

        return result["offset"], updates
    
    def process_updates(self, updates):
        """
        Process updates received based on the message type

        :param updates: `list` List of dictionaries or updates
        """
        # Process each update message according to the message type
        logger.debug("Processing updates")

        # Procesed update will be stored here
        processed_updates = []

        updates_count = len(updates)
        if updates_count:
            logger.debug(f"Found { updates_count } updates")
            for update in updates:
                processed_update = self.process_update(update)
                if processed_update:
                    processed_updates.append(processed_update)
        else:
            logger.debug("No updates found")
        
        return processed_updates

    def process_update(self, update):
        """
        Process each update by separate.

        According to the message/update, enrich or leave as-is. Messages without 

        :param update: `dict` Dictionary with the update information
        """
        logger.debug("Processing update")
        # Checking the events of interest
        events_of_interest = self.options["events_of_interest"]
        # Verify if muted updates must be processed
        include_muted_updates = self.options["include_muted_updates"]

        update_type = list(update.keys())[0]
        logger.debug(f"Events of interest: { ', '.join(events_of_interest) }")
        if update_type in events_of_interest:
            logger.debug(f"Processing update of type { update_type }")
            if update_type in ["NewIncidentCreated", "IncidentUpdated"]:
                if not include_muted_updates:
                    # Discard if status is muted
                    is_muted = update[update_type]["incident"]["status"] == "muted"
                    if is_muted:
                        logger.debug(f"Message will be discarded. It belongs to a muted incident. Include muted updates is { include_muted_updates }")
                        return
        
                self.enrich(update)
            elif update_type in NON_TIMESTAMP_EVENTS:
                logger.debug(f"Adding timestamp to event { update_type }")
                current_time = datetime.utcnow()
                status_timestamp = current_time.strftime(DATE_FORMAT)
                update[update_type].update({
                    "statusTimestamp": status_timestamp
                })
            # Stats will be discarded
            elif update_type == "OpenIncidentsStatusUpdated":
                logger.debug(f"Discarding update of type { update_type }")
                # Set update to None
                update = None
        else:
            # The message is not included as event of interest
            update = None

        if update:
            # Add URL info to open incident in Lumu
            incident_id = update[update_type]["incidentId"] if update_type in NON_TIMESTAMP_EVENTS else update[update_type]["incident"]["id"]
            update["url"] = f"https://portal.lumu.io/compromise/incidents/show/{ incident_id }/detections"
            # Format update with the following structure
            new_update = {
                "eventType": update_type,
                "data": update[update_type],
                "url": update["url"]
            }
            return new_update
    
    def enrich(self, update):
        """
        Enrich update record adding:

        * Last contact details
        * Label information

        :param update: `dict` Dictionary with the update information
        """
        logger.debug("Collecting incident details")
        update_type = list(update.keys())[0]
        update_detail = update[update_type]

        # Enrich label information
        update_detail["incident"]["labelDistribution"] = self._populate_label_distribution(update_detail["incident"]["labelDistribution"])
        label_from_contact_summary = update_detail["contactSummary"].get("label", 0)
        update_detail["contactSummary"]["label"] = self._get_label_data(
            label_from_contact_summary
        )

        # Discard stats
        update[update_type].pop("openIncidentsStats", None)
    
    def _populate_label_distribution(self, incident_labels):
        """
        Method to populate label informacion for incident

        :param incident_labels: `dict` Dictionary with the distribution of contacts by label
        :return: `dict` with reformatted distribution
        """
        dist_ = {}
        for k, v in incident_labels.items():
            try:
                # If label not exists in self.labels, the call api to update
                if not self.labels.get(int(k), None):
                    # Label not exist in memory, query and save it
                    new_label = self.lumu.labels[k]
                    self.labels[new_label["id"]] = {
                        "name": new_label["name"],
                        "relevance": LABEL_RELEVANCES[new_label["relevance"]]
                    }

                dist_[self.labels[int(k)]['name']] = v
            except KeyError:
                dist_[k] = v

        return dist_
    
    def _get_label_data(self, label_id : Union[str, int]) -> dict:
        """
        Internal method to get label data from cache. If the record is not in cache, then
        collect it from Defender API

        Args:
            label_id (str|int): Lumu label ID

        Returns:
            A Dictionary with the danem and relevance of the label
        """
        # If the label information is not present in cache, we need to pull it from Lumu API
        if not self.labels.get(int(label_id), None):
            new_label = self.lumu.labels[label_id]
            # Populate cache with the label data
            self.labels[new_label["id"]] = {
                "name": new_label["name"],
                "relevance": new_label["relevance"]
            }
        
        return self.labels[int(label_id)]
    
