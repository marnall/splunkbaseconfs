from abc import ABC, abstractmethod


class ServiceBase(ABC):
    """Abstract base class for service management."""

    ENDPOINT = None  # Must be defined in subclasses

    def __init__(self, name: str, session_key: str, initialize: bool = True):
        """Initialize the service with a name and session key."""
        self._session_key = session_key
        self.name = name

    @classmethod
    @abstractmethod
    def get_all(cls, session_key: str, *args, **kwargs):
        """Get all service from Splunk."""
        pass

    @classmethod
    @abstractmethod
    def create(cls, *args, **kwargs):
        """Create a new service in Splunk."""
        pass

    @abstractmethod
    def delete(self):
        """Delete the service from Splunk."""
        pass

    @abstractmethod
    def update(self, **kwargs):
        """Update the service in Splunk."""
        pass

    @abstractmethod
    def _init_properties(self):
        """Initialize the properties of the service."""
        pass
