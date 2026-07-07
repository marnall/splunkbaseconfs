from datetime import datetime, timezone


class WideEvent:
    """A class for building structured "wide" events for observability.

    This class facilitates the creation of a single, rich event object that captures
    various details of an operation, including context, a timeline of sub-events,
    and any errors that occurred.
    """

    def __init__(self, **common_attributes):
        """Initializes a WideEvent object.

        Args:
            **common_attributes: A dictionary of common attributes to initialize
                the event with.
        """
        self._event = {
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            **common_attributes,
            "timeline": [],
            "errors": [],
        }

    def add_attribute(self, key: str, value) -> None:
        """Adds a top-level attribute to the event.

        Args:
            key (str): The name of the attribute.
            value: The value of the attribute.
        """
        self._event[key] = value

        return None

    def add_context(self, key: str, value: dict) -> None:
        """Adds a dictionary of related attributes to the event.

        This is useful for grouping related data under a single key.

        Args:
            key (str): The name of the context.
            value (dict): A dictionary of attributes for the context.
        """
        self._event[key] = value

        return None

    def update_context(self, key: str, **attributes) -> None:
        """Updates a context dictionary with new attributes.

        If the context key does not exist or its value is not a dictionary,
        it will be created as an empty dictionary before updating.

        Args:
            key (str): The name of the context to update.
            **attributes: Keyword arguments representing the attributes to add
                or update in the context.
        """
        if key not in self._event or not isinstance(self._event.get(key), dict):
            self._event[key] = {}
        self._event[key].update(attributes)

        return None

    def add_timeline_event(self, name: str, **attributes) -> None:
        """Adds a timestamped event to the event's timeline.

        Args:
            name (str): The name of the timeline event.
            **attributes: Additional attributes to include with the timeline event.
        """
        event = {
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            "name": name,
            **attributes,
        }
        self._event["timeline"].append(event)

        return None

    def add_error_event(self, name: str, error: Exception, **attributes) -> None:
        """Adds a structured error to the event.

        Args:
            name (str): The name of the operation or context where the error
                occurred.
            error (Exception): The exception object.
            **attributes: Additional attributes to include with the error event.
        """
        error_event = {
            "timestamp": datetime.now(timezone.utc).replace(tzinfo=None).isoformat() + "Z",
            "name": name,
            "error_type": str(type(error)),
            "error_message": str(error),
            **attributes,
        }
        self._event["errors"].append(error_event)

        return None

    def build(self) -> dict:
        """Finalizes and returns the event dictionary.

        Calculates the total duration from instantiation to when build() is called
        and adds it as 'duration_seconds'.

        Returns:
            dict: The complete event data structure.
        """
        # Calculate duration
        start_time = datetime.fromisoformat(self._event["timestamp"][:-1])
        end_time = datetime.now(timezone.utc).replace(tzinfo=None)
        duration = (end_time - start_time).total_seconds()
        self._event["duration_seconds"] = duration

        return self._event
