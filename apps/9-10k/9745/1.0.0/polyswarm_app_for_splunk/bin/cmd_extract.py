"""Search command entry point for polyswarmextract.

Registered in default/commands.conf as a chunked (v2 protocol) command.

    ... | polyswarmextract
    ... | polyswarmextract textfield=message

Reads a text field off each incoming result, runs the shared IOC extraction
engine over it, and emits three aligned multivalue fields:

    polyswarm_ioc           the refanged canonical indicator
    polyswarm_ioc_type      one of sha256, sha1, md5, ip, domain, url, email
    polyswarm_ioc_defanged  the exact source text, possibly still defanged

The three lists are index aligned, so position n of each describes the same
indicator. Splunk's mvzip and mvexpand rely on that alignment, and a caller
doing `| eval pairs = mvzip(polyswarm_ioc, polyswarm_ioc_type)` gets nonsense
if it is ever broken, so it is asserted in the tests rather than assumed.

Why polyswarm_ioc_defanged carries the source text and not a boolean
--------------------------------------------------------------------
The engine reports a `defanged` boolean per indicator, and the obvious reading
of this field name would be that flag. It carries the original text instead,
because the original is strictly more information: the flag is recoverable from
it by comparing against polyswarm_ioc, whereas the original text cannot be
recovered from the flag. An analyst looking at a phishing mail wants to see
that the event said hxxps://evil[.]com, not that a boolean was true.

This command is pure local computation. It makes no network calls, needs no API
key, and costs no quota, which is why it is readable by the user role while
polyswarmsearch is not.

Importing this module is side effect free. It only runs when Splunk invokes it
as a subprocess.
"""

import os
import sys

# Vendored dependencies. Must precede the splunklib import. See bin/lib/README.
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

import extract_engine
import ps_log
from ps_sanitize import sanitize

from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    Option,
    StreamingCommand,
    dispatch,
)

COMMAND_NAME = "polyswarmextract"

# The component name this module reports itself as in structured log lines.
LOG_COMPONENT = "cmd_extract"

# The field the command reads indicators out of by default. The textfield option
# overrides it; the name lives here so the handler and the tests agree on one
# default.
DEFAULT_SOURCE_FIELD = "_raw"

# Output field names. Part of the command's public contract: a customer's saved
# search and dashboard panels reference these by name, so renaming one is a
# breaking change for them, not an internal refactor.
IOC_FIELD = "polyswarm_ioc"
IOC_TYPE_FIELD = "polyswarm_ioc_type"
IOC_DEFANGED_FIELD = "polyswarm_ioc_defanged"

OUTPUT_FIELDS = (IOC_FIELD, IOC_TYPE_FIELD, IOC_DEFANGED_FIELD)

# No module logger here. Everything this command writes goes through ps_log,
# so that the whitelist is the only route a value has into a log line.


def run_extract(field_value):
    """Return the indicators found in one input field value.

    The single entry point from the search command into the shared extraction
    engine. Pure: it reads the value, returns indicator dictionaries, and
    writes nothing anywhere. Field content is never logged, which is the reason
    this is a plain function call and not a wrapper with instrumentation.

    A value that is absent or not text yields no indicators rather than an
    error, because one malformed event must not fail a whole search.

    :param field_value: the raw field value from an input result.
    :returns: a list of indicator dicts as documented in extract_engine.
    """
    if field_value is None:
        return []
    if not isinstance(field_value, str):
        return []
    return extract_engine.extract(field_value)


def build_output_fields(field_value):
    """Return the three aligned multivalue lists for one input value.

    Built from a single pass over one indicator list, so the three lists cannot
    drift out of alignment by construction. An input with no indicators yields
    empty lists, and the caller decides whether to emit the fields at all.

    :param field_value: the raw field value from an input result.
    :returns: a dict of the three output field names to lists of strings.
    """
    indicators = run_extract(field_value)
    values = []
    types = []
    originals = []
    for indicator in indicators:
        values.append(indicator["value"])
        types.append(indicator["type"])
        originals.append(indicator["original"])
    return {
        IOC_FIELD: values,
        IOC_TYPE_FIELD: types,
        IOC_DEFANGED_FIELD: originals,
    }


def build_record(record, textfield=DEFAULT_SOURCE_FIELD):
    """Return a copy of one input record with the output fields added.

    The input record is never mutated: Splunk reuses the mapping it hands the
    command across the chunk in some SDK versions, and mutating it in place has
    produced fields bleeding between events.

    A record with no indicators gets the fields as empty lists rather than not
    at all, so that the schema of the result set does not depend on the content
    of the first event. A dashboard panel bound to polyswarm_ioc breaks if the
    field is sometimes absent entirely.

    THE THREE FIELDS THIS COMMAND EMITS GO THROUGH THE SANITIZER. THE
    CUSTOMER'S RECORD DOES NOT, AND THAT IS A FIX RATHER THAN A RELAXATION.
    ----------------------------------------------------------------------
    The sanitizer applies an unanchored field-NAME rule, so any key whose name
    merely CONTAINS api_key, authorization, password or token has its value
    replaced with [REDACTED], with no secret involved. Running the whole record
    through it therefore corrupted ordinary customer data on every event that
    passed through this command: password_age_days, tokens_issued and
    Authorization_Type are real field names, and all three came out redacted,
    silently, with the event's own value gone from the result set.

    Sanitizing what the app emits is still unconditional, for the reason it
    always was: an output path that is sanitized only when the developer judged
    it necessary is one that will one day be judged wrong. It costs nothing
    here, because this command holds no credential and its three field names
    match no rule.

    :param record: an input result mapping.
    :param textfield: the field to read indicators from.
    :returns: a new mapping, safe to emit.
    """
    output = dict(record)
    output.update(sanitize(build_output_fields(record.get(textfield))))
    return output


def build_records(records, textfield=DEFAULT_SOURCE_FIELD):
    """Yield an enriched record for each input record.

    Pure and generator based, so the whole result set is never held in memory.
    Takes no client and no session: this command reaches nothing outside the
    process.
    """
    for record in records:
        yield build_record(record, textfield=textfield)


@Configuration()
class PolySwarmExtractCommand(StreamingCommand):
    """Extract indicators of compromise from a text field.

    A streaming command rather than an eventing one, so Splunk can distribute
    it across indexers and run it on partial results. Nothing here depends on
    seeing the whole result set.
    """

    textfield = Option(
        doc="""
        **Syntax:** **textfield=***<field>*
        **Description:** the field to read indicators from. Defaults to _raw.
        """,
        require=False,
        default=DEFAULT_SOURCE_FIELD,
    )

    def stream(self, records):
        # One start line and one finish line, the same pair polyswarmsearch
        # writes. This command reaches nothing outside the process, so there is
        # no request or cache to report and the record count is the whole
        # story. It is still worth having: a command that starts and never
        # finishes is the shape a crash or a kill takes in a log, and that is
        # the case an operator cannot tell from a search that matched nothing.
        #
        # The textfield name is deliberately not on the line. ps_log has no key
        # for it, and a field name comes out of the search string, which is the
        # customer's and not ours to copy into a second file.
        timer = ps_log.Timer()
        ps_log.info(LOG_COMPONENT, "start", "ok")

        textfield = self.textfield or DEFAULT_SOURCE_FIELD

        emitted = 0
        for record in build_records(records, textfield=textfield):
            emitted += 1
            yield record

        ps_log.info(
            LOG_COMPONENT,
            "finish",
            "ok",
            records=emitted,
            duration_ms=timer.duration_ms,
        )


def main(argv=None):
    """Console entry point invoked by Splunk."""
    dispatch(
        PolySwarmExtractCommand,
        argv if argv is not None else sys.argv,
        sys.stdin,
        sys.stdout,
        __name__,
    )


if __name__ == "__main__":
    main()
