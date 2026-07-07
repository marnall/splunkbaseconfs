#!/usr/bin/env python
import sys
from typing import Generator
import datetime as dt

from vendor.splunklib.searchcommands import (
    StreamingCommand,
    dispatch,
    Configuration,
    Option,
    validators,
)

from vendor.croniter import croniter
from recordedfuture.core.logging import setup_logging


@Configuration(local=True)
class CronParserCommand(StreamingCommand):
    """A streaming command that takes a cron syntax and turns it into the next scheduled date"""

    cron = Option(
        doc="""**Syntax** *cron=<field_name>*
            **Description** a field with cron syntax""",
        validate=validators.Fieldname(),
    )

    timestamp = Option(
        doc="""**Syntax** *timestamp=<field_name>*
            **Description** A timestamp field, used as the base for the next date""",
        default="",
    )

    field_name = Option(
        doc="""**Syntax** field_name=<name>
            **Description** what you want the field to be named when returned in the record""",
        default="next_date",
        validate=validators.Fieldname(),
    )

    def __init__(self):
        super().__init__()
        self.rf_logger = setup_logging()

    def stream(self, records) -> Generator[str, None, None]:
        """Get the next scheduled date from a string with cron syntax"""
        cron_string_name = self.cron
        if not cron_string_name:
            raise ValueError("You need to define the cron field")

        date = dt.datetime.now(dt.timezone.utc)

        for record in records:
            cron_schedule = record.get(cron_string_name)
            next_date = None
            if cron_schedule and cron_schedule != "@now":
                if self.timestamp:
                    date = dt.datetime.fromtimestamp(
                        record[self.timestamp], tz=dt.timezone.utc
                    )

                cron_iterator = croniter(cron_schedule, date, second_at_beginning=True)
                next_date = cron_iterator.get_next(dt.datetime).timestamp()
            record[self.field_name] = next_date
            yield record


dispatch(CronParserCommand, sys.argv, sys.stdin, sys.stdout, __name__)
