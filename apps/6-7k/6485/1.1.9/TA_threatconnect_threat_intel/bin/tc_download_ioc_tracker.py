# standard library
import os
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Union

# Add the path to the library
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib_1_1_9"))


@dataclass
class Tracker:
    """Stored Attributes Class"""

    start_time: datetime  # Start time of the job
    job_name: str  # Name of the job
    version: str  # Version of the job
    fields: Union[str, List[str]]  # List of fields
    owners: Union[str, List[str]]  # List of owners
    last_run: Union[Optional[datetime], str] = (
        None  # last_run for the job, None implies the first run
    )
    deleted_indicators: Dict[str, str] = field(
        default_factory=dict
    )  # Dictionary to store deleted indicators
    updated_indicators_subset: Set[str] = field(
        default_factory=set
    )  # Set to store updated indicators matching criteria
    stored_uuid5s: Set[str] = field(default_factory=set)  # Set to store UUIDs
    tql: str = ""  # TQL query
    added: int = 0  # Count of added indicators
    removed: int = 0  # Count of removed indicators

    def __post_init__(self):
        """Post-initialization hook."""
        self.fields = self.fields_validator(self.fields)
        self.owners = self.owners_validator(self.owners)

    @property
    def datetime_format(self) -> str:
        """Return the datetime format."""
        return "%Y-%m-%dT%H:%M:%SZ"

    @property
    def last_run_formatted(self) -> str:
        """Get start time string."""
        if self.last_run:
            return self.last_run.strftime(self.datetime_format)
        return ""

    @property
    def start_time_formatted(self) -> str:
        """Get start time string."""
        return self.start_time.strftime(self.datetime_format)

    @property
    def metrics(self) -> dict:
        """Get metrics information."""
        return {
            "added": self.added,
            "removed": self.removed,
            "total": self.added + self.removed,
            "total-runtime": datetime.utcnow()
            - self.start_time,  # Calculate time taken
            "time-range": f"{self.last_run_formatted} - {self.start_time_formatted}",  # Time range
            "file-name": self.file_name,
            "initial-run": "False" if self.last_run else "True",
        }

    @property
    def details(self) -> dict:
        """Get details information."""
        return {
            "version": self.version,
            "owners": self.owners,  # Display owners
            "tql": self.tql,  # Display TQL
            "fields": self.fields,  # Display fields
            "last-run": self.last_run_formatted,  # Display last run
            "start-time": self.start_time_formatted,  # Display start time
            "file-name": self.file_name,  # Display file name
            "initial-tql": self.tql_initial,  # Display initial TQL
            "base-tql": self.tql_base,  # Display base TQL
            "enhanced-tql": self.tql_enhance,  # Display enhanced TQL
        }

    @property
    def search_uuid5(self) -> str:
        """Generate a UUID5 based on job information."""
        identifier = f"{self.job_name} : {self.version}"
        if not self.version:
            identifiers = [self.job_name, self.tql, ",".join(self.owners)]
            identifier = " : ".join(identifiers)
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, identifier))

    @property
    def file_name(self) -> str:
        """Generate the file name."""
        return f"last_run_{self.job_name}_{self.search_uuid5}"

    def fields_validator(self, fields: str) -> List[str]:
        """Validate and normalize the 'fields' attribute."""
        fields = [
            i.strip() for i in fields.split(",") if i.strip()
        ]  # Split and strip fields
        return sorted(fields)  # Sort fields

    def owners_validator(self, owners: str) -> List[str]:
        """Validate and normalize the 'owners' attribute."""
        owners = [
            i.strip() for i in owners.split(",") if i.strip()
        ]  # Split and strip owners
        return sorted(owners)  # Sort owners

    @property
    def _tql_owner(self) -> str:
        """Generate TQL for owner."""
        return f"""ownerName IN ({",".join([f'"{owner}"' for owner in self.owners])})"""

    @property
    def tql_initial(self) -> str:
        """Generate initial TQL."""
        return (
            f"({self.tql}) AND "
            f'({self._tql_owner} AND lastModified LT "{self.start_time_formatted}")'
        )

    @property
    def tql_base(self) -> str:
        """Generate base TQL."""
        enhanced_tql = self._enhance_tql(include_inactive_indicators=True)
        return f"{' AND '.join(enhanced_tql)}"

    @property
    def tql_enhance(self) -> str:
        """Generate enhanced TQL."""
        enhanced_tql = self._enhance_tql()
        return f"({self.tql}) AND ({' AND '.join(enhanced_tql)})"

    def _enhance_tql(self, include_inactive_indicators=False) -> List[str]:
        """Enhance TQL."""
        add_false_positive_filter = "falsepositivecount" in self.tql.lower()
        last_modified_tql = (
            f'lastModified GEQ "{self.last_run_formatted}"' if self.last_run else ""
        )
        # The lastFalsePositive field doesnt support hours/minutes/seconds so we subtract 24 hours
        # to ensure we get all false positives that were added since last run.
        false_positive = self.last_run - timedelta(hours=24) if self.last_run else None
        false_positive = (
            false_positive.strftime(self.datetime_format) if false_positive else None
        )
        start_time = self.start_time_formatted
        tql_enhancements = [f'lastModified LT "{start_time}"', self._tql_owner]

        if add_false_positive_filter and last_modified_tql and false_positive:
            false_positive_tql = f'lastFalsePositive GEQ "{false_positive}"'
            or_clause = " OR ".join([last_modified_tql, false_positive_tql])
            tql_enhancements.append(f"({or_clause})")
        elif last_modified_tql:
            tql_enhancements.append(last_modified_tql)

        if include_inactive_indicators:
            tql_enhancements.append("(indicatorActive=true OR indicatorActive=false)")

        return tql_enhancements
