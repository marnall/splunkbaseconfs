from typing import Optional
from dataclasses import dataclass


@dataclass
class EventLog:
    selected: bool = False
    index: Optional[str] = None
    interval: Optional[int] = None
    start_date: Optional[str] = None
    disabled: bool = False


@dataclass
class AllEvent(EventLog):
    pass


@dataclass
class DnsEvent(EventLog):
    pass


@dataclass
class DlpEvent(EventLog):
    pass


@dataclass
class ProxyEvent(EventLog):
    pass


@dataclass
class FirewallEvent(EventLog):
    pass


@dataclass
class AuditEvent(EventLog):
    pass


@dataclass
class IntrusionEvent(EventLog):
    pass


@dataclass
class RavpnEvent(EventLog):
    pass


@dataclass
class ZtnaEvent(EventLog):
    pass


@dataclass
class ZtnaflowEvent(EventLog):
    pass


@dataclass
class FileeventEvent(EventLog):
    pass


@dataclass
class ZtnaenrollmentEvent(EventLog):
    pass


@dataclass
class NtgEvent(EventLog):
    pass